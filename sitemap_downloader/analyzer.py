"""Analyze sitemap URLs and generate markdown reports."""

from collections import defaultdict
from datetime import date
from urllib.parse import urlparse


def count_sections(urls: list[str], max_depth: int = 3) -> dict[str, int]:
    """Count URLs by path section up to max_depth levels.

    Each URL contributes to every level of its path hierarchy.
    E.g., /products/shoes/running counts toward:
      /products (level 1), /products/shoes (level 2), /products/shoes/running (level 3)

    Args:
        urls: List of full URLs
        max_depth: Maximum path depth to analyze (default 3)

    Returns:
        Dict mapping path prefixes to URL counts
    """
    counts: dict[str, int] = defaultdict(int)

    for url in urls:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")

        if not path:
            counts["/"] += 1
            continue

        segments = path.strip("/").split("/")
        for depth in range(1, min(len(segments), max_depth) + 1):
            prefix = "/" + "/".join(segments[:depth])
            counts[prefix] += 1

    return dict(counts)


def generate_report(urls: list[str], site_name: str) -> str:
    """Generate a markdown analysis report for the given URLs.

    Args:
        urls: List of all URLs from the sitemap
        site_name: Display name of the site

    Returns:
        Markdown string with the report
    """
    total = len(urls)
    counts = count_sections(urls, max_depth=3)
    today = date.today().isoformat()

    # Sort sections: level 1 first, then by count descending
    level_1 = {k: v for k, v in counts.items() if k.count("/") == 1 and k != "/"}
    level_1_sorted = sorted(level_1.items(), key=lambda x: x[1], reverse=True)

    lines = [
        f"# Sitemap Analysis: {site_name}",
        f"",
        f"**Date:** {today}",
        f"**Total URLs:** {total:,}",
        f"",
        f"## Top-Level Sections",
        f"",
        f"| Section | URLs | % of Total |",
        f"|---------|------|-----------|",
    ]

    for section, count in level_1_sorted:
        pct = (count / total) * 100
        lines.append(f"| `{section}` | {count:,} | {pct:.1f}% |")

    # Homepage / root
    root_count = counts.get("/", 0)
    if root_count:
        pct = (root_count / total) * 100
        lines.append(f"| `/` (root) | {root_count:,} | {pct:.1f}% |")

    # Detailed breakdown (levels 2-3)
    lines.extend(["", "## Detailed Breakdown (up to 3 levels)", ""])

    for section, _ in level_1_sorted:
        # Find all sub-sections under this top-level
        sub_sections = {
            k: v for k, v in counts.items()
            if k.startswith(section + "/") and k != section
        }
        if not sub_sections:
            continue

        lines.append(f"### `{section}`")
        lines.append("")
        lines.append(f"| Sub-section | URLs |")
        lines.append(f"|-------------|------|")

        sub_sorted = sorted(sub_sections.items(), key=lambda x: x[1], reverse=True)
        for sub, count in sub_sorted[:20]:  # Cap at 20 to keep report readable
            lines.append(f"| `{sub}` | {count:,} |")

        if len(sub_sorted) > 20:
            lines.append(f"| ... and {len(sub_sorted) - 20} more | |")
        lines.append("")

    return "\n".join(lines)
