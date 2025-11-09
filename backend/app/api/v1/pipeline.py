"""Pipeline orchestration endpoints."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from ...schemas.pipeline import (
    PipelineRunRequest,
    PipelineRunStatusResponse,
    PipelineRunTriggerResponse,
)
from ...services.pipeline_runner import PipelineRunner
from ...services.run_state import RunStateManager

router = APIRouter()


@router.post("/run", response_model=PipelineRunTriggerResponse)
async def trigger_pipeline_run(
    payload: PipelineRunRequest,
    background_tasks: BackgroundTasks,
) -> PipelineRunTriggerResponse:
    """Enqueue a pipeline run and return its identifier."""

    manager = RunStateManager.instance()
    state = await manager.create_run(payload.run_name, payload)

    runner = PipelineRunner()
    background_tasks.add_task(runner.execute_with_tracking, state.run_id, payload)

    return PipelineRunTriggerResponse(run_id=state.run_id)


@router.get("/run/{run_id}", response_model=PipelineRunStatusResponse)
async def get_pipeline_run_status(run_id: str) -> PipelineRunStatusResponse:
    """Fetch the latest known status for a pipeline run."""

    manager = RunStateManager.instance()
    status = await manager.get_status(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return status


@router.get("/run/{run_id}/stream")
async def stream_pipeline_run(run_id: str) -> StreamingResponse:
    """Server-Sent Events stream emitting run lifecycle updates."""

    manager = RunStateManager.instance()
    queue = manager.get_queue(run_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator() -> AsyncIterator[str]:
        try:
            while True:
                message = await queue.get()
                if message is None:
                    break
                yield message
        except asyncio.CancelledError:  # pragma: no cover - connection dropped
            raise

    return StreamingResponse(event_generator(), media_type="text/event-stream")
