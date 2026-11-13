"""
Guards that the marketing website stays in sync with the server registry.

The site's tool catalog and its "N tools" numbers are generated from the live
registry; if a tool is added, renamed or removed without regenerating the site,
these tests fail.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from generate_website_catalog import build  # type: ignore[import-not-found]  # noqa: E402


def test_website_catalog_and_counts_are_up_to_date() -> None:
    """website/script.js and website/index.html must match generated output."""
    stale = []
    for path, expected in build(REPO_ROOT).items():
        if path.read_text(encoding="utf-8") != expected:
            stale.append(path.relative_to(REPO_ROOT))
    assert not stale, (
        f"Website is out of date: {[str(p) for p in stale]}. "
        "Run: uv run python scripts/generate_website_catalog.py"
    )


def test_website_catalog_matches_registered_tools() -> None:
    """Every catalog entry must correspond to a real tool and vice versa."""
    import re

    from synfig_mcp.tools.register import TOOL_PROFILES

    script = (REPO_ROOT / "website" / "script.js").read_text(encoding="utf-8")
    catalog = set(re.findall(r'\{ name: "([a-z0-9_]+)",', script))

    assert catalog == set(TOOL_PROFILES), (
        "Website catalog and tool registry disagree: "
        f"missing={sorted(set(TOOL_PROFILES) - catalog)}, "
        f"extra={sorted(catalog - set(TOOL_PROFILES))}"
    )


def test_website_states_the_correct_total() -> None:
    """The hero and tools section must advertise the real tool count."""
    from synfig_mcp.tools.register import TOOL_PROFILES

    total = len(TOOL_PROFILES)
    html = (REPO_ROOT / "website" / "index.html").read_text(encoding="utf-8")
    assert f'<span class="stat-number">{total}</span>' in html
    assert f">{total} Typed MCP Tools<" in html
    assert f"All ({total})" in html
