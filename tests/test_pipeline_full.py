from short_research.models import (
    AngleCandidate,
    AngleCompetition,
    HookCandidate,
    PackagingVariants,
    ResearchBrief,
    ResearchSource,
    SceneSpec,
    ShortCritique,
    ShortPackage,
    ThumbnailVariant,
    TitleVariant,
)
from short_research.pipeline import ShortResearchPipeline


class FakeResearcher:
    def search(self, topic: str, max_sources: int = 6) -> list[ResearchSource]:
        return [ResearchSource(title="Source", url="https://example.com", extracted_text="Verified fact.")]


class FakeLLM:
    def __init__(self) -> None:
        self.critic_calls = 0
        self.usage_log = []

    def complete_json(self, *, schema, **kwargs):
        if schema is ResearchBrief:
            return ResearchBrief(topic="x", core_angle="fact", key_facts=["Verified fact. [1]"])
        if schema is AngleCompetition:
            hook = HookCandidate(
                text="The thing you believe is backwards.",
                curiosity_score=90,
                clarity_score=90,
                visual_score=90,
                truthfulness_score=100,
                overall_score=92,
            )
            return AngleCompetition(
                candidates=[
                    AngleCandidate(
                        name=f"Angle {index}",
                        premise=f"Premise {index}",
                        payoff=f"Payoff {index}",
                        visual_engine="escalation",
                        hooks=[hook],
                        overall_score=80 + index,
                    )
                    for index in range(5)
                ],
                selected_angle_index=4,
                selected_hook_index=0,
            )
        if schema is ShortPackage:
            return ShortPackage(
                topic="x",
                working_title="Test Short",
                youtube_title="Test",
                hook="placeholder",
                payoff="placeholder",
                core_angle="placeholder",
                style="style",
                audience="audience",
                duration_seconds=30,
                narration="Narration.",
                scenes=[
                    SceneSpec(
                        index=1,
                        start_second=0,
                        end_second=30,
                        purpose="story",
                        narration="Narration.",
                        visual_direction="Specific visual.",
                        camera="push in",
                        retention_device="reveal",
                    )
                ],
                youtube_description="Description",
                research=ResearchBrief(topic="x", core_angle="fact"),
            )
        if schema is ShortCritique:
            self.critic_calls += 1
            score = 60 if self.critic_calls == 1 else 90
            return ShortCritique(
                hook_score=score,
                pacing_score=score,
                visual_novelty_score=score,
                escalation_score=score,
                payoff_score=score,
                factual_discipline_score=100,
                overall_score=score,
                rewrite_priorities=["Fix pacing"] if score < 78 else [],
            )
        if schema is PackagingVariants:
            return PackagingVariants(
                titles=[TitleVariant(title="Title A", score=90)],
                thumbnails=[ThumbnailVariant(concept="Concept", image_prompt="Prompt", score=90)],
            )
        raise AssertionError(f"Unexpected schema: {schema}")


def test_full_pipeline_rewrites_until_threshold() -> None:
    pipeline = ShortResearchPipeline(llm=FakeLLM(), researcher=FakeResearcher())
    run = pipeline.generate_full(
        "topic",
        duration_seconds=30,
        critic_threshold=78,
        max_rewrite_passes=2,
    )

    assert run.rewrite_passes == 1
    assert run.critique.overall_score == 90
    assert run.package.hook == "The thing you believe is backwards."
    assert run.package.core_angle == "Premise 4"
    assert run.package.payoff == "Payoff 4"
    assert run.package.research.sources[0].url == "https://example.com"
