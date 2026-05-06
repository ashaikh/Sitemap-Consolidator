"""Tests for fetcher abstraction and auto-fallback."""
from unittest.mock import MagicMock, patch

import pytest

from sitemap_downloader.downloader import BlockedError
from sitemap_downloader.fetchers import (
    Fetcher,
    RequestsFetcher,
    AutoFallbackFetcher,
)


def test_requests_fetcher_returns_bytes():
    f = RequestsFetcher()
    with patch("sitemap_downloader.fetchers.fetch_url", return_value=b"<urlset/>") as m:
        out = f.fetch("https://x.com/sitemap.xml")
    assert out == b"<urlset/>"
    m.assert_called_once_with("https://x.com/sitemap.xml")


def test_requests_fetcher_propagates_blocked():
    f = RequestsFetcher()
    with patch("sitemap_downloader.fetchers.fetch_url", side_effect=BlockedError("blocked")):
        with pytest.raises(BlockedError):
            f.fetch("https://walmart.com/sitemap.xml")


def test_autofallback_uses_primary_when_ok():
    primary = MagicMock(spec=Fetcher)
    primary.fetch.return_value = b"<urlset/>"
    fallback_factory = MagicMock()

    f = AutoFallbackFetcher(primary=primary, fallback_factory=fallback_factory)
    out = f.fetch("https://x.com/sitemap.xml")

    assert out == b"<urlset/>"
    fallback_factory.assert_not_called()


def test_autofallback_switches_on_blocked():
    primary = MagicMock(spec=Fetcher)
    primary.fetch.side_effect = BlockedError("px wall")

    fallback = MagicMock(spec=Fetcher)
    fallback.fetch.return_value = b"<urlset/>"
    factory = MagicMock(return_value=fallback)

    f = AutoFallbackFetcher(primary=primary, fallback_factory=factory)
    out = f.fetch("https://walmart.com/sitemap.xml")

    assert out == b"<urlset/>"
    factory.assert_called_once()
    fallback.fetch.assert_called_once_with("https://walmart.com/sitemap.xml")


def test_autofallback_reuses_fallback_after_first_block():
    primary = MagicMock(spec=Fetcher)
    primary.fetch.side_effect = BlockedError("px wall")

    fallback = MagicMock(spec=Fetcher)
    fallback.fetch.return_value = b"<urlset/>"
    factory = MagicMock(return_value=fallback)

    f = AutoFallbackFetcher(primary=primary, fallback_factory=factory)
    f.fetch("https://walmart.com/a.xml")
    f.fetch("https://walmart.com/b.xml")

    assert factory.call_count == 1
    assert fallback.fetch.call_count == 2
    # primary only called once (first attempt), then bypassed
    assert primary.fetch.call_count == 1


def test_autofallback_close_propagates():
    primary = MagicMock(spec=Fetcher)
    fallback = MagicMock(spec=Fetcher)
    factory = MagicMock(return_value=fallback)
    f = AutoFallbackFetcher(primary=primary, fallback_factory=factory)
    # trigger fallback
    primary.fetch.side_effect = BlockedError("blocked")
    fallback.fetch.return_value = b"<urlset/>"
    f.fetch("https://x.com/a.xml")

    f.close()
    primary.close.assert_called_once()
    fallback.close.assert_called_once()
