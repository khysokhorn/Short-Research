from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel


class LLMConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelCandidate:
    model: str
    quality: int = 50
    input_per_million: float = 0.0
    output_per_million: float = 0.0

    def estimate(self, input_chars: int, output_tokens: int = 1800) -> float:
        input_tokens = max(1, input_chars // 4)
        return (input_tokens / 1_000_000) * self.input_per_million + (
            output_tokens / 1_000_000
        ) * self.output_per_million


class ModelRouter:
    """Select the best configured model that fits the per-call budget.

    SHORT_RESEARCH_MODEL_ROUTES_JSON example:
    {
      "research": [{"model":"cheap-model","quality":50,"input_per_million":0.2,"output_per_million":0.8}],
      "critic": [{"model":"strong-model","quality":90,"input_per_million":2,"output_per_million":8}]
    }
    """

    def __init__(self, default_model: str, routes: dict[str, list[ModelCandidate]] | None = None) -> None:
        self.default_model = default_model
        self.routes = routes or {}

    @classmethod
    def from_env(cls, default_model: str) -> ModelRouter:
        raw = os.getenv("SHORT_RESEARCH_MODEL_ROUTES_JSON", "").strip()
        if not raw:
            return cls(default_model)
        parsed = json.loads(raw)
        routes: dict[str, list[ModelCandidate]] = {}
        for task, candidates in parsed.items():
            routes[str(task)] = [ModelCandidate(**item) for item in candidates]
        return cls(default_model, routes)

    def choose(self, task: str, input_chars: int, max_cost_usd: float | None = None) -> ModelCandidate:
        candidates = self.routes.get(task) or self.routes.get("default") or [ModelCandidate(self.default_model)]
        if max_cost_usd is None:
            return max(candidates, key=lambda item: item.quality)
        affordable = [item for item in candidates if item.estimate(input_chars) <= max_cost_usd]
        if affordable:
            return max(affordable, key=lambda item: item.quality)
        return min(candidates, key=lambda item: item.estimate(input_chars))


class OpenAICompatibleLLM:
    """Dependency-light OpenAI-compatible client with task-based model routing."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 120.0,
        router: ModelRouter | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("SHORT_RESEARCH_LLM_BASE_URL") or "").rstrip("/")
        self.api_key = api_key or os.getenv("SHORT_RESEARCH_LLM_API_KEY") or ""
        self.model = model or os.getenv("SHORT_RESEARCH_LLM_MODEL") or ""
        self.timeout_seconds = timeout_seconds
        self.max_cost_usd = self._optional_float(os.getenv("SHORT_RESEARCH_MAX_LLM_USD_PER_CALL"))
        self.router = router or ModelRouter.from_env(self.model)
        self.usage_log: list[dict[str, Any]] = []

        missing = [
            name
            for name, value in (
                ("SHORT_RESEARCH_LLM_BASE_URL", self.base_url),
                ("SHORT_RESEARCH_LLM_API_KEY", self.api_key),
                ("SHORT_RESEARCH_LLM_MODEL", self.model),
            )
            if not value
        ]
        if missing:
            raise LLMConfigurationError(f"Missing LLM configuration: {', '.join(missing)}")

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: type[BaseModel],
        task: str = "default",
        images: list[Path] | None = None,
        temperature: float = 0.7,
    ) -> BaseModel:
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        full_user = (
            f"{user}\n\nReturn ONLY one valid JSON object matching this JSON Schema exactly:\n{schema_json}"
        )
        candidate = self.router.choose(task, len(system) + len(full_user), self.max_cost_usd)
        user_content: str | list[dict[str, Any]] = full_user
        if images:
            user_content = [{"type": "text", "text": full_user}]
            user_content.extend(self._image_part(path) for path in images)

        payload = {
            "model": candidate.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        usage = data.get("usage") or {}
        self.usage_log.append(
            {
                "task": task,
                "model": candidate.model,
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "estimated_preflight_cost_usd": round(candidate.estimate(len(system) + len(full_user)), 6),
            }
        )
        text = data["choices"][0]["message"]["content"]
        parsed = self._parse_json(text)
        return schema.model_validate(parsed)

    @staticmethod
    def _image_part(path: Path) -> dict[str, Any]:
        media_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{media_type};base64,{encoded}"},
        }

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            cleaned = fenced.group(1).strip()
        return json.loads(cleaned)

    @staticmethod
    def _optional_float(value: str | None) -> float | None:
        if value is None or not value.strip():
            return None
        return float(value)
