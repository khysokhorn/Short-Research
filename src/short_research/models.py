from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchSource(BaseModel):
    title: str
    url: str
    snippet: str = ""
    extracted_text: str = ""


class ResearchBrief(BaseModel):
    topic: str
    core_angle: str
    key_facts: list[str] = Field(default_factory=list)
    surprising_facts: list[str] = Field(default_factory=list)
    stakes_or_tension: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    sources: list[ResearchSource] = Field(default_factory=list)


class CharacterSpec(BaseModel):
    name: str
    role: str
    visual_description: str
    consistency_notes: str = ""


class SceneSpec(BaseModel):
    index: int
    start_second: float
    end_second: float
    purpose: str
    narration: str
    visual_direction: str
    camera: str
    on_screen_text: str = ""
    sound_design: str = ""
    transition: str = ""
    retention_device: str = ""


class ShortPackage(BaseModel):
    topic: str
    working_title: str
    youtube_title: str
    hook: str
    payoff: str
    core_angle: str
    style: str
    audience: str
    duration_seconds: int
    narration: str
    characters: list[CharacterSpec] = Field(default_factory=list)
    scenes: list[SceneSpec]
    youtube_description: str
    hashtags: list[str] = Field(default_factory=list)
    research: ResearchBrief
