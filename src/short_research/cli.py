from __future__ import annotations

from pathlib import Path

import typer
from dotenv import load_dotenv

from .arcreel import ArcReelClient
from .llm import OpenAICompatibleLLM
from .pipeline import ShortResearchPipeline, export_package

app = typer.Typer(no_args_is_help=True, help="Research and build ArcReel-ready YouTube Shorts.")


@app.command()
def generate(
    topic: str = typer.Argument(..., help="Topic or story idea to research."),
    duration: int = typer.Option(45, "--duration", "-d", min=15, max=180),
    style: str = typer.Option("cinematic fun fact", "--style"),
    audience: str = typer.Option("general YouTube Shorts audience", "--audience"),
    max_sources: int = typer.Option(6, "--max-sources", min=2, max=12),
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    push_arcreel: bool = typer.Option(False, "--push-arcreel", help="Create/upload directly to ArcReel."),
) -> None:
    """Research a topic, write a high-retention short, and export an ArcReel screenplay."""
    load_dotenv()
    llm = OpenAICompatibleLLM()
    pipeline = ShortResearchPipeline(llm=llm)

    package = pipeline.generate(
        topic,
        duration_seconds=duration,
        style=style,
        audience=audience,
        max_sources=max_sources,
    )
    json_path, screenplay_path = export_package(package, output)

    typer.echo(f"Package: {json_path}")
    typer.echo(f"ArcReel screenplay: {screenplay_path}")

    if push_arcreel:
        result = ArcReelClient().push_screenplay(package, screenplay_path)
        typer.echo(f"ArcReel project: {result['project_url']}")


if __name__ == "__main__":
    app()
