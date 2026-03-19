import pytest
from pathlib import Path

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

SAMPLE_SITEMAP_INDEX = f"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="{SITEMAP_NS}">
  <sitemap>
    <loc>https://www.example.com/sitemap-products.xml</loc>
  </sitemap>
  <sitemap>
    <loc>https://www.example.com/sitemap-pages.xml.gz</loc>
  </sitemap>
</sitemapindex>"""

SAMPLE_SITEMAP_1 = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="{SITEMAP_NS}">
  <url><loc>https://www.example.com/products/shoes</loc></url>
  <url><loc>https://www.example.com/products/shoes/running</loc></url>
  <url><loc>https://www.example.com/products/hats</loc></url>
</urlset>"""

SAMPLE_SITEMAP_2 = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="{SITEMAP_NS}">
  <url><loc>https://www.example.com/about</loc></url>
  <url><loc>https://www.example.com/blog/2024/post-1</loc></url>
  <url><loc>https://www.example.com/blog/2024/post-2</loc></url>
</urlset>"""


@pytest.fixture
def sample_sitemap_index():
    return SAMPLE_SITEMAP_INDEX


@pytest.fixture
def sample_sitemap_1():
    return SAMPLE_SITEMAP_1


@pytest.fixture
def sample_sitemap_2():
    return SAMPLE_SITEMAP_2


@pytest.fixture
def sample_original_files(tmp_path, sample_sitemap_1, sample_sitemap_2):
    """Write two sample sitemap files to a tmp dir, return the dir path."""
    originals = tmp_path / "OriginalFiles"
    originals.mkdir()
    (originals / "sitemap-products.xml").write_text(sample_sitemap_1)
    (originals / "sitemap-pages.xml").write_text(sample_sitemap_2)
    return originals
