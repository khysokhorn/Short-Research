from short_research.arcreel import ArcReelClient
from short_research.llm import ModelCandidate, ModelRouter
from short_research.models import AngleCandidate, AngleCompetition, HookCandidate
from short_research.presets import BUILTIN_PRESETS, load_preset


def _hook(text: str, score: int) -> HookCandidate:
    return HookCandidate(
        text=text,
        curiosity_score=score,
        clarity_score=score,
        visual_score=score,
        truthfulness_score=score,
        overall_score=score,
    )


def test_model_router_uses_best_affordable_candidate() -> None:
    router = ModelRouter(
        "fallback",
        {
            "critic": [
                ModelCandidate(
                    model="premium",
                    quality=95,
                    input_per_million=100.0,
                    output_per_million=100.0,
                ),
                ModelCandidate(
                    model="cheap",
                    quality=70,
                    input_per_million=0.1,
                    output_per_million=0.2,
                ),
            ]
        },
    )
    selected = router.choose("critic", input_chars=4000, max_cost_usd=0.01)
    assert selected.model == "cheap"


def test_model_router_prefers_quality_without_budget() -> None:
    router = ModelRouter(
        "fallback",
        {
            "script": [
                ModelCandidate(model="fast", quality=60),
                ModelCandidate(model="strong", quality=90),
            ]
        },
    )
    assert router.choose("script", input_chars=1000).model == "strong"


def test_builtin_preset_loads() -> None:
    preset = load_preset("micro-disaster")
    assert preset is BUILTIN_PRESETS["micro-disaster"]
    assert "microscopic" in preset.style


def test_angle_competition_selected_indices() -> None:
    competition = AngleCompetition(
        candidates=[
            AngleCandidate(
                name="A",
                premise="First",
                payoff="One",
                visual_engine="macro",
                hooks=[_hook("hook a", 70)],
                overall_score=70,
            ),
            AngleCandidate(
                name="B",
                premise="Second",
                payoff="Two",
                visual_engine="escalation",
                hooks=[_hook("hook b1", 80), _hook("hook b2", 95)],
                overall_score=95,
            ),
        ],
        selected_angle_index=1,
        selected_hook_index=1,
    )
    angle, hook = competition.selected()
    assert angle.name == "B"
    assert hook.text == "hook b2"


def test_arcreel_project_slug_is_stable() -> None:
    assert ArcReelClient._project_name("Brain Freeze Emergency!!!") == "brain-freeze-emergency"
