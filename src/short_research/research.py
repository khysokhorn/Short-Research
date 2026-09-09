from __future__ import annotations

import logging

import httpx

from .models import ResearchSource

logger = logging.getLogger(__name__)


class WebResearcher:
    def __init__(self, timeout_seconds: float = 12.0) -> None:
        self.timeout_seconds = timeout_seconds

    def search(self, topic: str, max_sources: int = 6) -> list[ResearchSource]:
        import trafilatura
        from ddgs import DDGS

        results = list(DDGS().text(topic, max_results=max_sources))
        sources: list[ResearchSource] = []
        seen: set[str] = set()

        with httpx.Client(
            timeout=self.timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "ShortResearch/0.1 (+research for video scripting)"},
        ) as client:
            for result in results:
                url = str(result.get("href") or result.get("url") or "").strip()
                if not url or url in seen:
                    continue
                seen.add(url)

                extracted = ""
                try:
                    response = client.get(url)
                    response.raise_for_status()
                    extracted = trafilatura.extract(
                        response.text,
                        include_comments=False,
                        include_tables=False,
                    ) or ""
                except Exception as exc:  # noqa: BLE001 - third-party extractors raise heterogeneous errors
                    logger.debug("Could not extract %s: %s", url, exc)

                sources.append(
                    ResearchSource(
                        title=str(result.get("title") or url),
                        url=url,
                        snippet=str(result.get("body") or result.get("snippet") or ""),
                        extracted_text=extracted[:12_000],
                    )
                )

        return sources
