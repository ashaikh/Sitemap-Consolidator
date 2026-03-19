"""Merge multiple sitemap XML files into a single master sitemap."""

import xml.etree.ElementTree as ET
from pathlib import Path

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def extract_urls_from_file(filepath: Path) -> list[str]:
    """Extract all <loc> URLs from a sitemap XML file."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    ns = {"sm": SITEMAP_NS}
    return [loc.text for loc in root.findall(".//sm:url/sm:loc", ns) if loc.text]


def merge_sitemaps(sitemap_files: list[Path], output_path: Path) -> int:
    """Merge multiple sitemap files into one master sitemap.

    Args:
        sitemap_files: List of paths to individual sitemap XML files
        output_path: Where to write the merged sitemap

    Returns:
        Total number of URLs in the merged sitemap
    """
    all_urls: list[str] = []
    for f in sitemap_files:
        all_urls.extend(extract_urls_from_file(f))

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_urls: list[str] = []
    for url in all_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    # Build merged XML
    ET.register_namespace("", SITEMAP_NS)
    urlset = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for url in unique_urls:
        url_elem = ET.SubElement(urlset, f"{{{SITEMAP_NS}}}url")
        loc_elem = ET.SubElement(url_elem, f"{{{SITEMAP_NS}}}loc")
        loc_elem.text = url

    tree = ET.ElementTree(urlset)
    ET.indent(tree, space="  ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, xml_declaration=True, encoding="unicode")

    return len(unique_urls)
