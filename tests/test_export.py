from short_research.models import CharacterSpec, ResearchBrief, ResearchSource, SceneSpec, ShortPackage
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


def test_arcreel_export_contains_story_logic_and_continuity_bible() -> None:
    package = ShortPackage(
        topic="Mother bird saves three chicks from a wildfire",
        working_title="Mama's Wings",
        youtube_title="Mama's Wings",
        hook="Fire is already behind them.",
        payoff="All three chicks reach the stone arch safely.",
        core_angle="A parent solves one physical obstacle at a time to keep all three chicks together.",
        style="cinematic stylized animation",
        audience="general",
        duration_seconds=30,
        narration="",
        story_mode="silent_story",
        location_map="One orchard path runs beside one irrigation channel ending at one stone arch.",
        continuity_rules=["Exactly the same three chicks appear throughout."],
        characters=[
            CharacterSpec(
                name="Mother Hen",
                role="protector",
                visual_description="Chestnut-brown hen with cream chest and red comb.",
                immutable_id="mother-hen-v1",
            )
        ],
        scenes=[
            SceneSpec(
                index=1,
                start_second=0,
                end_second=6,
                purpose="danger-first hook",
                start_state="Family runs along the orchard path with fire behind them.",
                obstacle="A burning branch blocks the path.",
                decision="Mother Hen chooses the irrigation channel.",
                action="She stops and turns toward the channel.",
                consequence="The chicks bunch behind her and the channel becomes the only visible route.",
                end_state="All four are stopped at the branch beside the channel.",
                characters_present=["Mother Hen", "Pip", "Pop", "Peep"],
                character_positions="Mother in front; Pip, Pop, Peep directly behind in fixed order.",
                location="Orchard path beside irrigation channel",
                screen_direction="left-to-right",
                visual_direction="Fire advances behind the running family until the branch blocks them.",
                camera="Low tracking shot into a wider geography reveal.",
            )
        ],
        youtube_description="Silent animated rescue short.",
        research=ResearchBrief(topic="fictional rescue", core_angle="visual cause and effect"),
    )

    text = to_arcreel_screenplay(package)
    assert "## Continuity Bible" in text
    assert "**Story mode:** silent_story" in text
    assert "**Start state:**" in text
    assert "**Consequence:**" in text
    assert "**Characters present:** Mother Hen, Pip, Pop, Peep" in text
    assert "**Immutable ID:** mother-hen-v1" in text
