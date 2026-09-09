from __future__ import annotations

import json
from pathlib import Path

import typer
from dotenv import load_dotenv

from .arcreel import ArcReelClient
from .llm import OpenAICompatibleLLM
from .models import ShortPackage
from .pipeline import ShortResearchPipeline, export_package, export_run
from .presets import BUILTIN_PRESETS, load_preset
from .video_analysis import PostRenderCritic, ReferenceVideoAnalyzer

app = typer.Typer(no_args_is_help=True, help="Research, critique and build ArcReel-ready YouTube Shorts.")


@app.command()
def generate(
    topic: str = typer.Argument(..., help="Topic or story idea to research."),
    duration: int = typer.Option(45, "--duration", "-d", min=15, max=180),
    style: str = typer.Option("cinematic fun fact", "--style"),
    audience: str = typer.Option("general YouTube Shorts audience", "--audience"),
    preset: str | None = typer.Option(None, "--preset", help="Built-in preset name or JSON preset path."),
    max_sources: int = typer.Option(6, "--max-sources", min=2, max=12),
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    reference: str | None = typer.Option(None, "--reference", help="YouTube URL or local reference video."),
    reference_visual: bool = typer.Option(False, "--reference-visual", help="Also sample visual frames."),
    critic_threshold: int = typer.Option(78, "--critic-threshold", min=0, max=100),
    rewrite_passes: int = typer.Option(2, "--rewrite-passes", min=0, max=5),
    basic: bool = typer.Option(False, "--basic", help="Skip angle competition/critic/packaging stages."),
    push_arcreel: bool = typer.Option(False, "--push-arcreel", help="Create/upload directly to ArcReel."),
    trigger_arcreel: bool = typer.Option(False, "--trigger-arcreel", help="Push and start ArcReel /video-workflow."),
) -> None:
    """Run the research-to-production pipeline. ArcReel is never called unless explicitly requested."""
    load_dotenv()
    llm = OpenAICompatibleLLM()
    pipeline = ShortResearchPipeline(llm=llm)
    selected_preset = load_preset(preset)

    if basic:
        package = pipeline.generate(
            topic,
            duration_seconds=duration,
            style=selected_preset.style if selected_preset else style,
            audience=selected_preset.audience if selected_preset else audience,
            max_sources=max_sources,
        )
        json_path, screenplay_path = export_package(package, output)
    else:
        run = pipeline.generate_full(
            topic,
            duration_seconds=duration,
            style=style,
            audience=audience,
            max_sources=max_sources,
            preset=selected_preset,
            reference_source=reference,
            reference_visual=reference_visual,
            critic_threshold=critic_threshold,
            max_rewrite_passes=rewrite_passes,
        )
        package = run.package
        json_path, screenplay_path = export_run(run, output)
        typer.echo(f"Final critic score: {run.critique.overall_score}/100")
        typer.echo(f"Rewrite passes: {run.rewrite_passes}")

    usage_path = json_path.parent / "llm-usage.json"
    usage_path.write_text(json.dumps(llm.usage_log, indent=2), encoding="utf-8")

    typer.echo(f"Package: {json_path}")
    typer.echo(f"ArcReel screenplay: {screenplay_path}")
    typer.echo(f"LLM routing/usage: {usage_path}")

    if trigger_arcreel:
        result = ArcReelClient().push_and_trigger(package, screenplay_path)
        typer.echo(f"ArcReel project: {result['project_url']}")
        typer.echo(f"Workflow next action: {result['workflow'].get('next_action')}")
    elif push_arcreel:
        result = ArcReelClient().push_screenplay(package, screenplay_path)
        typer.echo(f"ArcReel project: {result['project_url']}")


@app.command("analyze-reference")
def analyze_reference(
    source: str = typer.Argument(..., help="YouTube URL or local video path."),
    visual: bool = typer.Option(False, "--visual", help="Download/sample frames for multimodal analysis."),
    output: Path = typer.Option(Path("reference-analysis.json"), "--output", "-o"),
) -> None:
    """Reverse-engineer reusable hook, pacing and editing patterns from a reference video."""
    load_dotenv()
    llm = OpenAICompatibleLLM()
    analysis = ReferenceVideoAnalyzer(llm).analyze(source, visual=visual)
    output.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Reference analysis: {output}")


@app.command("critique-render")
def critique_render(
    package_json: Path = typer.Argument(..., exists=True, readable=True),
    video: Path = typer.Argument(..., exists=True, readable=True),
    output: Path = typer.Option(Path("post-render-critique.json"), "--output", "-o"),
) -> None:
    """Sample the finished video and compare it with the planned short package."""
    load_dotenv()
    llm = OpenAICompatibleLLM()
    package = ShortPackage.model_validate_json(package_json.read_text(encoding="utf-8"))
    critique = PostRenderCritic(llm).critique(video, package)
    output.write_text(critique.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Post-render score: {critique.overall_score}/100")
    typer.echo(f"Critique: {output}")


@app.command("list-presets")
def list_presets() -> None:
    """Show built-in channel styles."""
    for name, preset in BUILTIN_PRESETS.items():
        typer.echo(f"{name}: {preset.description}")


if __name__ == "__main__":
    app()
