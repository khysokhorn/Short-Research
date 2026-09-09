from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx

from .llm import OpenAICompatibleLLM
from .models import PostRenderCritique, ReferenceVideoAnalysis, ShortPackage

REFERENCE_SYSTEM = """You are a short-form video analyst. Reverse-engineer structure, pacing, hook mechanics,
visual pattern changes, and retention devices without copying protected creative expression. Extract reusable
abstract patterns only. Be concrete about timing and editing behavior when evidence supports it."""

POST_RENDER_SYSTEM = """You are a ruthless short-form video QA editor. Compare the rendered frames and metadata
against the planned short. Score first-frame strength, visual continuity, readability, pacing, and story match.
Identify which planned scenes need editing or regeneration. Do not praise weak work just to be polite."""


class VideoToolError(RuntimeError):
    pass


class ReferenceVideoAnalyzer:
    def __init__(self, llm: OpenAICompatibleLLM) -> None:
        self.llm = llm

    def analyze(self, source: str, *, visual: bool = False, frame_count: int = 6) -> ReferenceVideoAnalysis:
        path = Path(source)
        if path.is_file():
            metadata = probe_video(path)
            transcript = ""
            frames = extract_frames(path, frame_count=frame_count) if visual else []
            title = path.stem
            duration = _duration_from_probe(metadata)
        elif source.startswith(("https://", "http://")):
            raw_metadata, transcript, downloaded = self._youtube_context(source, visual=visual)
            metadata = self._compact_youtube_metadata(raw_metadata)
            frames = extract_frames(downloaded, frame_count=frame_count) if downloaded else []
            title = str(metadata.get("title") or source)
            duration = _safe_float(metadata.get("duration"))
        else:
            raise VideoToolError(f"Reference source not found: {source}")

        context = {
            "source": source,
            "title": title,
            "duration_seconds": duration,
            "metadata": metadata,
            "transcript": transcript[:20_000],
            "visual_frame_count": len(frames),
        }
        prompt = (
            "Analyze this reference short for reusable high-level storytelling and editing patterns. "
            "Do not copy wording, characters, exact shot sequences, or other distinctive expression.\n\n"
            + json.dumps(context, ensure_ascii=False, indent=2)
        )
        result = self.llm.complete_json(
            system=REFERENCE_SYSTEM,
            user=prompt,
            schema=ReferenceVideoAnalysis,
            task="reference_analysis",
            images=frames or None,
            temperature=0.3,
        )
        analysis = ReferenceVideoAnalysis.model_validate(result.model_dump())
        analysis.source = source
        analysis.title = title
        analysis.duration_seconds = duration
        analysis.transcript_excerpt = transcript[:3000]
        return analysis

    def _youtube_context(self, url: str, *, visual: bool) -> tuple[dict[str, Any], str, Path | None]:
        try:
            import yt_dlp
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise VideoToolError("yt-dlp is required for URL reference analysis") from exc

        options: dict[str, Any] = {"quiet": True, "skip_download": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        transcript = self._caption_text(info)
        downloaded: Path | None = None
        if visual:
            temp_dir = Path(tempfile.mkdtemp(prefix="short-research-ref-"))
            output_template = str(temp_dir / "reference.%(ext)s")
            download_options = {
                "quiet": True,
                "no_warnings": True,
                "format": "best[height<=480]/worst",
                "outtmpl": output_template,
            }
            with yt_dlp.YoutubeDL(download_options) as ydl:
                downloaded_info = ydl.extract_info(url, download=True)
                downloaded = Path(ydl.prepare_filename(downloaded_info))
        return info, transcript, downloaded

    @staticmethod
    def _compact_youtube_metadata(info: dict[str, Any]) -> dict[str, Any]:
        keys = (
            "id",
            "title",
            "description",
            "duration",
            "channel",
            "uploader",
            "view_count",
            "like_count",
            "comment_count",
            "upload_date",
            "timestamp",
            "categories",
            "tags",
            "webpage_url",
        )
        compact = {key: info.get(key) for key in keys if info.get(key) is not None}
        if isinstance(compact.get("description"), str):
            compact["description"] = compact["description"][:3000]
        if isinstance(compact.get("tags"), list):
            compact["tags"] = compact["tags"][:30]
        return compact

    @staticmethod
    def _caption_text(info: dict[str, Any]) -> str:
        tracks = info.get("subtitles") or info.get("automatic_captions") or {}
        candidates = tracks.get("en") or tracks.get("en-US") or next(iter(tracks.values()), [])
        if not candidates:
            return ""
        preferred = next(
            (item for item in candidates if item.get("ext") in {"vtt", "srv3", "json3"}),
            candidates[0],
        )
        url = preferred.get("url")
        if not url:
            return ""
        try:
            text = httpx.get(url, timeout=15.0, follow_redirects=True).text
        except Exception:
            return ""
        if preferred.get("ext") == "json3":
            try:
                data = json.loads(text)
                pieces = []
                for event in data.get("events", []):
                    pieces.extend(seg.get("utf8", "") for seg in event.get("segs", []))
                return " ".join(pieces)
            except Exception:
                pass
        text = re.sub(r"WEBVTT.*?\n", "", text, flags=re.DOTALL)
        text = re.sub(r"\d{2}:\d{2}[^\n]*-->[^\n]*", "", text)
        text = re.sub(r"<[^>]+>", "", text)
        lines = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().isdigit()]
        return " ".join(dict.fromkeys(lines))


class PostRenderCritic:
    def __init__(self, llm: OpenAICompatibleLLM) -> None:
        self.llm = llm

    def critique(self, video_path: Path, package: ShortPackage, *, frame_count: int = 8) -> PostRenderCritique:
        if not video_path.is_file():
            raise VideoToolError(f"Rendered video not found: {video_path}")
        metadata = probe_video(video_path)
        frames = extract_frames(video_path, frame_count=frame_count)
        plan = {
            "title": package.working_title,
            "hook": package.hook,
            "duration_seconds": package.duration_seconds,
            "scenes": [
                {
                    "index": scene.index,
                    "time": [scene.start_second, scene.end_second],
                    "purpose": scene.purpose,
                    "visual": scene.visual_direction,
                    "on_screen_text": scene.on_screen_text,
                }
                for scene in package.scenes
            ],
        }
        prompt = (
            "Review the sampled frames of the finished vertical short against this production plan. "
            "Use regenerate_scene_indices only for scenes that genuinely need regeneration rather than a simple edit.\n\n"
            f"VIDEO METADATA:\n{json.dumps(metadata, ensure_ascii=False)}\n\n"
            f"PLAN:\n{json.dumps(plan, ensure_ascii=False, indent=2)}"
        )
        result = self.llm.complete_json(
            system=POST_RENDER_SYSTEM,
            user=prompt,
            schema=PostRenderCritique,
            task="post_render_critic",
            images=frames,
            temperature=0.2,
        )
        return PostRenderCritique.model_validate(result.model_dump())


def probe_video(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,size,bit_rate:stream=codec_name,width,height,r_frame_rate",
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise VideoToolError("ffprobe is required for video analysis") from exc
    return json.loads(completed.stdout or "{}")


def extract_frames(path: Path, *, frame_count: int = 8) -> list[Path]:
    metadata = probe_video(path)
    duration = _duration_from_probe(metadata)
    if not duration or duration <= 0:
        raise VideoToolError("Could not determine video duration")
    temp_dir = Path(tempfile.mkdtemp(prefix="short-research-frames-"))
    frames: list[Path] = []
    for index in range(frame_count):
        second = duration * ((index + 0.5) / frame_count)
        target = temp_dir / f"frame-{index + 1:02d}.jpg"
        command = [
            "ffmpeg",
            "-loglevel",
            "error",
            "-ss",
            f"{second:.3f}",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            "scale='min(720,iw)':-2",
            "-y",
            str(target),
        ]
        try:
            subprocess.run(command, capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise VideoToolError("ffmpeg is required for frame extraction") from exc
        if target.is_file():
            frames.append(target)
    return frames


def _duration_from_probe(metadata: dict[str, Any]) -> float | None:
    return _safe_float((metadata.get("format") or {}).get("duration"))


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
