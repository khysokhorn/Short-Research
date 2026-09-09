from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class ChannelPreset(BaseModel):
    name: str
    description: str
    style: str
    audience: str = "general YouTube Shorts audience"
    writer_rules: list[str] = Field(default_factory=list)
    visual_rules: list[str] = Field(default_factory=list)
    banned_patterns: list[str] = Field(default_factory=list)

    def prompt_fragment(self) -> str:
        sections = [
            f"CHANNEL PRESET: {self.name}",
            f"DESCRIPTION: {self.description}",
            "WRITER RULES:\n" + "\n".join(f"- {item}" for item in self.writer_rules),
            "VISUAL RULES:\n" + "\n".join(f"- {item}" for item in self.visual_rules),
        ]
        if self.banned_patterns:
            sections.append("DO NOT USE:\n" + "\n".join(f"- {item}" for item in self.banned_patterns))
        return "\n\n".join(sections)


BUILTIN_PRESETS: dict[str, ChannelPreset] = {
    "micro-disaster": ChannelPreset(
        name="micro-disaster",
        description="Comedic microscopic workers turn a real body process into an escalating physical disaster.",
        style="cinematic microscopic body comedy with exaggerated practical machinery",
        writer_rules=[
            "Ground the narration in real facts while the visuals may use a playful metaphor.",
            "Escalate the internal workers' reaction every 4-6 seconds.",
            "Alternate the microscopic world with the real-world social consequence.",
            "End on a practical or surprising factual payoff.",
        ],
        visual_rules=[
            "Keep recurring micro-workers visually consistent.",
            "Use oversized mechanical controls, gauges, valves, alarms and physical comedy.",
            "Prefer camera movement through anatomy over static explanatory diagrams.",
        ],
        banned_patterns=["generic medical stock footage", "long talking-head introductions"],
    ),
    "cinematic-fact": ChannelPreset(
        name="cinematic-fact",
        description="A surprising true fact told like a miniature documentary trailer.",
        style="cinematic factual documentary with fast visual reveals",
        writer_rules=[
            "Lead with the most counterintuitive verified fact.",
            "Build a clean question -> explanation -> payoff arc.",
            "Avoid sensational claims not supported by sources.",
        ],
        visual_rules=["Use scale changes, macro details, diagrams-in-motion and visual comparisons."],
    ),
    "horribly-wrong": ChannelPreset(
        name="horribly-wrong",
        description="A seemingly normal plan compounds into a funny or shocking failure.",
        style="fast escalating disaster comedy with cinematic cause-and-effect",
        writer_rules=[
            "Establish the normal goal immediately.",
            "Add a new complication every few seconds.",
            "Make each beat causally worse than the previous one.",
            "Deliver the final consequence as the payoff, not as random chaos.",
        ],
        visual_rules=["Use clear before/after states and increasingly aggressive camera movement."],
    ),
    "silent-rescue": ChannelPreset(
        name="silent-rescue",
        description="Dialogue-free emotional rescue story driven by clear physical cause-and-effect.",
        style="cinematic stylized animation, emotional family-friendly peril, clear physical storytelling",
        writer_rules=[
            "The complete story must be understandable without narration, captions, or on-screen text.",
            "Establish danger and the hero's goal in the first 2 seconds.",
            "Every scene must contain obstacle -> decision -> action -> consequence.",
            "Each important action must visibly change what happens in the next scene.",
            "Include at least one near-failure before the final rescue.",
            "The emotional payoff must resolve a danger established earlier.",
            "Do not solve problems with unexplained coincidences or miracle objects.",
        ],
        visual_rules=[
            "Lock character count, identity, markings, proportions, clothing and color palette.",
            "Maintain one connected geography unless a location change is explicitly shown.",
            "Preserve screen direction across consecutive movement scenes.",
            "Begin every scene from the physical state where the previous scene ended.",
            "Objects used for a solution must be introduced before they are used.",
            "Show the visible consequence of every major action on screen.",
        ],
        banned_patterns=[
            "teleporting between locations",
            "changing character count",
            "unmotivated objects appearing",
            "random scenic shots with no story consequence",
            "miracle solutions",
        ],
    ),
    "luxury-experiment": ChannelPreset(
        name="luxury-experiment",
        description="Ordinary objects become absurdly expensive through scientific or luxury constraints.",
        style="luxury product cinematography mixed with laboratory spectacle",
        writer_rules=[
            "Reveal cost escalation in stages.",
            "Attach each price jump to a concrete material, process or constraint.",
            "Save the total cost for the final third unless it is the hook.",
        ],
        visual_rules=["Macro material shots, clean price counters, laboratory closeups, premium product lighting."],
    ),
    "dark-mystery": ChannelPreset(
        name="dark-mystery",
        description="A factual mystery with controlled reveals and an evidence-first ending.",
        style="dark atmospheric mystery documentary",
        writer_rules=[
            "Open with an unresolved contradiction.",
            "Separate evidence from speculation explicitly.",
            "Reveal one clue at a time and avoid fake certainty.",
        ],
        visual_rules=["Use maps, evidence details, silhouettes and restrained cinematic motion."],
    ),
}


def load_preset(name_or_path: str | None) -> ChannelPreset | None:
    if not name_or_path:
        return None
    if name_or_path in BUILTIN_PRESETS:
        return BUILTIN_PRESETS[name_or_path]
    path = Path(name_or_path)
    if not path.is_file():
        available = ", ".join(sorted(BUILTIN_PRESETS))
        raise ValueError(f"Unknown preset '{name_or_path}'. Built-ins: {available}")
    return ChannelPreset.model_validate(json.loads(path.read_text(encoding="utf-8")))
