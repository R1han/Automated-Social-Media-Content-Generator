"""Video editing utilities for assembling demo deliverables."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

from moviepy import AudioFileClip, ColorClip, VideoFileClip, concatenate_videoclips  # type: ignore[import-untyped]

try:  # pragma: no cover - optional dependency path differences across MoviePy versions
    from moviepy.audio.AudioClip import AudioArrayClip  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    AudioArrayClip = None  # type: ignore[assignment]

try:  # pragma: no cover
    from moviepy.audio.compositing import CompositeAudioClip  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    CompositeAudioClip = None  # type: ignore[assignment]

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class EditingService:
    """Creates platform-specific cuts using MoviePy."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.outputs_dir = Path(self.settings.outputs_dir)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    def produce_videos(
        self,
        video_paths: Iterable[str],
        voiceover_path: str,
        run_name: str,
    ) -> dict[str, str]:
        """Render Instagram and TikTok videos using provided assets."""

        clips = self._load_clips(video_paths)
        placeholder_clip: ColorClip | None = None
        if not clips:
            logger.warning("No valid clips supplied; generating branded placeholder sequence")
            placeholder_clip = ColorClip(size=(1080, 1920), color=(48, 10, 85), duration=12)
            clips = [placeholder_clip]  # type: ignore[list-item]

        voiceover_file = Path(voiceover_path) if voiceover_path else None
        audio_path: Path | None = self._resolve_audio_path(voiceover_file)
        logger.info(
            "Editing run voiceover resolution: run=%s input_path=%s resolved_path=%s exists=%s",
            run_name,
            voiceover_path,
            str(audio_path) if audio_path else None,
            audio_path.is_file() if audio_path else False,
        )

        instagram_path = self.outputs_dir / f"{run_name}_instagram.mp4"
        tiktok_path = self.outputs_dir / f"{run_name}_tiktok.mp4"

        try:
            self._render_variant(
                clips,
                audio_path,
                instagram_path,
                width=1080,
                height=1920,
                fps=24,
                max_duration=45,
            )
            self._render_variant(
                clips,
                audio_path,
                tiktok_path,
                width=1080,
                height=1920,
                fps=30,
                max_duration=35,
            )
        finally:
            for clip in clips:
                clip.close()
            if placeholder_clip is not None:
                placeholder_clip.close()

        return {
            "instagram_video": str(instagram_path),
            "tiktok_video": str(tiktok_path),
        }

    def _load_clips(self, paths: Iterable[str]) -> list[VideoFileClip]:
        loaded: list[VideoFileClip] = []
        for path in paths:
            clip: VideoFileClip | None = None
            try:
                try:
                    clip = VideoFileClip(path, audio=False, load_images=True)
                except TypeError:
                    clip = VideoFileClip(path, audio=False)
                # Force lazy readers to initialize so we can catch issues early.
                _ = clip.duration
                if getattr(clip, "reader", None) is None:
                    raise RuntimeError("Clip reader failed to initialize")
                loaded.append(clip)
            except Exception as exc:
                logger.warning("Unable to load clip %s: %s", path, exc)
                if clip is not None:
                    try:
                        clip.close()
                    except Exception:
                        pass
        return loaded

    def _render_variant(
        self,
        clips: list[VideoFileClip],
        audio_path: Path | None,
        output_path: Path,
        *,
        width: int,
        height: int,
        fps: int,
        max_duration: int,
    ) -> None:
        audio_clip: AudioFileClip | None = None
        working_audio_clip = None
        materialized_audio_clip: Any = None
        if audio_path is not None:
            try:
                audio_clip = AudioFileClip(str(audio_path))
                logger.info(
                    "Loaded voiceover clip: path=%s duration=%s",
                    str(audio_path),
                    getattr(audio_clip, "duration", None),
                )
                if AudioArrayClip is not None:
                    try:
                        fps_value = getattr(audio_clip, "fps", None) or 44100
                        waveform = audio_clip.to_soundarray(fps=fps_value)
                        if hasattr(waveform, "shape") and waveform.shape:
                            sample_count = int(waveform.shape[0])
                        else:
                            sample_count = len(waveform)
                        computed_duration = sample_count / float(fps_value)
                        logger.info(
                            "Materialized voiceover waveform: samples=%s fps=%s computed_duration=%s",
                            sample_count,
                            fps_value,
                            computed_duration,
                        )
                        materialized_audio_clip = AudioArrayClip(waveform, fps=fps_value)
                        if hasattr(materialized_audio_clip, "set_duration"):
                            materialized_audio_clip = materialized_audio_clip.set_duration(audio_clip.duration)  # type: ignore[attr-defined]
                        else:
                            # Some MoviePy builds expose duration as attribute only.
                            setattr(materialized_audio_clip, "duration", audio_clip.duration)
                    except Exception as exc:
                        logger.warning("Unable to materialize voiceover waveform: %s", exc)
            except Exception as exc:
                logger.warning("Unable to load voiceover track for %s: %s", output_path.name, exc)
                audio_clip = None
        else:
            logger.info("Voiceover clip absent, proceeding silently: output=%s", str(output_path))

        processed = []
        accumulated = 0.0
        for clip in clips:
            target_duration = min(clip.duration, 15)
            if target_duration < 5:
                target_duration = clip.duration
            segment = self._trim_clip(clip, target_duration)
            segment = self._resize_clip(segment, width, height)
            segment = self._crop_clip(segment, width, height)
            processed.append(segment)
            accumulated += segment.duration
            if accumulated >= max_duration:
                break

        if not processed:
            raise RuntimeError("No processed clips available for export")

        target_duration = None
        if audio_clip is not None:
            target_duration = min(max_duration, audio_clip.duration)

        segments_for_render = self._fit_segments_to_duration(processed, target_duration)
        assembled_duration = sum(segment.duration for segment in segments_for_render)
        logger.info(
            "Prepared segments for render: output=%s segments=%s duration=%s target=%s",
            str(output_path),
            len(segments_for_render),
            assembled_duration,
            target_duration,
        )

        if not segments_for_render:
            raise RuntimeError("Unable to assemble segments for export")

        final_clip = concatenate_videoclips(segments_for_render, method="compose")

        if audio_clip is not None:
            try:
                working_audio_clip = materialized_audio_clip or audio_clip
                if (
                    CompositeAudioClip is not None
                    and working_audio_clip is not None
                    and getattr(working_audio_clip, "is_audio_clip", False)
                ):
                    working_audio_clip = CompositeAudioClip([working_audio_clip])

                if hasattr(final_clip, "set_audio"):
                    final_clip = final_clip.set_audio(working_audio_clip)  # type: ignore[attr-defined]
                elif hasattr(final_clip, "with_audio"):
                    final_clip = final_clip.with_audio(working_audio_clip)  # type: ignore[attr-defined]
                else:
                    final_clip.audio = working_audio_clip  # type: ignore[attr-defined]
                logger.info(
                    "Attached original audio to final clip: output=%s audio_duration=%s video_duration=%s",
                    str(output_path),
                    getattr(working_audio_clip, "duration", None),
                    getattr(final_clip, "duration", None),
                )
            except Exception as exc:
                logger.warning("Failed to attach voiceover to %s: %s", output_path.name, exc)
                working_audio_clip = None

        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Rendering video", extra={"path": str(output_path)})
        try:
            final_clip.write_videofile(
                str(output_path),
                codec="libx264",
                audio_codec="aac",
                audio_bitrate="192k",
                fps=fps,
                preset="medium",
                threads=2,
                write_logfile=False,
            )
        finally:
            final_clip.close()
            self._close_clips(segments_for_render, processed)
            if (
                working_audio_clip is not None
                and working_audio_clip is not audio_clip
                and working_audio_clip is not materialized_audio_clip
            ):
                try:
                    working_audio_clip.close()
                except Exception:
                    pass
            if materialized_audio_clip is not None:
                try:
                    materialized_audio_clip.close()
                except Exception:
                    pass
            if audio_clip is not None:
                try:
                    audio_clip.close()
                except Exception:
                    pass
            validation_clip: VideoFileClip | None = None
            try:
                validation_clip = VideoFileClip(str(output_path))
                audio_duration = None
                if getattr(validation_clip, "audio", None) is not None:
                    audio_duration = getattr(validation_clip.audio, "duration", None)
                logger.info(
                    "Validation playback durations: output=%s video_duration=%s audio_duration=%s",
                    str(output_path),
                    getattr(validation_clip, "duration", None),
                    audio_duration,
                )
            except Exception as exc:
                logger.warning("Unable to validate rendered output %s: %s", str(output_path), exc)
            finally:
                if validation_clip is not None:
                    try:
                        validation_clip.close()
                    except Exception:
                        pass

    def _trim_clip(self, clip: VideoFileClip, duration: float) -> VideoFileClip:
        if duration >= clip.duration:
            return clip
        if hasattr(clip, "subclip"):
            return clip.subclip(0, duration)  # type: ignore[attr-defined]
        if hasattr(clip, "time_slice"):
            return clip.time_slice(0, duration)  # type: ignore[attr-defined]
        if hasattr(clip, "with_duration"):
            return clip.with_duration(duration)  # type: ignore[attr-defined]
        return clip

    def _resize_clip(self, clip: VideoFileClip, width: int, height: int) -> VideoFileClip:
        if not hasattr(clip, "resize") or not getattr(clip, "w", None) or not getattr(clip, "h", None):
            return clip

        target_ratio = width / height
        clip_ratio = clip.w / clip.h

        if clip_ratio < target_ratio:
            return clip.resize(width=width)  # type: ignore[attr-defined]
        return clip.resize(height=height)  # type: ignore[attr-defined]

    def _crop_clip(self, clip: VideoFileClip, width: int, height: int) -> VideoFileClip:
        if not hasattr(clip, "crop") or not getattr(clip, "w", None) or not getattr(clip, "h", None):
            return clip

        crop_width = min(width, clip.w)
        crop_height = min(height, clip.h)

        if crop_width == clip.w and crop_height == clip.h:
            return clip

        return clip.crop(
            width=crop_width,
            height=crop_height,
            x_center=clip.w / 2,
            y_center=clip.h / 2,
        )  # type: ignore[attr-defined]

    def _resolve_audio_path(self, voiceover_file: Path | None) -> Path | None:
        if voiceover_file is None:
            return None

        if voiceover_file.is_file():
            return voiceover_file.resolve()

        candidates = []
        if not voiceover_file.is_absolute():
            candidates.append(self.outputs_dir / voiceover_file)

            parts = voiceover_file.parts
            if parts and parts[0] == "outputs":
                candidates.append(self.outputs_dir / Path(*parts[1:]))

        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()

        logger.warning("Voiceover file missing; proceeding without audio", extra={"voiceover_path": str(voiceover_file)})
        return None

    def _fit_segments_to_duration(self, segments: list[VideoFileClip], target_duration: float | None) -> list[VideoFileClip]:
        """Scale or loop prepared segments so the timeline matches target duration."""
        if target_duration is None or not segments:
            return segments

        tolerance = 1e-3
        total_duration = sum(segment.duration for segment in segments)

        if abs(total_duration - target_duration) <= tolerance:
            return segments

        if total_duration > target_duration + tolerance:
            scale = target_duration / total_duration if total_duration else 1.0
            adjusted: list[VideoFileClip] = []
            accumulated = 0.0
            remaining_segments = len(segments)
            for index, segment in enumerate(segments):
                remaining_segments = len(segments) - index
                remaining_time = max(target_duration - accumulated, 0.0)
                if remaining_time <= tolerance:
                    break

                desired = segment.duration * scale
                # Ensure final segment absorbs any rounding difference.
                if remaining_segments == 1:
                    desired = remaining_time
                desired = max(min(desired, remaining_time), 0.0)

                if desired <= tolerance:
                    continue

                if desired >= segment.duration - tolerance:
                    adjusted.append(segment)
                    accumulated += segment.duration
                else:
                    trimmed = self._extract_segment(segment, desired)
                    adjusted.append(trimmed)
                    accumulated += min(desired, trimmed.duration)

            return adjusted

        adjusted = []
        accumulated = 0.0
        index = 0
        max_iterations = max(len(segments) * 10, 10)
        while accumulated < target_duration - tolerance and index < max_iterations:
            segment_index = index % len(segments)
            segment = segments[segment_index]
            remaining = target_duration - accumulated
            duration = min(segment.duration, remaining)
            if duration <= tolerance:
                break

            if index < len(segments) and duration >= segment.duration - tolerance:
                adjusted.append(segment)
            else:
                adjusted.append(self._extract_segment(segment, duration))

            accumulated += duration
            index += 1

        if accumulated < target_duration - tolerance:
            logger.warning(
                "Unable to extend video to match audio duration precisely; leaving gap",
                extra={"target_duration": target_duration, "achieved": accumulated},
            )

        return adjusted if adjusted else segments

    def _prepare_audio_clip(self, audio_clip: AudioFileClip, target_duration: float) -> AudioFileClip:
        tolerance = 1e-3
        if audio_clip.duration <= target_duration + tolerance and audio_clip.duration >= target_duration - tolerance:
            return audio_clip

        logger.info(
            "Voiceover and video durations differ",
            extra={"audio_duration": audio_clip.duration, "video_duration": target_duration},
        )
        return audio_clip

    def _close_clips(self, *clip_lists: Iterable[VideoFileClip]) -> None:
        seen: set[int] = set()
        for clip_list in clip_lists:
            for clip in clip_list:
                if clip is None:
                    continue
                key = id(clip)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    clip.close()
                except Exception:
                    pass

    def _extract_segment(self, clip: VideoFileClip, duration: float) -> VideoFileClip:
        tolerance = 1e-3
        if duration >= clip.duration - tolerance:
            return clip

        if hasattr(clip, "subclip"):
            try:
                return clip.subclip(0, duration)  # type: ignore[attr-defined]
            except Exception:
                pass

        if hasattr(clip, "time_slice"):
            try:
                return clip.time_slice(0, duration)  # type: ignore[attr-defined]
            except Exception:
                pass

        if hasattr(clip, "with_duration"):
            try:
                return clip.with_duration(duration)  # type: ignore[attr-defined]
            except Exception:
                pass

        if hasattr(clip, "set_duration"):
            try:
                return clip.set_duration(duration)  # type: ignore[attr-defined]
            except Exception:
                pass

        logger.warning("Clip provider lacks trimming primitives; using original duration", extra={"requested": duration, "actual": clip.duration})
        return clip

    def _extract_audio_segment(self, clip: AudioFileClip, duration: float) -> AudioFileClip:
        tolerance = 1e-3
        if duration >= getattr(clip, "duration", 0.0) - tolerance:
            return clip

        for attr in ("subclip", "time_slice", "with_duration", "set_duration"):
            if hasattr(clip, attr):
                handler = getattr(clip, attr)
                try:
                    if attr in {"with_duration", "set_duration"}:
                        return handler(duration)  # type: ignore[misc]
                    return handler(0, duration)  # type: ignore[misc]
                except Exception:
                    continue

        logger.warning(
            "Audio provider lacks trimming primitives; using original duration",
            extra={"requested": duration, "actual": getattr(clip, "duration", None)},
        )
        return clip
