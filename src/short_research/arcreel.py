from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import httpx

from .models import ShortPackage


class ArcReelClient:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("ARCREEL_BASE_URL") or "http://localhost:8000").rstrip("/")
        self.token = token if token is not None else os.getenv("ARCREEL_TOKEN", "")

    def push_screenplay(self, package: ShortPackage, screenplay_path: Path) -> dict[str, Any]:
        project_name = self._project_name(package.working_title or package.topic)
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

        create_payload = {
            "name": project_name,
            "title": package.working_title,
            "content_mode": "drama",
            "source_kind": "screenplay",
            "aspect_ratio": "9:16",
            "episode_target_duration": package.duration_seconds,
            "generation_mode": "storyboard",
        }

        with httpx.Client(timeout=60.0, headers=headers) as client:
            create_response = client.post(f"{self.base_url}/api/v1/projects", json=create_payload)
            if create_response.status_code not in (200, 201, 409):
                create_response.raise_for_status()

            with screenplay_path.open("rb") as source_file:
                upload_response = client.post(
                    f"{self.base_url}/api/v1/projects/{project_name}/upload/source",
                    params={"on_conflict": "replace"},
                    files={"file": (screenplay_path.name, source_file, "text/markdown")},
                )
            upload_response.raise_for_status()

        return {
            "project_name": project_name,
            "project_url": f"{self.base_url}/projects/{project_name}",
            "upload": upload_response.json(),
        }

    @staticmethod
    def _project_name(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.lower()).strip("-")
        return slug[:60] or "youtube-short"
