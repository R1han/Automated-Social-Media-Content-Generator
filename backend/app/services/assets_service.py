"""Stock asset ingestion utilities."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import httpx
from moviepy import ColorClip
import shutil

from ..core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AssetDescriptor:
    """Represents a downloadable stock asset."""

    asset_id: str
    filename: str
    source_url: str
    keywords: list[str]
    license: str
    local_path: str | None

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "AssetDescriptor":
        return cls(
            asset_id=str(payload["id"]),
            filename=str(payload["filename"]),
            source_url=str(payload.get("source_url", "")),
            keywords=[str(keyword) for keyword in payload.get("keywords", [])],
            license=str(payload.get("license", "unknown")),
            local_path=str(payload.get("local_path")) if payload.get("local_path") else None,
        )


class AssetService:
    """Handles retrieval and caching of stock footage for the demo."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.manifest_path = Path(self.settings.assets_dir) / "stock_manifest.json"
        self.download_dir = Path(self.settings.assets_dir) / "downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.placeholder_dir = Path(self.settings.assets_dir) / "placeholders"
        self.placeholder_dir.mkdir(parents=True, exist_ok=True)

    def prepare_assets(self, requested_keywords: Iterable[str]) -> dict[str, object]:
        """Select and download assets matching the supplied keywords."""

        manifest = self._load_manifest()
        selected = self._select_assets(manifest, requested_keywords)
        downloaded_assets: list[dict[str, object]] = []

        for asset in selected:
            local_path = self.download_dir / asset.filename
            placeholder_used = False
            if not local_path.exists():
                try:
                    if asset.local_path:
                        source_path = Path(self.settings.assets_dir) / asset.local_path
                        if not source_path.exists():
                            raise FileNotFoundError(f"Local asset not found at {source_path}")
                        shutil.copy2(source_path, local_path)
                        logger.info("Copied local asset", extra={"asset_id": asset.asset_id})
                    elif asset.source_url:
                        logger.info("Downloading asset", extra={"asset_id": asset.asset_id})
                        self._download_asset(asset.source_url, local_path)
                    else:
                        raise RuntimeError("No source URL or local path available")
                except Exception as exc:
                    logger.warning("Asset unavailable; generating placeholder clip. Error: %s", exc)
                    local_path = self._create_placeholder_clip(asset.asset_id)
                    placeholder_used = True
            else:
                logger.debug("Asset cached", extra={"asset_id": asset.asset_id})

            downloaded_assets.append(
                {
                    "id": asset.asset_id,
                    "local_path": str(local_path),
                    "keywords": asset.keywords,
                    "license": asset.license,
                    "source_url": asset.source_url,
                    "placeholder": placeholder_used,
                }
            )

        return {
            "assets": downloaded_assets,
            "requested_keywords": list(requested_keywords),
            "assets_dir": str(self.download_dir),
        }

    def _load_manifest(self) -> list[AssetDescriptor]:
        if not self.manifest_path.exists():
            raise FileNotFoundError(
                f"Stock manifest not found at {self.manifest_path}. Please ensure assets are configured."
            )
        with self.manifest_path.open("r", encoding="utf-8") as file:
            raw_manifest = json.load(file)
        return [AssetDescriptor.from_dict(entry) for entry in raw_manifest]

    def _select_assets(
        self, manifest: list[AssetDescriptor], requested_keywords: Iterable[str]
    ) -> list[AssetDescriptor]:
        keywords = {keyword.lower() for keyword in requested_keywords}
        if not keywords:
            return manifest[:3]
        scored: list[tuple[int, AssetDescriptor]] = []
        for asset in manifest:
            score = sum(1 for keyword in asset.keywords if keyword.lower() in keywords)
            scored.append((score, asset))
        scored.sort(key=lambda item: item[0], reverse=True)
        top = [asset for score, asset in scored if score > 0]
        if len(top) < 2:
            top = [asset for _, asset in scored]
        return top[:3]

    def _download_asset(self, url: str, destination: Path) -> None:
        try:
            with httpx.stream("GET", url, timeout=60) as response:
                response.raise_for_status()
                with destination.open("wb") as file_handle:
                    for chunk in response.iter_bytes():
                        file_handle.write(chunk)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Failed to download asset from {url}: {exc}") from exc

    def _create_placeholder_clip(self, asset_id: str) -> Path:
        output_path = self.placeholder_dir / f"{asset_id}_placeholder.mp4"
        if output_path.exists():
            return output_path

        clip = ColorClip(size=(1080, 1920), color=(48, 10, 85), duration=6)
        logger.info("Generating placeholder clip", extra={"asset_id": asset_id})
        clip.write_videofile(
            str(output_path),
            codec="libx264",
            audio=False,
            fps=24,
            preset="medium",
            threads=2,
        )
        clip.close()
        return output_path
