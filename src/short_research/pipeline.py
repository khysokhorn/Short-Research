from __future__ import annotations

import json
import re
from pathlib import Path

from .llm import OpenAICompatibleLLM
from .models import (
    AngleCompetition,
    PipelineRun,
    ReferenceVideoAnalysis,
    ResearchBrief,
    ResearchSource,
    ShortPackage,
)
from .presets import ChannelPreset
from .quality import QualityEngine
from .research import WebResearcher
from .video_analysis import ReferenceVideoAnalyzer

RESEARCH_SYSTEM = """You are a research editor for factual, high-retention short-form videos.
Separate verified facts from uncertainty. Prefer surprising, visual facts that can be explained quickly.
Never invent a fact just to make the story more dramatic. Source indices refer to the supplied source list."""

SCRIPT_SYSTEM = """You are a YouTube Shorts writer and visual director.
Optimize for retention without clickbait lies. The first 1.5 seconds must create immediate curiosity.
Use fast escalation, pattern interrupts every few seconds, a clear payoff, and visual instructions that are
specific enough for an AI video system. Avoid generic B-roll directions. Keep spoken narration natural."""


class ShortResearchPipeline:
    def __init__(self, *, llm: OpenAICompatibleLLM, researcher: WebResearcher | None = None) -> None:
        self.llm = llm
        self.researcher = researcher or WebResearcher()
        self.quality = QualityEngine(llm)

    def generate(
        self,
        topic: str,
        *,
        duration_seconds: int = 45,
        style: str = "cinematic fun fact",
        audience: str = "general YouTube Shorts audience",
        max_sources: int = 6,
    ) -> ShortPackage:
        """Backward-compatible basic generation path."""
        raw_sources = self._research(topic, max_sources)
        brief = self._build_research_brief(topic, raw_sources)
        package = self._build_short_package(
            brief,
            duration_seconds=duration_seconds,
            style=style,
            audience=audience,
        )
        package.research.sources = raw_sources
        return package

    def generate_full(
        self,
        topic: str,
        *,
        duration_seconds: int = 45,
        style: str = "cinematic fun fact",
        audience: str = "general YouTube Shorts audience",
        max_sources: int = 6,
        preset: ChannelPreset | None = None,
        reference_source: str | None = None,
        reference_visual: bool = False,
        critic_threshold: int = 78,
        max_rewrite_passes: int = 2,
    ) -> PipelineRun:
        """Run every pre-production milestone through packaging, stopping before ArcReel by default."""
        if preset:
            style = preset.style
            audience = preset.audience

        raw_sources = self._research(topic, max_sources)
        brief = self._build_research_brief(topic, raw_sources)
        brief.sources = raw_sources

        reference: ReferenceVideoAnalysis | None = None
        if reference_source:
            reference = ReferenceVideoAnalyzer(self.llm).analyze(
                reference_source,
                visual=reference_visual,
            )

        competition = self.quality.compete_angles(
            brief,
            style=style,
            audience=audience,
            preset=preset,
            reference=reference,
        )
        package = self._build_short_package(
            brief,
            duration_seconds=duration_seconds,
            style=style,
            audience=audience,
            competition=competition,
            preset=preset,
            reference=reference,
        )
        package.research.sources = raw_sources

        critique = self.quality.critique(package)
        rewrite_passes = 0
        while critique.overall_score < critic_threshold and rewrite_passes < max_rewrite_passes:
            package = self.quality.rewrite(package, critique)
            package.research.sources = raw_sources
            rewrite_passes += 1
            critique = self.quality.critique(package)

        packaging = self.quality.packaging(package)
        return PipelineRun(
            package=package,
            angle_competition=competition,
            critique=critique,
            packaging=packaging,
            reference_analysis=reference,
            rewrite_passes=rewrite_passes,
        )

    def _research(self, topic: str, max_sources: int) -> list[ResearchSource]:
        raw_sources = self.researcher.search(topic, max_sources=max_sources)
        if not raw_sources:
            raise RuntimeError("Research returned no sources. Try a more specific topic or check network access.")
        return raw_sources

    def _build_research_brief(self, topic: str, sources: list[ResearchSource]) -> ResearchBrief:
        source_text = "\n\n".join(
            f"SOURCE [{i}]\nTITLE: {s.title}\nURL: {s.url}\nSNIPPET: {s.snippet}\nTEXT: {s.extracted_text}"
            for i, s in enumerate(sources, start=1)
        )
        prompt = f"""Research this topic for a short video: {topic}

Create a concise factual brief. Put source references like [1] or [2] inside each fact string when supported.
If sources disagree or evidence is weak, put that in uncertainties rather than presenting it as fact.

{source_text}"""
        result = self.llm.complete_json(
            system=RESEARCH_SYSTEM,
            user=prompt,
            schema=ResearchBrief,
            task="research",
            temperature=0.2,
        )
        brief = ResearchBrief.model_validate(result.model_dump())
        brief.topic = topic
        brief.sources = []
        return brief

    def _build_short_package(
        self,
        brief: ResearchBrief,
        *,
        duration_seconds: int,
        style: str,
        audience: str,
        competition: AngleCompetition | None = None,
        preset: ChannelPreset | None = None,
        reference: ReferenceVideoAnalysis | None = None,
    ) -> ShortPackage:
        brief_json = json.dumps(brief.model_dump(exclude={"sources"}), ensure_ascii=False, indent=2)
        selected_instruction = ""
        selected_hook = None
        selected_angle = None
        if competition:
            selected_angle, selected_hook = competition.selected()
            selected_instruction = f"""
WINNING ANGLE: {selected_angle.name} — {selected_angle.premise}
WINNING PAYOFF: {selected_angle.payoff}
MANDATORY OPENING HOOK: {selected_hook.text}
VISUAL ENGINE: {selected_angle.visual_engine}
"""

        prompt = f"""Turn this research brief into a {duration_seconds}-second vertical YouTube Short.

STYLE: {style}
AUDIENCE: {audience}
FORMAT: 9:16
{selected_instruction}
Rules:
- Hook must work in roughly 1.5 seconds.
- Reach the central question/problem immediately; no intro greeting.
- Give every scene a concrete visual direction and camera instruction.
- Add a retention device or pattern interrupt about every 3-6 seconds.
- Scene times must start at 0, be chronological, and end close to {duration_seconds} seconds.
- Narration should fit the requested duration; do not stuff excessive words into the runtime.
- Preserve uncertainty from the research brief.
- Do not include unsupported facts.
- youtube_title should be compelling but factual.

RESEARCH BRIEF:\n{brief_json}"""
        if preset:
            prompt += f"\n\n{preset.prompt_fragment()}"
        if reference:
            prompt += (
                "\n\nREFERENCE ANALYSIS — borrow abstract retention patterns only, never wording or exact shots:\n"
                + reference.model_dump_json(indent=2, exclude={"transcript_excerpt"})
            )

        result = self.llm.complete_json(
            system=SCRIPT_SYSTEM,
            user=prompt,
            schema=ShortPackage,
            task="script",
            temperature=0.65,
        )
        package = ShortPackage.model_validate(result.model_dump())
        package.topic = brief.topic
        package.duration_seconds = duration_seconds
        package.style = style
        package.audience = audience
        package.research = brief
        if selected_hook is not None:
            package.hook = selected_hook.text
        if selected_angle is not None:
            package.core_angle = selected_angle.premise
            package.payoff = selected_angle.payoff
        return package


def export_run(run: PipelineRun, output_root: Path) -> tuple[Path, Path]:
    package = run.package
    slug = _slugify(package.working_title or package.topic)
    output_dir = output_root / slug
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "research-brief.json").write_text(
        package.research.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "angle-competition.json").write_text(
        run.angle_competition.model_dump_json(indent=2), encoding="utf-8"
    )
    json_path = output_dir / "short-package.json"
    json_path.write_text(package.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "short-critique.json").write_text(run.critique.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "packaging-variants.json").write_text(
        run.packaging.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "run-summary.json").write_text(
        json.dumps(
            {
                "rewrite_passes": run.rewrite_passes,
                "final_critic_score": run.critique.overall_score,
                "reference_analysis": run.reference_analysis is not None,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if run.reference_analysis:
        (output_dir / "reference-analysis.json").write_text(
            run.reference_analysis.model_dump_json(indent=2), encoding="utf-8"
        )
    screenplay_path = output_dir / "arcreel-screenplay.md"
    screenplay_path.write_text(to_arcreel_screenplay(package), encoding="utf-8")
    return json_path, screenplay_path


def export_package(package: ShortPackage, output_root: Path) -> tuple[Path, Path]:
    """Backward-compatible package-only exporter."""
    slug = _slugify(package.working_title or package.topic)
    output_dir = output_root / slug
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "short-package.json"
    screenplay_path = output_dir / "arcreel-screenplay.md"
    json_path.write_text(package.model_dump_json(indent=2), encoding="utf-8")
    screenplay_path.write_text(to_arcreel_screenplay(package), encoding="utf-8")
    return json_path, screenplay_path


def to_arcreel_screenplay(package: ShortPackage) -> str:
    lines: list[str] = [
        f"# {package.working_title}",
        "",
        "## Project Overview",
        f"**Topic:** {package.topic}",
        f"**Format:** YouTube Short · 9:16 · {package.duration_seconds}s",
        f"**Style:** {package.style}",
        f"**Audience:** {package.audience}",
        f"**Core angle:** {package.core_angle}",
        f"**Hook:** {package.hook}",
        f"**Payoff:** {package.payoff}",
        "",
    ]

    if package.characters:
        lines.extend(["## Cast", ""])
        for character in package.characters:
            lines.extend([
                f"### {character.name} — {character.role}",
                character.visual_description,
                f"**Consistency:** {character.consistency_notes}" if character.consistency_notes else "",
                "",
            ])

    lines.extend(["## Full Narration", "", package.narration, "", "## Scene Breakdown", ""])
    for scene in package.scenes:
        lines.extend([
            f"### Scene {scene.index} — {scene.start_second:.1f}s to {scene.end_second:.1f}s",
            f"**Purpose:** {scene.purpose}",
            f"**Narration:** {scene.narration}",
            f"**Visual:** {scene.visual_direction}",
            f"**Camera:** {scene.camera}",
            f"**On-screen text:** {scene.on_screen_text or 'None'}",
            f"**Sound:** {scene.sound_design or 'None'}",
            f"**Transition:** {scene.transition or 'Cut'}",
            f"**Retention device:** {scene.retention_device or 'None'}",
            "",
        ])

    lines.extend(["## Research Guardrails", ""])
    lines.extend(f"- {fact}" for fact in package.research.key_facts)
    if package.research.uncertainties:
        lines.extend(["", "### Uncertainties / do not overclaim"])
        lines.extend(f"- {item}" for item in package.research.uncertainties)

    lines.extend(["", "## Sources", ""])
    for i, source in enumerate(package.research.sources, start=1):
        lines.append(f"{i}. {source.title} — {source.url}")

    return "\n".join(lines).strip() + "\n"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:70] or "short"
