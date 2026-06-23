from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.core.event_bus import Event, event_bus

logger = logging.getLogger(__name__)


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineStep:
    agent_type: str
    config: dict = field(default_factory=dict)
    status: str = "pending"
    result: dict | None = None
    error: str | None = None


@dataclass
class Pipeline:
    pipeline_id: str
    project_id: str
    goal: str
    steps: list[PipelineStep]
    status: PipelineStatus = PipelineStatus.PENDING
    context: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


EventHandlerType = callable


class PipelineRunner:
    def __init__(self):
        self._pipelines: dict[str, Pipeline] = {}
        self._handlers: dict[str, EventHandlerType] = {}
        self._subscribed = False

    def _ensure_subscribed(self):
        if not self._subscribed:
            event_bus.subscribe("agent:*", self._on_agent_event)
            self._subscribed = True

    def create_pipeline(
        self,
        pipeline_id: str,
        project_id: str,
        goal: str,
        steps: list[dict],
    ) -> Pipeline:
        self._ensure_subscribed()
        pipeline = Pipeline(
            pipeline_id=pipeline_id,
            project_id=project_id,
            goal=goal,
            steps=[PipelineStep(**s) for s in steps],
        )
        self._pipelines[pipeline_id] = pipeline
        return pipeline

    def get_pipeline(self, pipeline_id: str) -> Pipeline | None:
        return self._pipelines.get(pipeline_id)

    def list_pipelines(self, project_id: str) -> list[Pipeline]:
        return [p for p in self._pipelines.values() if p.project_id == project_id]

    def register_handler(
        self, agent_type: str, handler: EventHandlerType
    ):
        self._handlers[agent_type] = handler

    async def start_pipeline(self, pipeline_id: str) -> dict:
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return {"success": False, "error": "Pipeline not found"}

        pipeline.status = PipelineStatus.RUNNING
        pipeline.updated_at = datetime.now(timezone.utc)

        first_step = pipeline.steps[0]
        first_step.status = "running"
        handler = self._handlers.get(first_step.agent_type)
        if not handler:
            first_step.status = "failed"
            first_step.error = f"No handler for {first_step.agent_type}"
            pipeline.status = PipelineStatus.FAILED
            return {"success": False, "error": first_step.error}

        try:
            result = await handler(context=pipeline.context)
            first_step.result = result
            first_step.status = "completed"
            pipeline.context.setdefault(first_step.agent_type, {})
            pipeline.context[first_step.agent_type] = result

            await event_bus.publish(Event(
                event_type=f"agent:{first_step.agent_type}:completed",
                source="pipeline",
                data={
                    "pipeline_id": pipeline_id,
                    "project_id": pipeline.project_id,
                    "result": result,
                    "next_steps": [s.agent_type for s in pipeline.steps[1:]],
                },
            ))

            if len(pipeline.steps) == 1:
                pipeline.status = PipelineStatus.COMPLETED
                pipeline.updated_at = datetime.now(timezone.utc)
                await event_bus.publish(Event(
                    event_type="pipeline:completed",
                    source="pipeline",
                    data={
                        "pipeline_id": pipeline_id,
                        "project_id": pipeline.project_id,
                        "results": {s.agent_type: s.result for s in pipeline.steps if s.result},
                    },
                ))

            return {"success": True, "pipeline_id": pipeline_id, "step": first_step.agent_type, "result": result}
        except Exception as e:
            first_step.status = "failed"
            first_step.error = str(e)
            pipeline.status = PipelineStatus.FAILED
            logger.exception("Pipeline step %s failed: %s", first_step.agent_type, e)
            return {"success": False, "error": str(e)}

    async def _on_agent_event(self, event: Event):
        if event.event_type.startswith("agent:") and event.event_type.endswith(":completed"):
            agent_type = event.event_type.split(":")[1]
            data = event.data
            pipeline_id = data.get("pipeline_id")
            if not pipeline_id:
                return
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline or pipeline.status != PipelineStatus.RUNNING:
                return

            current_step_index = None
            for i, step in enumerate(pipeline.steps):
                if step.agent_type == agent_type and step.status == "completed":
                    current_step_index = i
                    break

            if current_step_index is None:
                return

            next_index = current_step_index + 1
            if next_index >= len(pipeline.steps):
                pipeline.status = PipelineStatus.COMPLETED
                pipeline.updated_at = datetime.now(timezone.utc)
                await event_bus.publish(Event(
                    event_type="pipeline:completed",
                    source="pipeline",
                    data={
                        "pipeline_id": pipeline_id,
                        "project_id": pipeline.project_id,
                    },
                ))
                return

            next_step = pipeline.steps[next_index]
            next_step.status = "running"
            handler = self._handlers.get(next_step.agent_type)
            if not handler:
                next_step.status = "failed"
                next_step.error = f"No handler for {next_step.agent_type}"
                pipeline.status = PipelineStatus.FAILED
                return

            try:
                kwargs = {"context": pipeline.context}
                for s in pipeline.steps[:next_index]:
                    if s.status == "completed" and s.result:
                        kwargs[s.agent_type] = s.result
                result = await handler(**kwargs)
                next_step.result = result
                next_step.status = "completed"
                pipeline.context[next_step.agent_type] = result
                pipeline.updated_at = datetime.now(timezone.utc)

                await event_bus.publish(Event(
                    event_type=f"agent:{next_step.agent_type}:completed",
                    source="pipeline",
                    data={
                        "pipeline_id": pipeline_id,
                        "project_id": pipeline.project_id,
                        "result": result,
                    },
                ))

                if next_index == len(pipeline.steps) - 1:
                    pipeline.status = PipelineStatus.COMPLETED
                    pipeline.updated_at = datetime.now(timezone.utc)
                    await event_bus.publish(Event(
                        event_type="pipeline:completed",
                        source="pipeline",
                        data={
                            "pipeline_id": pipeline_id,
                            "project_id": pipeline.project_id,
                            "results": {s.agent_type: s.result for s in pipeline.steps if s.result},
                        },
                    ))

            except Exception as e:
                next_step.status = "failed"
                next_step.error = str(e)
                pipeline.status = PipelineStatus.FAILED
                pipeline.updated_at = datetime.now(timezone.utc)
                logger.exception("Pipeline chain step %s failed: %s", next_step.agent_type, e)


pipeline_runner = PipelineRunner()
