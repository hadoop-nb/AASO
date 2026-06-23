from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext, BaseAgent
from app.agents.developer import DeveloperAgent
from app.agents.qa_agent import QAAgent
from app.agents.review_agent import ReviewAgent
from app.core.event_bus import Event, event_bus
from app.schemas.task import TaskCreate
from app.services.analytics_service import AnalyticsService
from app.services.code_service import CodeService
from app.services.llm_service import LLMService, llm_service as default_llm
from app.services.memory_service import MemoryService
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)

_orchestration_runs: dict[str, OrchestrationRun] = {}


@dataclass
class OrchestrationRun:
    run_id: str
    project_id: str
    goal: str
    status: str = "pending"
    sub_tasks: list[dict] = field(default_factory=list)
    results: dict = field(default_factory=dict)
    qa_result: dict | None = None
    review_result: dict | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class OrchestratorAgent(BaseAgent):
    def __init__(
        self,
        context: AgentContext,
        session: AsyncSession,
        llm: LLMService | None = None,
        memory: MemoryService | None = None,
        analytics: AnalyticsService | None = None,
    ):
        super().__init__(context)
        self.session = session
        self.task_service = TaskService(session)
        self.code_service = CodeService(session)
        self.llm = llm or default_llm
        self.memory = memory
        self.analytics = analytics or AnalyticsService(session)

    async def execute(self, input_data: dict) -> dict:
        project_id = input_data.get("project_id", self.context.project_id)
        goal = input_data.get("goal", "")
        if not goal:
            return {"success": False, "error": "No goal provided"}

        run = OrchestrationRun(
            run_id=input_data.get("run_id", f"orchestrate-{int(time.time())}"),
            project_id=project_id,
            goal=goal,
        )
        _orchestration_runs[run.run_id] = run

        try:
            run.status = "planning"
            sub_tasks = await self._decompose_goal(project_id, goal)
            run.sub_tasks = sub_tasks
            run.status = "executing"

            all_file_ids = []
            for i, st in enumerate(sub_tasks):
                st["status"] = "running"
                task_id = await self._create_task(project_id, st)
                st["task_id"] = task_id

                start = time.monotonic()
                agent = DeveloperAgent(
                    context=AgentContext(
                        agent_id=f"dev-sub-{i}",
                        name=f"Sub-task Developer {i}",
                        project_id=project_id,
                        task_id=task_id,
                    ),
                    session=self.session,
                    llm=self.llm,
                    memory=self.memory,
                )
                dev_result = await agent.execute(
                    {"task_id": task_id, "project_id": project_id}
                )
                duration = (time.monotonic() - start) * 1000

                st["status"] = "completed" if dev_result.get("success") else "failed"
                st["result"] = dev_result
                st["duration_ms"] = duration

                file_ids = dev_result.get("files", [])
                all_file_ids.extend(file_ids)

                await self.analytics.record_run(
                    agent_type="developer",
                    agent_id=f"dev-sub-{i}",
                    project_id=project_id,
                    task_id=task_id,
                    success=dev_result.get("success", False),
                    duration_ms=duration,
                    files_generated=len(file_ids),
                    error=dev_result.get("error"),
                    metadata={"sub_task": st.get("title", ""), "goal": goal},
                )

                await event_bus.publish(Event(
                    event_type="agent:developer:completed",
                    source="orchestrator",
                    data={
                        "project_id": project_id,
                        "task_id": task_id,
                        "sub_task_index": i,
                        "result": dev_result,
                    },
                ))

            run.status = "reviewing"
            all_files_data = []
            for fid in all_file_ids:
                f = await self.code_service.get(fid)
                if f:
                    all_files_data.append({
                        "path": f.path,
                        "content": f.content,
                        "language": f.language,
                    })

            qa_start = time.monotonic()
            qa_agent = QAAgent(
                context=AgentContext(
                    agent_id="qa-orchestrator",
                    name="QA Agent",
                    project_id=project_id,
                ),
                llm=self.llm,
            )
            qa_result = await qa_agent.validate_code(
                all_files_data, task_context=f"Goal: {goal}"
            )
            run.qa_result = qa_result
            qa_duration = (time.monotonic() - qa_start) * 1000
            await self.analytics.record_run(
                agent_type="qa",
                agent_id="qa-orchestrator",
                project_id=project_id,
                task_id="",
                success=qa_result.get("passed", False),
                duration_ms=qa_duration,
                metadata={"goal": goal, "files_count": len(all_files_data)},
            )

            review_start = time.monotonic()
            review_agent = ReviewAgent(
                context=AgentContext(
                    agent_id="review-orchestrator",
                    name="Review Agent",
                    project_id=project_id,
                ),
                llm=self.llm,
            )
            review_result = await review_agent.review_code(
                all_files_data, qa_results=qa_result, task_context=f"Goal: {goal}"
            )
            run.review_result = review_result
            review_duration = (time.monotonic() - review_start) * 1000
            await self.analytics.record_run(
                agent_type="review",
                agent_id="review-orchestrator",
                project_id=project_id,
                task_id="",
                success=review_result.get("approved", False),
                duration_ms=review_duration,
                metadata={
                    "goal": goal,
                    "score": review_result.get("score"),
                    "files_count": len(all_files_data),
                },
            )

            await event_bus.publish(Event(
                event_type="orchestration:completed",
                source="orchestrator",
                data={
                    "run_id": run.run_id,
                    "project_id": project_id,
                    "goal": goal,
                    "sub_tasks_count": len(sub_tasks),
                    "qa_passed": qa_result.get("passed"),
                    "review_approved": review_result.get("approved"),
                    "files_count": len(all_files_data),
                },
            ))

            run.status = "completed"
            return {
                "success": True,
                "run_id": run.run_id,
                "project_id": project_id,
                "goal": goal,
                "sub_tasks": sub_tasks,
                "qa_result": qa_result,
                "review_result": review_result,
                "total_files": len(all_files_data),
                "all_file_ids": all_file_ids,
            }

        except Exception as e:
            run.status = "failed"
            run.error = str(e)
            logger.exception("Orchestration failed: %s", e)
            return {"success": False, "error": str(e), "run_id": run.run_id}

    async def _decompose_goal(
        self, project_id: str, goal: str
    ) -> list[dict]:
        prompt = (
            f"Break down this development goal into sub-tasks:\n\n"
            f"Goal: {goal}\n\n"
            "Each sub-task should be a small, focused implementation step. "
            'Respond as JSON: {"sub_tasks": [{"title": "...", "description": "..."}]}'
        )
        result = await self.llm.generate(
            prompt,
            system_prompt="You are a technical lead decomposing work into sub-tasks.",
            project_id=project_id,
            agent_type="orchestrator",
        )
        try:
            data = json.loads(result)
            tasks = data.get("sub_tasks", [])
            if tasks:
                return tasks
        except json.JSONDecodeError:
            pass
        return [{"title": goal, "description": goal}]

    async def _create_task(
        self, project_id: str, sub_task: dict
    ) -> str:
        task = await self.task_service.create(
            project_id=project_id,
            data=TaskCreate(
                title=sub_task.get("title", "Untitled"),
                description=sub_task.get("description", ""),
            ),
        )
        return task.task_id

    def get_run(self, run_id: str) -> OrchestrationRun | None:
        return _orchestration_runs.get(run_id)

    def list_runs(self, project_id: str) -> list[OrchestrationRun]:
        return [r for r in _orchestration_runs.values() if r.project_id == project_id]
