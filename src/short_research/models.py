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


class HookCandidate(BaseModel):
    text: str
    curiosity_score: int = Field(ge=0, le=100)
    clarity_score: int = Field(ge=0, le=100)
    visual_score: int = Field(ge=0, le=100)
    truthfulness_score: int = Field(ge=0, le=100)
    overall_score: int = Field(ge=0, le=100)
    reason: str = ""


class AngleCandidate(BaseModel):
    name: str
    premise: str
    payoff: str
    visual_engine: str
    hooks: list[HookCandidate] = Field(default_factory=list)
    overall_score: int = Field(ge=0, le=100)
    reason: str = ""


class AngleCompetition(BaseModel):
    candidates: list[AngleCandidate] = Field(default_factory=list)
    selected_angle_index: int = 0
    selected_hook_index: int = 0
    selection_reason: str = ""

    def selected(self) -> tuple[AngleCandidate, HookCandidate]:
        if not self.candidates:
            raise ValueError("Angle competition returned no candidates")
        angle_index = min(max(self.selected_angle_index, 0), len(self.candidates) - 1)
        angle = self.candidates[angle_index]
        if not angle.hooks:
            raise ValueError("Selected angle returned no hooks")
        hook_index = min(max(self.selected_hook_index, 0), len(angle.hooks) - 1)
        return angle, angle.hooks[hook_index]


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


class SceneCritique(BaseModel):
    scene_index: int
    retention_score: int = Field(ge=0, le=100)
    visual_novelty_score: int = Field(ge=0, le=100)
    clarity_score: int = Field(ge=0, le=100)
    issue: str = ""
    fix: str = ""


class ShortCritique(BaseModel):
    hook_score: int = Field(ge=0, le=100)
    pacing_score: int = Field(ge=0, le=100)
    visual_novelty_score: int = Field(ge=0, le=100)
    escalation_score: int = Field(ge=0, le=100)
    payoff_score: int = Field(ge=0, le=100)
    factual_discipline_score: int = Field(ge=0, le=100)
    overall_score: int = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    scene_critiques: list[SceneCritique] = Field(default_factory=list)
    rewrite_priorities: list[str] = Field(default_factory=list)


class TitleVariant(BaseModel):
    title: str
    score: int = Field(ge=0, le=100)
    reason: str = ""


class ThumbnailVariant(BaseModel):
    concept: str
    image_prompt: str
    overlay_text: str = ""
    score: int = Field(ge=0, le=100)
    reason: str = ""


class PackagingVariants(BaseModel):
    titles: list[TitleVariant] = Field(default_factory=list)
    thumbnails: list[ThumbnailVariant] = Field(default_factory=list)
    recommended_title_index: int = 0
    recommended_thumbnail_index: int = 0


class ReferenceVideoAnalysis(BaseModel):
    source: str
    title: str = ""
    duration_seconds: float | None = None
    hook_summary: str
    structure: list[str] = Field(default_factory=list)
    pacing_notes: list[str] = Field(default_factory=list)
    visual_patterns: list[str] = Field(default_factory=list)
    retention_devices: list[str] = Field(default_factory=list)
    reusable_patterns: list[str] = Field(default_factory=list)
    avoid_copying: list[str] = Field(default_factory=list)
    transcript_excerpt: str = ""


class PostRenderCritique(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    first_frame_score: int = Field(ge=0, le=100)
    visual_continuity_score: int = Field(ge=0, le=100)
    readability_score: int = Field(ge=0, le=100)
    pacing_score: int = Field(ge=0, le=100)
    story_match_score: int = Field(ge=0, le=100)
    issues: list[str] = Field(default_factory=list)
    recommended_edits: list[str] = Field(default_factory=list)
    regenerate_scene_indices: list[int] = Field(default_factory=list)


class PipelineRun(BaseModel):
    package: ShortPackage
    angle_competition: AngleCompetition
    critique: ShortCritique
    packaging: PackagingVariants
    reference_analysis: ReferenceVideoAnalysis | None = None
    rewrite_passes: int = 0
