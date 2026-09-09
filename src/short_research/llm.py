from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx
from pydantic import BaseModel


class LLMConfigurationError(RuntimeError):
    pass


class OpenAICompatibleLLM:
    """Tiny dependency-light client for OpenAI-compatible chat-completions APIs."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("SHORT_RESEARCH_LLM_BASE_URL") or "").rstrip("/")
        self.api_key = api_key or os.getenv("SHORT_RESEARCH_LLM_API_KEY") or ""
        self.model = model or os.getenv("SHORT_RESEARCH_LLM_MODEL") or ""
        self.timeout_seconds = timeout_seconds

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

    def complete_json(self, *, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"{user}\n\nReturn ONLY one valid JSON object matching this JSON Schema exactly:\n"
                        f"{schema_json}"
                    ),
                },
            ],
            "temperature": 0.7,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        text = data["choices"][0]["message"]["content"]
        parsed = self._parse_json(text)
        return schema.model_validate(parsed)

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            cleaned = fenced.group(1).strip()
        return json.loads(cleaned)
