"""Stealth Playwright fetcher for bot-walled sites.

Lazy-imports playwright so base install (`pip install -r requirements.txt`)
stays browser-free. Install via:

    pip install -e .[stealth]
    playwright install chromium

Approach:
- Persistent BrowserContext (cookies persist across all sub-sitemaps in run)
- Realistic Chrome UA, viewport, locale, timezone
- Homepage warmup: visit https://<host>/ once to solve PerimeterX/Cloudflare
  JS challenge, store cookies, then fetch sitemaps with same context
- Throttle: configurable jitter between requests
"""

from __future__ import annotations

import random
import time
from typing import Optional
from urllib.parse import urlparse

from sitemap_downloader.downloader import (
    USER_AGENT,
    ACCEPT_HEADER,
    ACCEPT_LANGUAGE,
    BlockedError,
    BLOCK_PATH_MARKERS,
    BLOCK_BODY_MARKERS,
)


class PlaywrightFetcher:
    """Stealth Playwright fetcher with persistent context + per-host warmup."""

    def __init__(
        self,
        headless: bool = True,
        throttle_seconds: float = 1.5,
        jitter_seconds: float = 0.8,
        warmup_timeout_ms: int = 30_000,
        fetch_timeout_ms: int = 30_000,
        manual_solve_timeout_ms: int = 600_000,
    ) -> None:
        self.headless = headless
        self.throttle_seconds = throttle_seconds
        self.jitter_seconds = jitter_seconds
        self.warmup_timeout_ms = warmup_timeout_ms
        self.fetch_timeout_ms = fetch_timeout_ms
        self.manual_solve_timeout_ms = manual_solve_timeout_ms

        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._warmed_hosts: set[str] = set()
        self._last_fetch_at: float = 0.0
        self._started = False

    # ----- lifecycle -----

    def _start(self) -> None:
        if self._started:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise ImportError(
                "Playwright not installed. Run: pip install -e .[stealth] "
                "&& playwright install chromium"
            ) from e

        try:
            from playwright_stealth import Stealth
            stealth = Stealth()
            self._pw = stealth.use_sync(sync_playwright()).start()
            self._stealth_applied = True
        except ImportError:
            self._pw = sync_playwright().start()
            self._stealth_applied = False

        self._browser = self._pw.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        self._context = self._browser.new_context(
            locale="en-US",
            timezone_id="America/New_York",
            viewport={"width": 1440, "height": 900},
            extra_http_headers={
                "Accept-Language": ACCEPT_LANGUAGE,
                "Accept": ACCEPT_HEADER,
            },
        )
        if not self._stealth_applied:
            self._context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
        self._started = True

    def close(self) -> None:
        if not self._started:
            return
        try:
            if self._page:
                try:
                    self._page.close()
                except Exception:
                    pass
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        finally:
            self._started = False
            self._page = None
            self._context = None
            self._browser = None
            self._pw = None

    def _get_page(self):
        """Reuse a single page across all fetches — avoids focus storms in
        headful mode where each new_page() call steals the keyboard on macOS.
        """
        if self._page is None or self._page.is_closed():
            self._page = self._context.new_page()
        return self._page

    # ----- core -----

    def _warmup(self, host: str) -> None:
        if host in self._warmed_hosts:
            return
        page = self._get_page()
        try:
            print(f"  [stealth] warmup: https://{host}/")
            page.goto(
                f"https://{host}/",
                wait_until="domcontentloaded",
                timeout=self.warmup_timeout_ms,
            )
            try:
                page.wait_for_load_state("networkidle", timeout=15_000)
            except Exception:
                pass
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  [stealth] warmup failed ({e}); proceeding anyway")
        self._warmed_hosts.add(host)

    def _fetch_via_request(self, url: str) -> bytes:
        """Use the browser's APIRequestContext for non-renderable URLs (.gz)."""
        resp = self._context.request.get(url, timeout=self.fetch_timeout_ms)
        body = resp.body()

        if resp.status in (403, 429):
            raise BlockedError(f"HTTP {resp.status} from {url} (stealth/api)")

        final_url = resp.url
        final_path = urlparse(final_url).path
        if any(m in final_path for m in BLOCK_PATH_MARKERS):
            raise BlockedError(f"final URL on block path (api): {final_url}")

        for marker in BLOCK_BODY_MARKERS:
            if marker in body[:4096]:
                raise BlockedError(
                    f"block marker '{marker.decode(errors='replace')}' in body (api): {final_url}"
                )

        if not resp.ok:
            raise RuntimeError(f"HTTP {resp.status} from {final_url} (api)")

        return body

    def _wait_for_human_solve(self, page) -> None:
        """Poll page URL until it leaves a known block path. Used in headful mode
        when a 'press and hold' / image CAPTCHA appears."""
        deadline = time.time() + (self.manual_solve_timeout_ms / 1000.0)
        last_print = 0.0
        while time.time() < deadline:
            try:
                current = urlparse(page.url).path
            except Exception:
                current = ""
            if not any(m in current for m in BLOCK_PATH_MARKERS):
                print(f"  [stealth] CAPTCHA solved (url now {page.url})")
                return
            now = time.time()
            if now - last_print > 10:
                remaining = int(deadline - now)
                print(f"  [stealth] still on block page — {remaining}s left to solve")
                last_print = now
            page.wait_for_timeout(1500)

    def _throttle(self) -> None:
        if self._last_fetch_at == 0.0:
            self._last_fetch_at = time.time()
            return
        elapsed = time.time() - self._last_fetch_at
        wait = self.throttle_seconds + random.uniform(0, self.jitter_seconds) - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_fetch_at = time.time()

    def fetch(self, url: str) -> bytes:
        self._start()
        host = urlparse(url).netloc
        self._warmup(host)
        self._throttle()

        # .gz URLs trigger browser download instead of navigation. Use the
        # browser's APIRequestContext (shares cookies with browser context)
        # for these — keeps the PX cookie attached but avoids the download
        # error. If this returns blocked content, callers can still retry.
        if url.lower().endswith(".gz"):
            return self._fetch_via_request(url)

        page = self._get_page()
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=self.fetch_timeout_ms)
            # Allow JS bot-challenge to settle, then re-check final URL
            try:
                page.wait_for_load_state("networkidle", timeout=10_000)
            except Exception:
                pass

            if response is None:
                raise RuntimeError(f"no response from {url}")

            status = response.status
            final_url = page.url
            final_path = urlparse(final_url).path

            # If challenge redirected us to /blocked:
            #   - headful: wait for human to solve "press and hold" CAPTCHA, then retry
            #   - headless: short pause + retry (often fails — bot wall stays up)
            if any(m in final_path for m in BLOCK_PATH_MARKERS):
                if not self.headless:
                    print(f"  [stealth] CAPTCHA at {final_url} — solve in browser (waiting up to {self.manual_solve_timeout_ms//1000}s)")
                    self._wait_for_human_solve(page)
                else:
                    page.wait_for_timeout(4000)
                response = page.goto(url, wait_until="domcontentloaded", timeout=self.fetch_timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=10_000)
                except Exception:
                    pass
                final_url = page.url
                final_path = urlparse(final_url).path

            if status in (403, 429):
                raise BlockedError(f"HTTP {status} from {url} (stealth)")

            if any(m in final_path for m in BLOCK_PATH_MARKERS):
                raise BlockedError(f"final URL on block path: {final_url}")

            # Pull raw bytes from the response (pre-render — Chrome's XML viewer
            # wraps the body in HTML which we don't want).
            body = response.body() if response else b""

            ctype = (response.headers or {}).get("content-type", "").lower() if response else ""
            expecting_xml = ".xml" in urlparse(url).path.lower()
            looks_html = (
                ("html" in ctype and "xml" not in ctype)
                or body.lstrip()[:6].lower() == b"<html>"
                or body.lstrip()[:5].lower() == b"<!doc"
            )
            if expecting_xml and looks_html:
                raise BlockedError(f"got HTML when expecting XML at {final_url} (stealth)")

            for marker in BLOCK_BODY_MARKERS:
                if marker in body[:4096]:
                    raise BlockedError(
                        f"block marker '{marker.decode(errors='replace')}' in body of {final_url} (stealth)"
                    )

            if status >= 400:
                raise RuntimeError(f"HTTP {status} from {final_url}")

            return body
        finally:
            # Page kept alive — closed in fetcher.close(). Avoids macOS focus storms
            # when fetching hundreds of sitemaps in headful mode.
            pass
