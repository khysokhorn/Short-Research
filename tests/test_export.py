from short_research.models import ResearchBrief, ResearchSource, SceneSpec, ShortPackage
from short_research.pipeline import to_arcreel_screenplay


def test_arcreel_export_contains_core_sections() -> None:
    package = ShortPackage(
        topic="Why airplane windows have a tiny hole",
        working_title="The Tiny Hole That Keeps Your Window Safe",
        youtube_title="Why Airplane Windows Have That Tiny Hole",
        hook="That tiny hole in your airplane window is there on purpose.",
        payoff="It helps manage pressure between window panes.",
        core_angle="A tiny overlooked detail solves a serious engineering problem.",
        style="cinematic fun fact",
        audience="general",
        duration_seconds=30,
        narration="That tiny hole is not damage.",
        scenes=[
            SceneSpec(
                index=1,
                start_second=0,
                end_second=4,
                purpose="hook",
                narration="That tiny hole is not damage.",
                visual_direction="Macro push-in on the aircraft window hole.",
                camera="Fast macro dolly-in",
                retention_device="Immediate visual mystery",
            )
        ],
        youtube_description="A quick engineering fact.",
        hashtags=["#shorts"],
        research=ResearchBrief(
            topic="Why airplane windows have a tiny hole",
            core_angle="Engineering detail",
            key_facts=["The hole helps equalize pressure between panes. [1]"],
            sources=[ResearchSource(title="Example", url="https://example.com")],
        ),
    )

    text = to_arcreel_screenplay(package)
    assert "## Project Overview" in text
    assert "## Scene Breakdown" in text
    assert "## Research Guardrails" in text
    assert "https://example.com" in text
