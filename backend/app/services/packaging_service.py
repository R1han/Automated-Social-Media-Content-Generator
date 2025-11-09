"""Packaging of deliverables into structured metadata bundles."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class PackagingService:
    """Serializes outputs for easy consumption by the frontend and demo audiences."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.outputs_dir = Path(self.settings.outputs_dir)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    def package(
        self,
        run_name: str,
        narrative: dict[str, Any],
        assets: dict[str, Any],
        video_paths: dict[str, str],
    ) -> dict[str, Any]:
        bundle_dir = self.outputs_dir / run_name
        bundle_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = bundle_dir / "metadata.json"

        payload = {
            "run_name": run_name,
            "narrative": narrative,
            "assets": assets,
            "videos": video_paths,
        }
        with metadata_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)

        logger.info("Packaged outputs", extra={"metadata": str(metadata_path)})
        return {"metadata_path": str(metadata_path), "bundle_dir": str(bundle_dir)}
