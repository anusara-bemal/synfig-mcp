"""
Subprocess runner for synfig CLI introspection and rendering.
"""

import asyncio
import json
import shutil
from pathlib import Path

from synfig_mcp.config import settings
from synfig_mcp.schema.registry import LayerParamInfo, LayerTypeInfo


class CliRunner:
    """Invokes synfig CLI for introspection and rendering."""

    #: Layer catalogues are shared between runner instances (and cached on
    #: disk), because introspecting them spawns one subprocess per layer type.
    _catalog_cache: dict[str, dict[str, LayerTypeInfo]] = {}

    def __init__(self, binary_path: Path | None = None) -> None:
        self.binary_path = binary_path or self._discover_binary()
        self._layer_catalog: dict[str, LayerTypeInfo] | None = None
        self._layer_names: list[str] | None = None

    def _catalog_cache_key(self) -> str:
        """Cache key of the layer catalogue for the current binary."""
        path = self.binary_path
        if path is None:
            return "none"
        try:
            stat = path.stat()
            return f"{path.resolve()}:{stat.st_mtime_ns}:{stat.st_size}"
        except OSError:
            return str(path)

    def _catalog_disk_path(self) -> Path:
        import hashlib

        digest = hashlib.sha256(self._catalog_cache_key().encode("utf-8")).hexdigest()[:16]
        return Path.home() / ".synfig" / "mcp_cache" / f"layer_catalog_{digest}.json"

    async def get_layer_catalog(self) -> dict[str, LayerTypeInfo]:
        """Return (and cache) the full layer catalog of the Synfig binary.

        Each entry carries the layer version and the list of parameters the
        engine knows about, which the writer needs to emit valid documents.
        The catalogue is cached in memory and on disk, because introspecting it
        spawns one subprocess per layer type.
        """
        if self._layer_catalog is not None:
            return self._layer_catalog

        key = self._catalog_cache_key()
        catalog = CliRunner._catalog_cache.get(key)
        if catalog is None:
            catalog = self._load_catalog_from_disk()
        if catalog is None:
            catalog = {}
            for name in await self.get_layers():
                info = await self.get_layer_info(name)
                catalog[name] = info or LayerTypeInfo(name=name)
            self._save_catalog_to_disk(catalog)
        CliRunner._catalog_cache[key] = catalog
        self._layer_catalog = catalog
        return catalog

    def _load_catalog_from_disk(self) -> dict[str, LayerTypeInfo] | None:
        """Load a previously introspected catalogue from the disk cache."""
        path = self._catalog_disk_path()
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {name: LayerTypeInfo.model_validate(info) for name, info in data.items()}
        except Exception:
            return None

    def _save_catalog_to_disk(self, catalog: dict[str, LayerTypeInfo]) -> None:
        """Store the introspected catalogue for the next process."""
        path = self._catalog_disk_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {name: info.model_dump() for name, info in catalog.items()}
            path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            pass

    async def get_layer_version(self, layer_name: str) -> str | None:
        """Return the version string of a layer type (e.g. ``0.2``)."""
        catalog = await self.get_layer_catalog()
        info = catalog.get(layer_name)
        return info.version if info else None

    async def is_valid_layer_type(self, layer_name: str) -> bool:
        """Check whether the Synfig binary knows the given layer type."""
        if not self.is_available:
            # Without a binary we cannot validate; assume the type is valid so
            # offline usage keeps working.
            return True
        catalog = await self.get_layer_catalog()
        if layer_name in catalog:
            return True
        # Studio uses a few aliases for the same layer (e.g. "group" ->
        # "PasteCanvas").
        return layer_name.lower() in {name.lower() for name in catalog}

    def _discover_binary(self) -> Path | None:
        """Find the synfig CLI binary from config, PATH, or local build trees."""
        if settings.synfig_cli_path and settings.synfig_cli_path.is_file():
            return settings.synfig_cli_path

        which_synfig = shutil.which("synfig") or shutil.which("synfig.exe")
        if which_synfig:
            return Path(which_synfig)

        # Look for local build outputs in project workspace
        candidates = [
            Path.cwd() / "build_synfig" / "build_ucrt64" / "install" / "bin" / "synfig.exe",
            Path.cwd()
            / "build_synfig"
            / "build_ucrt64"
            / "output"
            / "Release"
            / "bin"
            / "synfig.exe",
            Path(__file__).parents[4]
            / "build_synfig"
            / "build_ucrt64"
            / "install"
            / "bin"
            / "synfig.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate

        return None

    @property
    def is_available(self) -> bool:
        """Check if synfig binary is found and executable."""
        return self.binary_path is not None and self.binary_path.is_file()

    async def get_version(self) -> str | None:
        """Get version string from synfig CLI."""
        if not self.is_available or self.binary_path is None:
            return None

        try:
            proc = await asyncio.create_subprocess_exec(
                str(self.binary_path),
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            out_str = stdout.decode("utf-8", errors="replace").strip()
            if not out_str:
                out_str = stderr.decode("utf-8", errors="replace").strip()
            # Synfig returns exit code 3 (SYNFIGTOOL_HELP) or 0
            if proc.returncode in (0, 3) and out_str:
                for line in out_str.splitlines():
                    clean = line.strip()
                    if clean and not clean.startswith("synfig(") and not clean.startswith("mlt_"):
                        # The CLI prints "synfig 1.5.5"; keep the bare version.
                        if clean.lower().startswith("synfig "):
                            clean = clean[len("synfig ") :].strip()
                        return clean
            return out_str or None
        except Exception:
            return None

    async def get_layers(self) -> list[str]:
        """List available layer types via synfig -q --layers."""
        if not self.is_available or self.binary_path is None:
            return []

        try:
            proc = await asyncio.create_subprocess_exec(
                str(self.binary_path),
                "-q",
                "--layers",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            layers: list[str] = []
            for line in stdout.decode("utf-8", errors="replace").splitlines():
                name = line.strip()
                if name and not name.startswith("synfig(") and not name.startswith("mlt_"):
                    layers.append(name)
            return layers
        except Exception:
            return []

    async def get_layer_info(self, layer_name: str) -> LayerTypeInfo | None:
        """Inspect layer parameters via synfig -q --layer-info=<layer_name>."""
        if not self.is_available or self.binary_path is None:
            return None

        try:
            proc = await asyncio.create_subprocess_exec(
                str(self.binary_path),
                "-q",
                f"--layer-info={layer_name}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            lines = stdout.decode("utf-8", errors="replace").splitlines()
            if not lines:
                return None

            info = LayerTypeInfo(name=layer_name)
            current_param: LayerParamInfo | None = None

            for line in lines:
                raw_line = line.strip()
                if not raw_line or raw_line.startswith("synfig(") or raw_line.startswith("mlt_"):
                    continue

                if raw_line.startswith("Layer Name:"):
                    info.name = raw_line.split(":", 1)[1].strip()
                elif raw_line.startswith("Localized Layer Name:"):
                    info.localized_name = raw_line.split(":", 1)[1].strip()
                elif raw_line.startswith("Version:"):
                    info.version = raw_line.split(":", 1)[1].strip()
                elif raw_line.startswith("param -"):
                    if current_param:
                        info.params[current_param.name] = current_param
                    p_name = raw_line.split("-", 1)[1].strip()
                    current_param = LayerParamInfo(name=p_name)
                elif line.startswith(("\t", "    ")) and current_param and ":" in raw_line:
                    k, v = raw_line.split(":", 1)
                    k = k.strip()
                    v = v.strip()
                    if k == "Localized Name":
                        current_param.localized_name = v
                    elif k == "Description":
                        current_param.description = v
                    elif k == "Hint":
                        current_param.hint = v
                    elif k == "Type":
                        current_param.type = v

            if current_param:
                info.params[current_param.name] = current_param

            return info if info.params or info.name else None
        except Exception:
            return None

    async def get_targets(self) -> list[str]:
        """List available render targets via synfig -q --targets."""
        if not self.is_available or self.binary_path is None:
            return []

        try:
            proc = await asyncio.create_subprocess_exec(
                str(self.binary_path),
                "-q",
                "--targets",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            targets: list[str] = []
            for line in stdout.decode("utf-8", errors="replace").splitlines():
                t = line.strip()
                if t and not t.startswith("synfig(") and not t.startswith("mlt_"):
                    targets.append(t)
            return targets
        except Exception:
            return []

    async def get_renderers(self) -> list[str]:
        """List available render engines via synfig -q --renderers.

        The CLI prints ``<name> - <description>`` lines, e.g.
        ``software-draft - Cobra Draft (software)``.  Only the separator
        ``" - "`` marks the end of the name, so names such as
        ``software-low2`` keep their suffix.
        """
        if not self.is_available or self.binary_path is None:
            return []

        try:
            proc = await asyncio.create_subprocess_exec(
                str(self.binary_path),
                "-q",
                "--renderers",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            renderers: list[str] = []
            for line in stdout.decode("utf-8", errors="replace").splitlines():
                r = line.strip()
                if r and not r.startswith("synfig(") and not r.startswith("mlt_"):
                    name = r.split(" - ", 1)[0].strip()
                    renderers.append(name or r)
            return renderers
        except Exception:
            return []

    async def get_valuenodes(self) -> list[str]:
        """List available valuenode types via synfig -q --valuenodes."""
        if not self.is_available or self.binary_path is None:
            return []

        try:
            proc = await asyncio.create_subprocess_exec(
                str(self.binary_path),
                "-q",
                "--valuenodes",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            valuenodes: list[str] = []
            for line in stdout.decode("utf-8", errors="replace").splitlines():
                v = line.strip()
                if v and not v.startswith("synfig(") and not v.startswith("mlt_"):
                    valuenodes.append(v)
            return valuenodes
        except Exception:
            return []

    async def render_frame(
        self,
        sif_path: Path,
        output_path: Path,
        time: float | str = 0.0,
        width: int | None = None,
        height: int | None = None,
        target: str = "png",
        antialias: int = 2,
    ) -> bool:
        """Render a single frame of a .sif/.sifz/.sfg document to an image."""
        if not self.is_available or self.binary_path is None:
            return False

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        time_str = f"{time}s" if isinstance(time, (int, float)) else str(time)
        args = [
            str(self.binary_path),
            "-q",
            str(sif_path),
            "-t",
            target,
            "-o",
            str(output_path),
            "--time",
            time_str,
            "-a",
            str(antialias),
        ]
        if width is not None and width > 0:
            args.extend(["-w", str(width)])
        if height is not None and height > 0:
            args.extend(["-h", str(height)])

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return output_path.is_file() and output_path.stat().st_size > 0
        except Exception:
            return False

    async def render_sequence(
        self,
        sif_path: Path,
        output_path: Path,
        begin_time: float | str = 0.0,
        end_time: float | str = 1.0,
        fps: float = 24.0,
        width: int | None = None,
        height: int | None = None,
        target: str = "png",
    ) -> bool:
        """Render animation frames to output sequence or video."""
        if not self.is_available or self.binary_path is None:
            return False

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        begin_str = f"{begin_time}s" if isinstance(begin_time, (int, float)) else str(begin_time)
        end_str = f"{end_time}s" if isinstance(end_time, (int, float)) else str(end_time)

        args = [
            str(self.binary_path),
            "-q",
            str(sif_path),
            "-t",
            target,
            "-o",
            str(output_path),
            "--begin-time",
            begin_str,
            "--end-time",
            end_str,
            "--fps",
            f"{fps:.3f}",
        ]
        if width is not None and width > 0:
            args.extend(["-w", str(width)])
        if height is not None and height > 0:
            args.extend(["-h", str(height)])

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode in (0, 3)
        except Exception:
            return False
