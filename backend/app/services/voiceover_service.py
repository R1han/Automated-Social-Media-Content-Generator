"""Voiceover synthesis service backed by ElevenLabs streaming API."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from ..core.config import get_settings
try:  # pragma: no cover - optional dependency at runtime
    from elevenlabs import VoiceSettings  # type: ignore[import-untyped]
    from elevenlabs.client import ElevenLabs  # type: ignore[import-untyped]
except Exception:  # pragma: no cover
    VoiceSettings = None  # type: ignore[assignment]
    ElevenLabs = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class VoiceoverService:
    """Streams synthesized audio into the outputs directory."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.output_dir = Path(self.settings.outputs_dir) / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.voice_id = self.settings.tts_voice_id
        self.model_id = self.settings.tts_model
        self.client: Any | None = None
        self.fallback_voiceover = Path(self.settings.outputs_dir) / "audio" / "demo-1762681313183_voiceover.mp3"

        api_key = self.settings.tts_api_key
        if api_key and ElevenLabs is not None:
            try:
                self.client = ElevenLabs(api_key=api_key)
            except Exception as exc:  # pragma: no cover
                logger.warning("Failed to initialize ElevenLabs client: %s", exc)
                self.client = None

    def synthesize(self, script: str, run_name: str) -> dict[str, Any]:
        if not script.strip():
            raise ValueError("Cannot synthesize an empty script")

        output_path = self.output_dir / f"{run_name}_voiceover.mp3"
        if self.client is None:
            logger.warning("ElevenLabs TTS not configured; using fallback voiceover if available")
            fallback = self._fallback_audio(output_path)
            return fallback

        temp_path = self.output_dir / f"{uuid.uuid4().hex}.mp3"

        try:
            logger.info("Generating voiceover audio", extra={"run": run_name, "provider": "elevenlabs"})
            stream = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=script,
                model_id=self.model_id,
                output_format="mp3_44100_128",
                optimize_streaming_latency="0",
                voice_settings=self._voice_settings(),
            )

            with open(temp_path, "wb") as handle:
                for chunk in stream:
                    if isinstance(chunk, bytes):
                        handle.write(chunk)
                    elif chunk:
                        handle.write(str(chunk).encode("utf-8"))

            temp_path.replace(output_path)
            return {
                "voiceover_path": str(output_path),
                "status": "generated",
                "voice": self.voice_id,
                "provider": "elevenlabs",
                "alignment_path": None,
            }
        except Exception as exc:  # pragma: no cover
            logger.warning("Voiceover synthesis failed: %s", exc)
            temp_path.unlink(missing_ok=True)
            fallback = self._fallback_audio(output_path, error=str(exc))
            return fallback

    def _voice_settings(self):
        if VoiceSettings is None:
            return None
        try:
            return VoiceSettings(
                stability=0.0,
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,
            )
        except Exception:  # pragma: no cover
            return None

    def _fallback_audio(self, output_path: Path, error: str | None = None) -> dict[str, Any]:
        if self.fallback_voiceover.is_file():
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(self.fallback_voiceover.read_bytes())
                logger.info("Applied fallback voiceover", extra={"source": str(self.fallback_voiceover), "target": str(output_path)})
                return {
                    "voiceover_path": str(output_path),
                    "status": "fallback",
                    "source": str(self.fallback_voiceover),
                    "error": error,
                }
            except Exception as exc:  # pragma: no cover
                logger.warning("Failed to apply fallback voiceover: %s", exc)
        logger.warning("Fallback voiceover not available; continuing without audio")
        return {
            "voiceover_path": str(output_path),
            "status": "failed",
            "error": error or "tts_unavailable",
            "fallback_available": False,
        }
