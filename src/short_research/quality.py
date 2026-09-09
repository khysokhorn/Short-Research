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

CRITIC_SYSTEM = """You are a demanding short-form retention, story-logic, and continuity editor. Score the script
scene by scene. Penalize slow context, generic visuals, repeated beats, weak escalation, confusing narration,
unsupported claims, broken cause-and-effect, character drift, impossible geography, silent-story beats that need
explanation, and a payoff that merely repeats the hook. Apply the WHY-NEXT test between every adjacent pair of
scenes: the next beat should happen because of the previous beat. Scores must be useful, not inflated. Provide
concrete rewrite instructions."""

REWRITE_SYSTEM = """You are a surgical YouTube Shorts rewrite editor and continuity supervisor. Rewrite only what
is weak according to the critic. Preserve verified facts, uncertainty, requested runtime, locked character identity,
winning hook/angle/payoff, established geography, story mode, and every strong scene. Repair cause-and-effect and
scene-boundary continuity. Return a complete replacement package even when only a subset of scenes changes."""

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
        silent_instruction = (
            "This is a silent story. Give silent_readability_score real weight: the danger, goal, decisions, "
            "consequences, character count, near-failure, and final safety must be visually understandable without "
            "narration, captions, or on-screen text. "
            if package.story_mode == "silent_story"
            else ""
        )
        prompt = (
            "Critique this complete short. Scores under 70 should indicate a material problem; 85+ should be rare. "
            "Check every factual claim against the embedded research guardrails. "
            "Score causality, character consistency, spatial continuity, silent readability, and emotional payoff. "
            "For every adjacent scene pair ask: 'Why does the next scene happen because of this one?' If the answer "
            "is only 'because the writer moved on', causality should fail. Verify Scene N end_state is physically "
            "compatible with Scene N+1 start_state, characters do not appear/disappear/duplicate, locations and "
            "screen direction stay coherent, and solution objects are established before use. "
            + silent_instruction
            + "\n\n"
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

    def rewrite(
        self,
        package: ShortPackage,
        critique: ShortCritique,
        *,
        scene_threshold: int = 75,
    ) -> ShortPackage:
        weak_scene_indices: set[int] = set()
        continuity_weak_indices: set[int] = set()
        valid_indices = {scene.index for scene in package.scenes}

        for item in critique.scene_critiques:
            all_scores = (
                item.retention_score,
                item.visual_novelty_score,
                item.clarity_score,
                item.causality_score,
                item.character_consistency_score,
                item.spatial_continuity_score,
                item.silent_readability_score,
                item.emotional_payoff_score,
            )
            if min(all_scores) < scene_threshold:
                weak_scene_indices.add(item.scene_index)

            continuity_scores = (
                item.causality_score,
                item.character_consistency_score,
                item.spatial_continuity_score,
            )
            if min(continuity_scores) < scene_threshold:
                continuity_weak_indices.add(item.scene_index)

        # A continuity failure often lives on a scene boundary, so allow the
        # rewrite to repair the neighboring beat instead of patching one shot in isolation.
        for scene_index in continuity_weak_indices:
            for candidate in (scene_index - 1, scene_index, scene_index + 1):
                if candidate in valid_indices:
                    weak_scene_indices.add(candidate)

        weak_instruction = (
            f"Only scenes with these indices may be replaced: {sorted(weak_scene_indices)}. "
            "All other scene objects must stay semantically unchanged. For rewritten adjacent scenes, make each "
            "end_state physically compatible with the next start_state."
            if weak_scene_indices
            else "No individual weak scene was identified; make only the minimum global changes needed."
        )
        package_for_prompt = package.model_dump_json(indent=2, exclude={"research": {"sources"}})
        prompt = f"""Rewrite the package so its weakest dimensions improve materially.
Do not change topic, winning hook, winning angle, payoff, duration, audience, story mode, factual guardrails,
locked character identities, or established location map.
{weak_instruction}

Causality contract:
- Every action-driven scene should expose start_state -> obstacle -> decision -> action -> consequence -> end_state.
- Scene N+1 must happen because of Scene N; do not connect beats with coincidence or unexplained relocation.
- Preserve characters_present, markings, proportions, and identity unless the story visibly changes who is present.
- Preserve spatial geography and screen direction unless a visible turn/reversal motivates the change.
- Do not introduce a solution object in the same instant it solves the problem.
- If story_mode is silent_story, use no narration, captions, or on-screen text and make every beat visually legible.

Keep scene timing chronological and ending close to {package.duration_seconds} seconds. Return the entire ShortPackage.

CRITIQUE:\n{critique.model_dump_json(indent=2)}

PACKAGE:\n{package_for_prompt}
"""
        result = self.llm.complete_json(
            system=REWRITE_SYSTEM,
            user=prompt,
            schema=ShortPackage,
            task="rewrite",
            temperature=0.55,
        )
        rewritten = ShortPackage.model_validate(result.model_dump())

        if weak_scene_indices:
            replacements = {scene.index: scene for scene in rewritten.scenes}
            merged_scenes = []
            for original in package.scenes:
                replacement = replacements.get(original.index)
                if original.index in weak_scene_indices and replacement is not None:
                    replacement.start_second = original.start_second
                    replacement.end_second = original.end_second
                    merged_scenes.append(replacement)
                else:
                    merged_scenes.append(original)
            rewritten.scenes = merged_scenes
            rewritten.narration = " ".join(scene.narration.strip() for scene in merged_scenes if scene.narration.strip())

        rewritten.topic = package.topic
        rewritten.hook = package.hook
        rewritten.core_angle = package.core_angle
        rewritten.payoff = package.payoff
        rewritten.duration_seconds = package.duration_seconds
        rewritten.style = package.style
        rewritten.audience = package.audience
        rewritten.story_mode = package.story_mode
        rewritten.continuity_rules = package.continuity_rules
        rewritten.location_map = package.location_map
        rewritten.characters = package.characters
        rewritten.research = package.research

        if rewritten.story_mode == "silent_story":
            rewritten.narration = ""
            for scene in rewritten.scenes:
                scene.narration = ""
                scene.on_screen_text = ""

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
