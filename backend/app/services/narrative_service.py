"""Narrative and caption generation powered by Gemini with graceful fallback."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

try:  # pragma: no cover - optional dependency
    from google import genai
except ImportError:  # pragma: no cover - handled via fallback path
    genai = None  # type: ignore[assignment]

from ..core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class NarrativePayload:
    """Structured storytelling output for the pipeline."""

    master_script: str
    instagram_caption: str
    instagram_hashtags: list[str]
    tiktok_caption: str
    tiktok_hashtags: list[str]
    cta: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "script": self.master_script,
            "instagram_caption": self.instagram_caption,
            "instagram_hashtags": self.instagram_hashtags,
            "tiktok_caption": self.tiktok_caption,
            "tiktok_hashtags": self.tiktok_hashtags,
            "cta": self.cta,
        }


class NarrativeService:
    """Generates luxury-aligned storytelling assets."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.client: Any | None = None
        if self.settings.gemini_api_key and genai is not None:
            try:
                self.client = genai.Client(api_key=self.settings.gemini_api_key)
            except Exception as exc:  # pragma: no cover
                logger.warning("Gemini configuration failed: %s", exc)
                self.client = None

    def generate(self, run_name: str, keywords: list[str], platform_targets: list[str]) -> NarrativePayload:
        """Return narrative artefacts tailored to both IG and TikTok."""

        prompt = self._build_prompt(run_name, keywords, platform_targets)
        if self.client is not None:
            try:
                logger.info("Invoking Gemini for narrative generation", extra={"run": run_name})
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                content = self._parse_response(response)
                return content
            except Exception as exc:  # pragma: no cover - fall back on handcrafted copy
                logger.warning("Gemini narrative generation failed, using fallback. Error: %s", exc)

        logger.info("Falling back to deterministic narrative generation", extra={"run": run_name})
        return self._fallback_narrative(keywords)

    def _build_prompt(self, run_name: str, keywords: list[str], platforms: list[str]) -> str:
        keyword_str = ", ".join(keywords) if keywords else "luxury education, neuroscience, bespoke parenting"
        platform_str = ", ".join(platforms) if platforms else "instagram, tiktok"
        return f"""
        You are the creative director for Masterminds Academy (https://mastermindsacademy.org),
        a luxury, neuroscience-led educational institution for high-net-worth families in the UAE and US.

        Generate a JSON object with the following keys:
        - script: 90-120 word master narration in British English, majestic yet warm.
        - instagram_caption: 3-4 sentence caption tailored to organic + lead generation.
        - instagram_hashtags: Array of 6-8 concise hashtags targeting luxury education parents.
        - tiktok_caption: 120 character hook-driven caption with a soft luxury appeal.
        - tiktok_hashtags: Array of 5-6 emotionally resonant hashtags suited to TikTok trends.
        - cta: A clear, aspirational call-to-action inviting a private tour or consultation.

        Guardrails:
        - Maintain authentic human tone, referencing neuroscience-backed learning and bespoke programs.
        - Weave in UAE/US context subtly.
        - Avoid clichés, emojis, and salesy language.
        - Do not include quotation marks unless necessary for quoting.

        Run Name: {run_name}
        Desired Platforms: {platform_str}
        Inspiration Keywords: {keyword_str}

        Return only valid JSON with string keys matching the schema above.
        """

    def _parse_response(self, response: Any) -> NarrativePayload:
        data: dict[str, Any]
        if hasattr(response, "text") and response.text:
            text_payload = response.text
        try:
            text_payload = text_payload.strip("```json").strip("```").strip()
            data = json.loads(text_payload)
        except json.JSONDecodeError as exc:
            logger.warning("Unable to parse Gemini response, raw text returned. Error: %s", exc)
            raise RuntimeError("Gemini response was not valid JSON") from exc
        except json.JSONDecodeError as exc:
            logger.warning("Unable to parse Gemini response, raw text returned. Error: %s", exc)
            raise RuntimeError("Gemini response was not valid JSON") from exc

        return NarrativePayload(
            master_script=str(data.get("script", "")),
            instagram_caption=str(data.get("instagram_caption", "")),
            instagram_hashtags=[str(tag) for tag in data.get("instagram_hashtags", [])],
            tiktok_caption=str(data.get("tiktok_caption", "")),
            tiktok_hashtags=[str(tag) for tag in data.get("tiktok_hashtags", [])],
            cta=str(data.get("cta", "Book a Private Discovery Tour")),
        )

    def _fallback_narrative(self, keywords: list[str]) -> NarrativePayload:
        keyword_line = ", ".join(keywords[:3]) if keywords else "neuroscience-led, bespoke pathways"
        script = (
            "At Masterminds Academy, every detail is choreographed by neuroscientists and designers "
            "to ignite a child's emerging genius. From Dubai to New York, our ateliers, sensory "
            "labs, and mentorship suites craft fearless thinkers prepared for a changing world."
        )
        instagram_caption = (
            "Where neuroscience meets bespoke education. Our ateliers, bi-lateral learning studios, and "
            "elite faculty collaborate with families to craft luminous futures. Book a private tour of "
            "Masterminds Academy and experience the art of elevated learning."
        )
        tiktok_caption = (
            "Inside the academy rewiring education for visionary families. From sensory labs to bespoke coaching—"
            "discover how we cultivate audacious young minds."
        )
        return NarrativePayload(
            master_script=script,
            instagram_caption=instagram_caption,
            instagram_hashtags=["LuxuryEducation", "NeuroscienceLearning", "ParenthoodRedefined", "DubaiFamilies", "USParents", "FutureMinds", "HNWParenting"],
            tiktok_caption=tiktok_caption,
            tiktok_hashtags=["LuxuryLearning", "STEMKids", "NeuroscienceEducation", "DubaiToNYC", "FutureLeaders"],
            cta="Explore our bespoke programs – book a private tour.",
        )
