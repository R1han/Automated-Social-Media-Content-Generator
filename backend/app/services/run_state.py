"""In-memory run state tracking for live pipeline updates."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable

from ..schemas.pipeline import (
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineRunStatus,
    PipelineRunStatusResponse,
    PipelineStage,
    PipelineStageSnapshot,
)


PIPELINE_STAGE_ORDER: tuple[PipelineStage, ...] = (
    PipelineStage.ingest,
    PipelineStage.narrative,
    PipelineStage.voiceover,
    PipelineStage.editing,
    PipelineStage.packaging,
    PipelineStage.analytics,
    PipelineStage.completed,
)


@dataclass
class RunState:
    """Represents the lifecycle of an individual pipeline run."""

    run_id: str
    run_name: str
    request: PipelineRunRequest
    status: PipelineRunStatus = PipelineRunStatus.queued
    stages: dict[PipelineStage, PipelineStageSnapshot] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    queue: asyncio.Queue[str | None] = field(default_factory=asyncio.Queue)

    def stage_snapshots(self) -> list[PipelineStageSnapshot]:
        ordered = []
        for stage in PIPELINE_STAGE_ORDER:
            snapshot = self.stages.get(stage)
            if snapshot is not None:
                ordered.append(snapshot)
        return ordered


class RunStateManager:
    """Singleton manager coordinating run state and event emission."""

    _instance: RunStateManager | None = None

    def __init__(self) -> None:
        self._runs: dict[str, RunState] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def instance(cls) -> RunStateManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def create_run(self, run_name: str, request: PipelineRunRequest) -> RunState:
        run_id = uuid.uuid4().hex
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        stages = {
            stage: PipelineStageSnapshot(stage=stage, status="queued", detail="Awaiting execution", payload=None)
            for stage in PIPELINE_STAGE_ORDER
        }
        state = RunState(run_id=run_id, run_name=run_name, request=request, stages=stages, queue=queue)
        async with self._lock:
            self._runs[run_id] = state
        await queue.put(self._serialize_event({
            "event": "init",
            "run_id": run_id,
            "run_name": run_name,
            "stages": [snapshot.model_dump() for snapshot in state.stage_snapshots()],
        }))
        return state

    async def mark_run_started(self, run_id: str) -> None:
        state = await self._get_run(run_id)
        if state is None:
            return
        state.status = PipelineRunStatus.running
        await state.queue.put(self._serialize_event({"event": "run", "run_id": run_id, "status": state.status.value}))

    async def update_stage(
        self,
        run_id: str,
        stage: PipelineStage,
        status: str,
        detail: str | None = None,
        payload: Any | None = None,
    ) -> None:
        state = await self._get_run(run_id)
        if state is None:
            return
        snapshot = PipelineStageSnapshot(stage=stage, status=status, detail=detail, payload=payload)
        state.stages[stage] = snapshot
        await state.queue.put(
            self._serialize_event(
                {
                    "event": "stage",
                    "run_id": run_id,
                    "snapshot": snapshot.model_dump(),
                }
            )
        )

    async def mark_run_completed(self, run_id: str, response: PipelineRunResponse) -> None:
        state = await self._get_run(run_id)
        if state is None:
            return
        state.status = PipelineRunStatus.completed
        state.outputs = response.outputs
        await state.queue.put(self._serialize_event({"event": "run", "run_id": run_id, "status": state.status.value}))
        await state.queue.put(
            self._serialize_event(
                {
                    "event": "complete",
                    "run_id": run_id,
                    "response": response.model_dump(),
                }
            )
        )
        await state.queue.put(None)

    async def mark_run_failed(self, run_id: str, message: str) -> None:
        state = await self._get_run(run_id)
        if state is None:
            return
        state.status = PipelineRunStatus.error
        await state.queue.put(self._serialize_event({"event": "run", "run_id": run_id, "status": state.status.value}))
        await state.queue.put(
            self._serialize_event(
                {
                    "event": "error",
                    "run_id": run_id,
                    "message": message,
                }
            )
        )
        await state.queue.put(None)

    async def get_status(self, run_id: str) -> PipelineRunStatusResponse | None:
        state = await self._get_run(run_id)
        if state is None:
            return None
        return PipelineRunStatusResponse(
            run_id=run_id,
            run_name=state.run_name,
            status=state.status,
            stages=state.stage_snapshots(),
            outputs=state.outputs,
        )

    def get_queue(self, run_id: str) -> asyncio.Queue[str | None] | None:
        return self._runs.get(run_id).queue if run_id in self._runs else None

    async def _get_run(self, run_id: str) -> RunState | None:
        async with self._lock:
            return self._runs.get(run_id)

    def _serialize_event(self, payload: dict[str, Any]) -> str:
        return f"data: {json.dumps(payload)}\n\n"