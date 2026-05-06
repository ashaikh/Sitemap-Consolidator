"""Pluggable fetcher backends for sitemap downloads.

RequestsFetcher — fast default using `requests` (90%+ of sites).
AutoFallbackFetcher — wraps a primary; on BlockedError builds + switches to
                      a fallback (typically PlaywrightFetcher) for rest of run.

Playwright backend lives in `playwright_fetcher.py` (lazy import — keeps base
install free of browser deps).
"""

from __future__ import annotations

from typing import Callable, Protocol

from sitemap_downloader.downloader import BlockedError, fetch_url


class Fetcher(Protocol):
    def fetch(self, url: str) -> bytes: ...
    def close(self) -> None: ...


class RequestsFetcher:
    """Default fetcher using requests + Chrome UA."""

    def fetch(self, url: str) -> bytes:
        return fetch_url(url)

    def close(self) -> None:
        return None


class AutoFallbackFetcher:
    """Try primary; on BlockedError, build fallback via factory and use it
    for this and all subsequent fetches in the run.
    """

    def __init__(
        self,
        primary: Fetcher,
        fallback_factory: Callable[[], Fetcher],
    ) -> None:
        self._primary = primary
        self._fallback_factory = fallback_factory
        self._fallback: Fetcher | None = None

    def fetch(self, url: str) -> bytes:
        if self._fallback is not None:
            return self._fallback.fetch(url)
        try:
            return self._primary.fetch(url)
        except BlockedError as e:
            print(f"  [stealth] primary blocked ({e}); switching to fallback")
            self._fallback = self._fallback_factory()
            return self._fallback.fetch(url)

    def close(self) -> None:
        self._primary.close()
        if self._fallback is not None:
            self._fallback.close()


def build_default_fetcher(stealth: bool = False, headless: bool = True) -> Fetcher:
    """Construct the default auto-fallback fetcher.

    stealth=True forces Playwright from the start (skip requests entirely).
    """
    if stealth:
        from sitemap_downloader.playwright_fetcher import PlaywrightFetcher
        return PlaywrightFetcher(headless=headless)

    def _factory() -> Fetcher:
        from sitemap_downloader.playwright_fetcher import PlaywrightFetcher
        return PlaywrightFetcher(headless=headless)

    return AutoFallbackFetcher(primary=RequestsFetcher(), fallback_factory=_factory)
