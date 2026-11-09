#!/usr/bin/env python3
"""Render the Markdown body for a GitHub release."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO_URL = "https://github.com/anusara-bemal/synfig-mcp"


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GB"


def changelog_section(changelog: Path, version: str) -> str:
    if not changelog.is_file():
        return ""
    text = changelog.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def checksum_map(checksum_file: Path) -> dict[str, str]:
    if not checksum_file.is_file():
        return {}
    result: dict[str, str] = {}
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            result[parts[1].strip()] = parts[0].strip()
    return result


def render(tag: str, dist: Path) -> str:
    version = tag.removeprefix("v")
    checksums = checksum_map(dist / "SHA256SUMS.txt")
    files = sorted(
        (p for p in dist.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt"),
        key=lambda p: p.name,
    )

    wheel = next((p.name for p in files if p.name.endswith(".whl")), None)
    source_bundle = next(
        (p.name for p in files if p.name.startswith("synfig-mcp-gpl-source")), None
    )
    windows_bundle = next((p.name for p in files if p.name.endswith(".zip")), None)
    linux_bundle = next(
        (
            p.name
            for p in files
            if p.name.endswith(".tar.gz") and "synfigstudio-linux" in p.name
        ),
        None,
    )
    prerelease = any(marker in version.lower() for marker in ("rc", "beta", "alpha"))

    lines: list[str] = [
        f"# synfig-mcp {tag}",
        "",
        (
            "Model Context Protocol server for Synfig Studio, with live canvas automation "
            "and a headless render fallback."
        ),
        "",
    ]
    if prerelease:
        lines += [
            (
                "> **Pre-release.** This build is ready for evaluation and daily use, but the "
                "tool surface may still change before the next stable tag."
            ),
            "",
        ]

    section = changelog_section(Path("CHANGELOG.md"), version)
    if section:
        lines += ["## What changed", "", section, ""]

    lines += ["## Installation", ""]
    if wheel:
        lines += [
            "Python server (wheel attached below):",
            "",
            "```bash",
            f'uv pip install "{REPO_URL}/releases/download/{tag}/{wheel}"',
            "synfig-mcp doctor",
            "```",
            "",
        ]
    lines += [
        "Container image:",
        "",
        "```bash",
        f"docker pull ghcr.io/anusara-bemal/synfig-mcp:{version}",
        "```",
        "",
    ]
    if windows_bundle or linux_bundle:
        lines += ["Patched Synfig Studio bundles:", ""]
        if windows_bundle:
            lines.append(f"- **Windows (UCRT64):** `{windows_bundle}`")
        if linux_bundle:
            lines.append(f"- **Linux x64:** `{linux_bundle}`")
        lines.append("")

    if files:
        lines += [
            "## Release assets",
            "",
            "| Asset | Size | SHA-256 |",
            "|---|---:|---|",
        ]
        for path in files:
            digest = checksums.get(path.name, "")
            short = f"`{digest[:16]}...`" if digest else "—"
            lines.append(
                f"| `{path.name}` | {human_size(path.stat().st_size)} | {short} |"
            )
        lines.append("")

    if source_bundle:
        lines += [
            "## GPL source",
            "",
            (
                f"`{source_bundle}` contains the complete corresponding source for Synfig Studio "
                "at the pinned commit, the MCP bridge sources, patches, build scripts, and "
                "third-party license manifests, as required by GPL-3.0 section 6."
            ),
            "",
        ]

    lines += [
        "## Verify downloads",
        "",
        "```bash",
        "sha256sum -c SHA256SUMS.txt",
        "```",
        "",
        "## Documentation",
        "",
        f"- [Quick start and client setup]({REPO_URL}#quick-start)",
        f"- [Tools API]({REPO_URL}/blob/{tag}/docs/api.md)",
        f"- [Troubleshooting]({REPO_URL}/blob/{tag}/docs/troubleshooting.md)",
        f"- [Security policy]({REPO_URL}/blob/{tag}/SECURITY.md)",
        f"- [GPL compliance]({REPO_URL}/blob/{tag}/docs/gpl-compliance.md)",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="Release tag, for example v0.8.0-rc2")
    parser.add_argument("dist", type=Path, help="Directory containing release assets")
    args = parser.parse_args()
    print(render(args.tag, args.dist))


if __name__ == "__main__":
    main()
