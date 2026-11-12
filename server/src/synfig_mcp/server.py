"""
MCP Server entrypoint for synfig-mcp.
Configures logging to stderr to maintain clean stdio transport, registers all typed tools,
and executes the MCP protocol loop.
"""

from __future__ import annotations

import argparse
import sys

from mcp.server.mcpserver import MCPServer

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.backend.select import get_backend
from synfig_mcp.config import ProfileType
from synfig_mcp.logging import configure_logging, get_logger
from synfig_mcp.tools import register_all_tools

configure_logging()
logger = get_logger("synfig_mcp.server")


def create_server(
    backend: BackendBase | None = None,
    profile: ProfileType | None = None,
) -> MCPServer:
    """Create and configure the MCPServer instance with tools filtered by profile."""
    active_backend = backend or get_backend()
    mcp_app = MCPServer("synfig-mcp")
    register_all_tools(mcp_app, active_backend, profile=profile)
    return mcp_app


mcp = create_server()


def _run_produce(parsed: argparse.Namespace) -> int:
    """Load a brief, run the production pipeline, and print the report."""
    import asyncio
    import json
    from pathlib import Path

    from synfig_mcp.backend.select import get_backend
    from synfig_mcp.production import AnimeProductionPipeline, ProductionBrief

    if parsed.brief == "-":
        raw = sys.stdin.read()
    else:
        try:
            raw = Path(parsed.brief).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"Cannot read brief '{parsed.brief}': {exc}", file=sys.stderr)
            return 2
    try:
        brief = ProductionBrief.model_validate(json.loads(raw))
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"Invalid brief: {exc}", file=sys.stderr)
        return 2

    pipeline = AnimeProductionPipeline(backend=get_backend(), output_dir=parsed.output_dir)
    report = asyncio.run(pipeline.run(brief, dry_run=parsed.dry_run))

    if parsed.json:
        print(json.dumps(report.model_dump(), indent=2, default=str))
    else:
        print(f"{report.title}  [{report.style}]  success={report.success}")
        for stage in report.stages:
            print(f"  {stage.name:<12} {stage.status:<8} {stage.detail}")
        for label, path in report.artifacts.items():
            print(f"  {label}: {path}")
        for warning in report.warnings:
            print(f"  warning: {warning}")
    return 0 if report.success else 1


def main(args: list[str] | None = None) -> None:
    """Run the MCP server over stdio or streamable HTTP transport, or run diagnostics."""
    raw_args = args if args is not None else sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="synfig-mcp",
        description="Live MCP control of Synfig Studio (native bridge + headless fallback)",
    )
    subparsers = parser.add_subparsers(dest="command")

    # synfig-mcp doctor
    subparsers.add_parser("doctor", help="Run system diagnostics and verify dependencies")

    # synfig-mcp usage-report
    subparsers.add_parser(
        "usage-report", help="Display token budget baseline and profile consumption metrics"
    )

    # synfig-mcp produce BRIEF.json
    produce = subparsers.add_parser(
        "produce",
        help="Run the one-command anime production pipeline from a JSON brief",
    )
    produce.add_argument(
        "brief",
        help="Path to a JSON brief, or '-' to read the brief from standard input",
    )
    produce.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan the run and report the stages without building a document",
    )
    produce.add_argument(
        "--output-dir",
        default=None,
        help="Directory for the .sif, video and contact sheet (default: <slug>_production)",
    )
    produce.add_argument(
        "--json",
        action="store_true",
        help="Print the full ProductionReport as JSON instead of a summary",
    )

    # server options
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for HTTP transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP transport (default: 8000)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Bearer token for HTTP authentication",
    )
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        default=False,
        help="Allow binding to non-loopback network interfaces (requires --token)",
    )
    parser.add_argument(
        "--allowed-hosts",
        nargs="*",
        default=["127.0.0.1", "localhost"],
        help="Allowed Host headers for HTTP transport",
    )

    parsed = parser.parse_args(raw_args)

    if parsed.command == "doctor":
        from synfig_mcp.doctor import run_doctor

        sys.exit(run_doctor())

    if parsed.command == "usage-report":
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        budget_doc = repo_root / "docs" / "TOKEN_BUDGET.md"
        if budget_doc.exists():
            print(budget_doc.read_text(encoding="utf-8"))
        else:
            print("Token budget documentation not found at docs/TOKEN_BUDGET.md")
        sys.exit(0)

    if parsed.command == "produce":
        sys.exit(_run_produce(parsed))

    if parsed.transport == "streamable-http":
        from synfig_mcp.http_transport import run_http_server

        logger.info(
            "Starting synfig-mcp server over streamable HTTP",
            host=parsed.host,
            port=parsed.port,
            auth_enabled=bool(parsed.token),
        )
        run_http_server(
            mcp_server=mcp,
            host=parsed.host,
            port=parsed.port,
            token=parsed.token,
            allow_remote=parsed.allow_remote,
            allowed_hosts=parsed.allowed_hosts,
        )
    else:
        logger.info("Starting synfig-mcp server over stdio transport")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
