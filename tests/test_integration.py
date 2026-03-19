"""Integration tests — require network access. Run with: pytest -m integration"""
import pytest
from pathlib import Path
from sitemap_downloader.cli import run

pytestmark = pytest.mark.integration


@pytest.mark.integration
def test_full_pipeline_finditparts(tmp_path):
    run([
        "https://www.finditparts.com/sitemap.xml",
        "--output", str(tmp_path),
        "--date", "2026-03-18",
    ])
    base = tmp_path / "finditparts.com" / "2026-03-18"
    assert (base / "OriginalFiles").exists()
    originals = list((base / "OriginalFiles").glob("*.xml"))
    assert len(originals) >= 1
    assert (base / "MergedSitemap" / "finditparts.com-2026-03-18.xml").exists()
    assert (base / "MergedSitemap" / "finditparts.com-2026-03-18.md").exists()

    # Check report has content
    report = (base / "MergedSitemap" / "finditparts.com-2026-03-18.md").read_text()
    assert "Total URLs" in report


@pytest.mark.integration
def test_full_pipeline_aloyoga(tmp_path):
    run([
        "https://www.aloyoga.com/sitemap.xml",
        "--output", str(tmp_path),
        "--date", "2026-03-18",
    ])
    base = tmp_path / "aloyoga.com" / "2026-03-18"
    assert (base / "MergedSitemap" / "aloyoga.com-2026-03-18.xml").exists()
    assert (base / "MergedSitemap" / "aloyoga.com-2026-03-18.md").exists()
