from __future__ import annotations

import json

from .llm import OpenAICompatibleLLM
from .models import (
    AngleCompetition,
    PackagingVariants,
    ReferenceVideoAnalysis,
    ResearchBrief,
    ShortCritique,
    ShortPackage,
)
from .presets import ChannelPreset

ANGLE_SYSTEM = """You are a senior YouTube Shorts concept editor. Generate genuinely different story angles, not
five paraphrases. For each angle generate exactly five distinct hooks and score them for curiosity, clarity,
visual potential, and truthfulness. Choose the strongest angle+hook combination for a factual short. Never reward
a hook for being misleading."""

CRITIC_SYSTEM = """You are a demanding short-form retention editor. Score the script scene by scene. Penalize slow
context, generic visuals, repeated beats, weak escalation, confusing narration, unsupported claims, and a payoff
that merely repeats the hook. Scores must be useful, not inflated. Provide concrete rewrite instructions."""

REWRITE_SYSTEM = """You are a surgical YouTube Shorts rewrite editor. Rewrite the supplied package using the critic's
priorities. Preserve verified facts, uncertainty, requested runtime, character continuity, and the winning angle.
Fix weak scenes rather than changing things that already work. Return a complete replacement package."""

PACKAGING_SYSTEM = """You package YouTube Shorts for discovery without misleading clickbait. Produce meaningfully
different factual title variants and thumbnail concepts. Thumbnail concepts must be visually legible on mobile,
use minimal overlay text, and describe one clear focal image rather than a collage."""


class QualityEngine:
    def __init__(self, llm: OpenAICompatibleLLM) -> None:
        self.llm = llm

    def compete_angles(
        self,
        brief: ResearchBrief,
        *,
        style: str,
        audience: str,
        preset: ChannelPreset | None = None,
        reference: ReferenceVideoAnalysis | None = None,
    ) -> AngleCompetition:
        prompt = f"""Create exactly 5 competing angles for this short and exactly 5 hooks per angle.
The candidates must differ in narrative engine (contradiction, escalation, mystery, consequence, comparison, etc.).
Select one angle and one hook using zero-based selected_* indices.

STYLE: {style}
AUDIENCE: {audience}
RESEARCH:\n{json.dumps(brief.model_dump(exclude={'sources'}), ensure_ascii=False, indent=2)}
"""
        if preset:
            prompt += f"\n\n{preset.prompt_fragment()}"
        if reference:
            prompt += (
                "\n\nREFERENCE PATTERNS (abstract inspiration only; do not copy expression):\n"
                + json.dumps(reference.model_dump(exclude={"transcript_excerpt"}), ensure_ascii=False, indent=2)
            )
        result = self.llm.complete_json(
            system=ANGLE_SYSTEM,
            user=prompt,
            schema=AngleCompetition,
            task="angle_competition",
            temperature=0.9,
        )
        competition = AngleCompetition.model_validate(result.model_dump())
        if len(competition.candidates) < 3:
            raise ValueError("Angle competition must return at least 3 candidates")
        competition.selected()
        return competition

    def critique(self, package: ShortPackage) -> ShortCritique:
        prompt = (
            "Critique this complete short. Scores under 70 should indicate a material problem; 85+ should be rare. "
            "Check every factual claim against the embedded research guardrails.\n\n"
            + package.model_dump_json(indent=2, exclude={"research": {"sources"}})
        )
        result = self.llm.complete_json(
            system=CRITIC_SYSTEM,
            user=prompt,
            schema=ShortCritique,
            task="critic",
            temperature=0.2,
        )
        return ShortCritique.model_validate(result.model_dump())

    def rewrite(self, package: ShortPackage, critique: ShortCritique) -> ShortPackage:
        prompt = f"""Rewrite the package so its weakest dimensions improve materially.
Do not change topic, winning hook, winning angle, payoff, duration, audience, or factual guardrails.
Keep scene timing chronological and ending close to {package.duration_seconds} seconds. Return the entire ShortPackage.

CRITIQUE:\n{critique.model_dump_json(indent=2)}

PACKAGE:\n{package.model_dump_json(indent=2)}
"""
        result = self.llm.complete_json(
            system=REWRITE_SYSTEM,
            user=prompt,
            schema=ShortPackage,
            task="rewrite",
            temperature=0.55,
        )
        rewritten = ShortPackage.model_validate(result.model_dump())
        rewritten.topic = package.topic
        rewritten.hook = package.hook
        rewritten.core_angle = package.core_angle
        rewritten.payoff = package.payoff
        rewritten.duration_seconds = package.duration_seconds
        rewritten.style = package.style
        rewritten.audience = package.audience
        rewritten.research = package.research
        return rewritten

    def packaging(self, package: ShortPackage) -> PackagingVariants:
        prompt = f"""Create 5 YouTube title variants and 4 thumbnail concepts for this short.
Score each 0-100. Use zero-based recommended indices. Do not add claims absent from the research.

SHORT:\n{package.model_dump_json(indent=2, exclude={'research': {'sources'}})}
"""
        result = self.llm.complete_json(
            system=PACKAGING_SYSTEM,
            user=prompt,
            schema=PackagingVariants,
            task="packaging",
            temperature=0.8,
        )
        return PackagingVariants.model_validate(result.model_dump())
