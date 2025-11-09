"""Pydantic models describing pipeline requests and responses."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PipelinePlatform(str, Enum):
    """Supported social export targets."""

    instagram = "instagram"
    tiktok = "tiktok"


class PipelineStage(str, Enum):
    """Agent stages surfaced to the frontend."""

    ingest = "ingest"
    narrative = "narrative"
    voiceover = "voiceover"
    editing = "editing"
    packaging = "packaging"
    analytics = "analytics"
    completed = "completed"


class PipelineStageSnapshot(BaseModel):
    """Status snapshot for a specific pipeline stage."""

    stage: PipelineStage
    status: str = Field(description="Current status label (e.g., pending, running, done)")
    detail: str | None = Field(default=None, description="Human-friendly summary")
    payload: dict[str, Any] | None = Field(default=None, description="Optional stage data")


class PipelineRunRequest(BaseModel):
    """Incoming request payload to bootstrap a pipeline run."""

    run_name: str = Field(default="demo-run")
    platforms: list[PipelinePlatform] = Field(default_factory=lambda: [PipelinePlatform.instagram, PipelinePlatform.tiktok])
    stock_keywords: list[str] = Field(
        default_factory=lambda: [
            "luxury education",
            "STEM kids",
            "family learning",
        ]
    )
    notes: str | None = Field(default=None, description="Optional creative direction notes")


class PipelineRunResponse(BaseModel):
    """Response body returned once the pipeline completes or is queued."""

    run_name: str
    stages: list[PipelineStageSnapshot]
    outputs: dict[str, Any] = Field(default_factory=dict)


class PipelineRunTriggerResponse(BaseModel):
    """Response returned once a pipeline run has been enqueued."""

    run_id: str


class PipelineRunStatus(str, Enum):
    """Overall pipeline run lifecycle state."""

    queued = "queued"
    running = "running"
    completed = "completed"
    error = "error"


class PipelineRunStatusResponse(BaseModel):
    """Snapshot describing the current state of a pipeline run."""

    run_id: str
    run_name: str
    status: PipelineRunStatus
    stages: list[PipelineStageSnapshot] = Field(default_factory=list)
    outputs: dict[str, Any] = Field(default_factory=dict)
