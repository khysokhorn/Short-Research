from __future__ import annotations

import json
import re
from pathlib import Path

from .llm import OpenAICompatibleLLM
from .models import ResearchBrief, ResearchSource, ShortPackage
from .research import WebResearcher

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

    def generate(
        self,
        topic: str,
        *,
        duration_seconds: int = 45,
        style: str = "cinematic fun fact",
        audience: str = "general YouTube Shorts audience",
        max_sources: int = 6,
    ) -> ShortPackage:
        raw_sources = self.researcher.search(topic, max_sources=max_sources)
        if not raw_sources:
            raise RuntimeError("Research returned no sources. Try a more specific topic or check network access.")

        brief = self._build_research_brief(topic, raw_sources)
        package = self._build_short_package(
            brief,
            duration_seconds=duration_seconds,
            style=style,
            audience=audience,
        )
        package.research.sources = raw_sources
        return package

    def _build_research_brief(self, topic: str, sources: list[ResearchSource]) -> ResearchBrief:
        source_text = "\n\n".join(
            f"SOURCE [{i}]\nTITLE: {s.title}\nURL: {s.url}\nSNIPPET: {s.snippet}\nTEXT: {s.extracted_text}"
            for i, s in enumerate(sources, start=1)
        )
        prompt = f"""Research this topic for a short video: {topic}

Create a concise factual brief. Put source references like [1] or [2] inside each fact string when supported.
If sources disagree or evidence is weak, put that in uncertainties rather than presenting it as fact.

{source_text}"""
        result = self.llm.complete_json(system=RESEARCH_SYSTEM, user=prompt, schema=ResearchBrief)
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
    ) -> ShortPackage:
        brief_json = json.dumps(brief.model_dump(exclude={"sources"}), ensure_ascii=False, indent=2)
        prompt = f"""Turn this research brief into a {duration_seconds}-second vertical YouTube Short.

STYLE: {style}
AUDIENCE: {audience}
FORMAT: 9:16

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
        result = self.llm.complete_json(system=SCRIPT_SYSTEM, user=prompt, schema=ShortPackage)
        package = ShortPackage.model_validate(result.model_dump())
        package.topic = brief.topic
        package.duration_seconds = duration_seconds
        package.style = style
        package.audience = audience
        package.research = brief
        return package


def export_package(package: ShortPackage, output_root: Path) -> tuple[Path, Path]:
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
