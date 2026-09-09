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

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def push_screenplay(self, package: ShortPackage, screenplay_path: Path) -> dict[str, Any]:
        project_name = self._project_name(package.working_title or package.topic)
        create_payload = {
            "name": project_name,
            "title": package.working_title,
            "content_mode": "drama",
            "source_kind": "screenplay",
            "aspect_ratio": "9:16",
            "episode_target_duration": package.duration_seconds,
            "generation_mode": "storyboard",
        }

        with httpx.Client(timeout=60.0, headers=self.headers) as client:
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

    def workflow_plan(self, project_name: str, *, episode: int | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if episode is not None:
            payload["episode"] = episode
        with httpx.Client(timeout=30.0, headers=self.headers) as client:
            response = client.post(
                f"{self.base_url}/api/v1/projects/{project_name}/workflow-plan",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def trigger_workflow(
        self,
        project_name: str,
        *,
        episode: int | None = None,
        instruction: str | None = None,
    ) -> dict[str, Any]:
        """Start ArcReel's own /video-workflow agent against the authoritative server plan.

        ArcReel may still pause when its workflow requires a user decision/confirmation; this method deliberately
        does not bypass ArcReel's gates. It starts the real project assistant rather than emulating generation calls.
        """
        plan = self.workflow_plan(project_name, episode=episode)
        next_action = plan.get("next_action")
        content = instruction or (
            "/video-workflow\n"
            "Continue this project using the authoritative workflow plan. Execute the next admissible action. "
            "Respect blockers and stop if the workflow requires a user choice or confirmation."
        )
        with httpx.Client(timeout=120.0, headers=self.headers) as client:
            response = client.post(
                f"{self.base_url}/api/v1/projects/{project_name}/assistant/sessions/send",
                json={
                    "content": content,
                    "client_key": f"short-research-workflow-{project_name}-{episode or 'project'}",
                },
            )
            response.raise_for_status()
            assistant = response.json()
        return {"project_name": project_name, "plan": plan, "next_action": next_action, "assistant": assistant}

    def push_and_trigger(self, package: ShortPackage, screenplay_path: Path) -> dict[str, Any]:
        pushed = self.push_screenplay(package, screenplay_path)
        workflow = self.trigger_workflow(pushed["project_name"])
        return {**pushed, "workflow": workflow}

    @staticmethod
    def _project_name(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.lower()).strip("-")
        return slug[:60] or "youtube-short"
