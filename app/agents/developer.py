from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, AgentContext
from app.models.task import Task
from app.schemas.code_file import CodeFileCreate
from app.schemas.decision import DecisionCreate
from app.schemas.lesson import LessonCreate
from app.schemas.task import TaskUpdate
from app.services.code_service import CodeService
from app.services.decision_service import DecisionService
from app.services.lesson_service import LessonService
from app.services.llm_service import LLMService, llm_service as default_llm
from app.services.memory_service import MemoryService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


class DeveloperAgent(BaseAgent):
    def __init__(
        self,
        context: AgentContext,
        session: AsyncSession,
        llm: LLMService | None = None,
        memory: MemoryService | None = None,
    ):
        super().__init__(context)
        self.session = session
        self.project_service = ProjectService(session)
        self.task_service = TaskService(session)
        self.decision_service = DecisionService(session)
        self.lesson_service = LessonService(session)
        self.code_service = CodeService(session)
        self.llm = llm or default_llm
        self.memory = memory

    async def execute(self, input_data: dict) -> dict:
        task_id = input_data.get("task_id")
        project_id = input_data.get("project_id")

        task = await self._validate_task(task_id, project_id)
        if not task:
            return {"success": False, "error": "Task not found"}

        project = await self.project_service.get(task.project_id)
        context_text = await self._build_context(task, project)

        relevant_lessons = await self._retrieve_experiences(task)
        relevant_decisions = await self._retrieve_decisions(task)

        plan = await self._generate_plan(
            task, context_text, relevant_lessons, relevant_decisions
        )

        code_files = await self._generate_code(plan, task)
        stored_files = await self._store_files(code_files, task)

        decision = await self._record_decision(plan, task)
        lesson = await self._record_lesson(plan, task)

        await self.task_service.update(
            task.task_id,
            TaskUpdate(status="in_progress"),
        )
        await self.task_service.update(
            task.task_id,
            TaskUpdate(status="completed"),
        )

        return {
            "success": True,
            "task_id": task.task_id,
            "files": stored_files,
            "decision_id": decision.decision_id if decision else None,
            "lesson_id": lesson.lesson_id if lesson else None,
        }

    async def _validate_task(
        self, task_id: str, project_id: str
    ) -> Task | None:
        task = await self.task_service.get(task_id)
        if not task:
            return None
        if project_id and task.project_id != project_id:
            return None
        return task

    async def _build_context(
        self, task: Task, project
    ) -> str:
        parts = [
            f"Project: {project.name if project else 'Unknown'}",
            f"Description: {project.description if project else ''}",
            f"Task: {task.title}",
            f"Task Description: {task.description}",
            f"Priority: {task.priority}",
        ]
        return "\n".join(parts)

    async def _retrieve_experiences(
        self, task: Task
    ) -> list[dict]:
        if not self.memory:
            return []
        return await self.memory.query(
            project_id=task.project_id,
            query=f"Implementation lessons for: {task.title} {task.description}",
            filter_types=["lesson"],
            limit=5,
        )

    async def _retrieve_decisions(
        self, task: Task
    ) -> list[dict]:
        if not self.memory:
            return []
        return await self.memory.query(
            project_id=task.project_id,
            query=f"Decisions related to: {task.title} {task.description}",
            filter_types=["decision"],
            limit=5,
        )

    async def _generate_plan(
        self,
        task: Task,
        context: str,
        lessons: list[dict],
        decisions: list[dict],
    ) -> dict:
        prompt = (
            f"Task: Implement the following:\n{context}\n\n"
            f"Relevant past lessons:\n{json.dumps(lessons, indent=2)}\n\n"
            f"Relevant past decisions:\n{json.dumps(decisions, indent=2)}\n\n"
            "Generate an implementation plan with code files, "
            "a key decision made, and a lesson learned."
        )
        result = await self.llm.generate(
            prompt,
            system_prompt="You are a senior software engineer implementing features.",
            project_id=self.context.project_id,
            agent_type="developer",
        )
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {
                "plan": result,
                "files": [],
                "decision": {},
                "lesson": {},
            }

    async def _generate_code(
        self, plan: dict, task: Task
    ) -> list[dict]:
        return plan.get("files", [])

    async def _store_files(
        self, files: list[dict], task: Task
    ) -> list[str]:
        stored = []
        for f in files:
            record = await self.code_service.create(
                project_id=task.project_id,
                data=CodeFileCreate(
                    path=f.get("path", "unknown"),
                    summary=f.get("summary", ""),
                    content=f.get("content", ""),
                    language=f.get("language", "python"),
                ),
                task_id=task.task_id,
            )
            stored.append(record.file_id)
        return stored

    async def _record_decision(
        self, plan: dict, task: Task
    ) -> None:
        dec = plan.get("decision", {})
        if dec.get("question"):
            return await self.decision_service.create(
                project_id=task.project_id,
                data=DecisionCreate(
                    question=dec["question"],
                    alternatives=dec.get("alternatives", []),
                    selected=dec.get("selected", ""),
                    reason=dec.get("reason", ""),
                ),
            )
        return None

    async def _record_lesson(
        self, plan: dict, task: Task
    ) -> None:
        les = plan.get("lesson", {})
        if les.get("problem"):
            return await self.lesson_service.create(
                project_id=task.project_id,
                data=LessonCreate(
                    problem=les["problem"],
                    solution=les.get("solution", ""),
                    result=les.get("result", ""),
                ),
            )
        return None
