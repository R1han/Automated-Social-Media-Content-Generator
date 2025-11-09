"""High-level orchestration of the demo content pipeline."""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from pathlib import Path
from dataclasses import asdict, is_dataclass
from typing import Any, Callable

from ..core.config import get_settings
from ..schemas.pipeline import (
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineStage,
    PipelineStageSnapshot,
)
from .analytics_service import AnalyticsService
from .assets_service import AssetService
from .editing_service import EditingService
from .narrative_service import NarrativePayload, NarrativeService
from .packaging_service import PackagingService
from .voiceover_service import VoiceoverService
from .run_state import RunStateManager

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Coordinates the sequential stages for the demo pipeline."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.assets_service = AssetService()
        self.narrative_service = NarrativeService()
        self.voiceover_service = VoiceoverService()
        self.editing_service = EditingService()
        self.packaging_service = PackagingService()
        self.analytics_service = AnalyticsService()
        self.state_manager = RunStateManager.instance()

    async def run(self, request: PipelineRunRequest) -> PipelineRunResponse:
        return await self._execute(request)

    async def execute_with_tracking(self, run_id: str, request: PipelineRunRequest) -> None:
        try:
            await self.state_manager.mark_run_started(run_id)
            response = await self._execute(request, run_id=run_id)
            await self.state_manager.mark_run_completed(run_id, response)
        except Exception as exc:  # pragma: no cover - runtime failure path
            logger.exception("Pipeline run failed", extra={"run_id": run_id})
            await self.state_manager.mark_run_failed(run_id, str(exc))

    async def _execute(self, request: PipelineRunRequest, run_id: str | None = None) -> PipelineRunResponse:
        logger.info("Starting pipeline run", extra={"run_name": request.run_name, "run_id": run_id})
        snapshots: list[PipelineStageSnapshot] = []

        assets_payload = await self._run_stage(
            stage=PipelineStage.ingest,
            snapshots=snapshots,
            executor=lambda: self.assets_service.prepare_assets(request.stock_keywords),
            detail_builder=lambda payload: self._format_ingest_detail(payload),
            run_id=run_id,
        )

        narrative_payload: NarrativePayload = await self._run_stage(
            stage=PipelineStage.narrative,
            snapshots=snapshots,
            executor=lambda: self.narrative_service.generate(
                request.run_name, request.stock_keywords, [platform.value for platform in request.platforms]
            ),
            detail_builder=lambda payload: "Generated master script and dual-platform captions.",
            run_id=run_id,
        )

        voiceover_payload = await self._run_stage(
            stage=PipelineStage.voiceover,
            snapshots=snapshots,
            executor=lambda: self.voiceover_service.synthesize(narrative_payload.master_script, request.run_name),
            detail_builder=lambda payload: f"Voiceover status: {payload.get('status', 'unknown')}.",
            run_id=run_id,
        )

        video_payload = await self._run_stage(
            stage=PipelineStage.editing,
            snapshots=snapshots,
            executor=lambda: self.editing_service.produce_videos(
                (asset["local_path"] for asset in assets_payload["assets"]),
                voiceover_payload.get("voiceover_path", ""),
                request.run_name,
            ),
            detail_builder=lambda payload: "Rendered Instagram and TikTok masters.",
            run_id=run_id,
        )

        packaging_payload = await self._run_stage(
            stage=PipelineStage.packaging,
            snapshots=snapshots,
            executor=lambda: self.packaging_service.package(
                request.run_name,
                narrative_payload.as_dict(),
                assets_payload,
                video_payload,
            ),
            detail_builder=lambda payload: "Packaged deliverables into metadata bundle.",
            run_id=run_id,
        )

        analytics_payload = await self._run_stage(
            stage=PipelineStage.analytics,
            snapshots=snapshots,
            executor=lambda: self.analytics_service.evaluate(
                narrative_payload.master_script,
                narrative_payload.instagram_caption,
            ),
            detail_builder=lambda payload: "Computed engagement heuristics.",
            run_id=run_id,
        )

        completion_snapshot = PipelineStageSnapshot(
            stage=PipelineStage.completed,
            status="done",
            detail=f"Run finished at {dt.datetime.utcnow().isoformat()}Z",
            payload=None,
        )
        snapshots.append(completion_snapshot)
        if run_id:
            await self.state_manager.update_stage(run_id, PipelineStage.completed, "done", completion_snapshot.detail, None)

        outputs = {
            "instagram": {
                "video_path": self._public_asset_path(video_payload.get("instagram_video")),
                "caption": narrative_payload.instagram_caption,
                "hashtags": narrative_payload.instagram_hashtags,
                "cta": narrative_payload.cta,
            },
            "tiktok": {
                "video_path": self._public_asset_path(video_payload.get("tiktok_video")),
                "caption": narrative_payload.tiktok_caption,
                "hashtags": narrative_payload.tiktok_hashtags,
                "cta": narrative_payload.cta,
            },
            "metadata": packaging_payload,
            "analytics": analytics_payload.as_dict(),
        }

        return PipelineRunResponse(run_name=request.run_name, stages=snapshots, outputs=outputs)

    async def _run_stage(
        self,
        *,
        stage: PipelineStage,
        snapshots: list[PipelineStageSnapshot],
        executor: Callable[[], Any],
        detail_builder: Callable[[Any], str],
        run_id: str | None = None,
    ) -> Any:
        logger.info("Stage started", extra={"stage": stage.value})
        if run_id:
            await self.state_manager.update_stage(run_id, stage, "running")
        try:
            result = await asyncio.to_thread(executor)
            detail = detail_builder(result)
            snapshot = PipelineStageSnapshot(
                stage=stage,
                status="done",
                detail=detail,
                payload=self._sanitize_payload(result),
            )
            snapshots.append(snapshot)
            if run_id:
                await self.state_manager.update_stage(run_id, stage, "done", detail, snapshot.payload)
            logger.info("Stage finished", extra={"stage": stage.value})
            return result
        except Exception as exc:
            logger.exception("Stage failed", extra={"stage": stage.value})
            snapshot = PipelineStageSnapshot(
                stage=stage,
                status="error",
                detail=str(exc),
                payload=None,
            )
            snapshots.append(snapshot)
            if run_id:
                await self.state_manager.update_stage(run_id, stage, "error", str(exc))
            raise RuntimeError(f"Stage {stage.value} failed") from exc

    def _sanitize_payload(self, payload: Any) -> Any:
        if is_dataclass(payload):
            return self._sanitize_payload(asdict(payload))
        if isinstance(payload, dict):
            sanitized: dict[str, Any] = {}
            for key, value in payload.items():
                if key in {"assets"}:
                    sanitized[key] = [
                        {
                            "id": item.get("id"),
                            "local_path": item.get("local_path"),
                            "license": item.get("license"),
                        }
                        for item in value
                        if isinstance(item, dict)
                    ]
                elif isinstance(value, (str, int, float)):
                    if isinstance(value, str):
                        sanitized[key] = self._rewrite_asset_path(value)
                    else:
                        sanitized[key] = value
                else:
                    sanitized[key] = str(value)
            return sanitized
        if isinstance(payload, (list, tuple)):
            return [self._sanitize_payload(item) for item in payload]
        return payload

    def _format_ingest_detail(self, payload: Any) -> str:
        assets = payload.get("assets", []) if isinstance(payload, dict) else []
        count = len(assets)
        placeholder_count = sum(1 for asset in assets if isinstance(asset, dict) and asset.get("placeholder"))
        if placeholder_count:
            return f"Prepared {count} clips ({placeholder_count} placeholders generated)."
        return f"Prepared {count} curated clips."

    def _public_asset_path(self, path: str | None) -> str | None:
        if not path:
            return None
        try:
            path_obj = Path(path)
            relative = path_obj.relative_to(self.settings.outputs_dir)
        except ValueError:
            return None
        return f"outputs/{relative.as_posix()}"

    def _rewrite_asset_path(self, value: str) -> str:
        public_path = self._public_asset_path(value)
        return public_path or value
