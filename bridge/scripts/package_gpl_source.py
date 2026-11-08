#!/usr/bin/env python3
"""
Packages the complete and corresponding GPL-3.0 source bundle for Synfig Studio MCP release.

Includes:
- Upstream Synfig source tree at pinned commit 1b623cf577e163d0c3ebf4922dc9fb28e7c1f8fa
- MCP bridge source code, patches, and build scripts
- Third-party licensing manifests and GPL compliance documentation
"""

import os
import shutil
import subprocess
import tarfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DIST_DIR = REPO_ROOT / "dist"
SYNFIG_SRC = REPO_ROOT / "build_synfig" / "synfig_src"
VERSION = os.environ.get("SYNFIG_MCP_VERSION", "v0.8.0-rc1")
if not VERSION.startswith("v"):
    VERSION = f"v{VERSION}"
OUTPUT_TAR = DIST_DIR / f"synfig-mcp-gpl-source-{VERSION}.tar.gz"


def main() -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    temp_bundle_dir = DIST_DIR / f"synfig-mcp-gpl-source-{VERSION}"
    if temp_bundle_dir.exists():
        shutil.rmtree(temp_bundle_dir)
    temp_bundle_dir.mkdir(parents=True)

    pinned_commit = (REPO_ROOT / "bridge" / "PINNED_COMMIT").read_text().strip()
    print(f"[gpl_package] Packaging GPL source bundle into {OUTPUT_TAR} (pinned commit: {pinned_commit})...")

    # 1. Export or copy upstream Synfig at pinned commit
    upstream_target = temp_bundle_dir / "synfig-upstream"
    if (SYNFIG_SRC / ".git").exists():
        print(f"[gpl_package] Exporting pinned git commit {pinned_commit}...")
        upstream_target.mkdir(parents=True)
        tar_path = temp_bundle_dir / "upstream.tar"
        subprocess.run(
            ["git", "-C", str(SYNFIG_SRC), "archive", "--format=tar", "-o", str(tar_path), pinned_commit],
            check=True,
        )
        with tarfile.open(tar_path, "r") as t:
            t.extractall(path=upstream_target)
        tar_path.unlink()
    else:
        print("[gpl_package] Warning: synfig_src not found; creating stub upstream instructions.")
        upstream_target.mkdir(parents=True)
        (upstream_target / "SOURCE_README.txt").write_text(
            f"Clone https://github.com/synfig/synfig.git at commit {pinned_commit}\n"
        )

    # 2. Copy bridge directory (patches, src, scripts)
    bridge_target = temp_bundle_dir / "bridge"
    shutil.copytree(REPO_ROOT / "bridge", bridge_target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))

    # 3. Copy documentation and license files
    docs_target = temp_bundle_dir / "docs"
    docs_target.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO_ROOT / "docs" / "gpl-compliance.md", docs_target / "gpl-compliance.md")
    shutil.copy(REPO_ROOT / "bridge" / "THIRD_PARTY_LICENSES.md", temp_bundle_dir / "THIRD_PARTY_LICENSES.md")
    if (REPO_ROOT / "bridge" / "MSYS2_SOURCE_MANIFEST.md").exists():
        shutil.copy(REPO_ROOT / "bridge" / "MSYS2_SOURCE_MANIFEST.md", temp_bundle_dir / "MSYS2_SOURCE_MANIFEST.md")
    shutil.copy(REPO_ROOT / "LICENSE", temp_bundle_dir / "LICENSE")

    # 4. Create tar.gz archive
    print(f"[gpl_package] Writing tarball {OUTPUT_TAR}...")
    with tarfile.open(OUTPUT_TAR, "w:gz") as tar:
        tar.add(temp_bundle_dir, arcname=f"synfig-mcp-gpl-source-{VERSION}")

    shutil.rmtree(temp_bundle_dir)
    size_mb = OUTPUT_TAR.stat().st_size / (1024 * 1024)
    print(f"[gpl_package] Successfully generated {OUTPUT_TAR.name} ({size_mb:.2f} MB)")

    import hashlib

    sha256 = hashlib.sha256(OUTPUT_TAR.read_bytes()).hexdigest()
    sha_file = OUTPUT_TAR.with_name(f"{OUTPUT_TAR.name}.sha256")
    sha_file.write_text(f"{sha256}  {OUTPUT_TAR.name}\n", encoding="utf-8")
    print(f"[gpl_package] Checksum: {sha256} saved to {sha_file.name}")


if __name__ == "__main__":
    main()
