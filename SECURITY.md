# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Model & Sandboxing

`synfig-mcp` is designed to be executed safely by automated AI agents. To prevent malicious activity, several hardening layers are enforced:

1. **Workspace Sandboxing**: All file paths (project reads, writes, asset imports, render outputs) are strictly resolved against `SYNFIG_MCP_WORKSPACE`. Any path escaping via `..` or symlinks is rejected immediately with a `WorkspaceError`.
2. **Subprocess Safety**: CLI binary invocations use `asyncio.create_subprocess_exec` with explicit argument lists. Shell execution (`shell=True`) is strictly prohibited to eliminate command injection.
3. **Resource Quotas**: Hard boundaries prevent Denial-of-Service attacks:
   - Maximum canvas dimensions (default 8192x8192)
   - Maximum frame count per render job (default 10,000)
   - Maximum file size per project (default 100 MB)
   - Layer count caps per document (default 500)
   - Render subprocess timeouts (default 300s)
4. **Secret Protection**: Logs are strictly directed to `stderr` and sanitized; no sensitive credentials or tokens are logged.

## Reporting a Vulnerability

If you discover a potential security vulnerability in this project, please report it responsibly:

- **Do NOT create a public GitHub issue.**
- Email details of the vulnerability to **Anusara Bemal (ABM)** directly.
- Include reproduction steps and potential impact.

We will acknowledge receipt of your vulnerability report within 48 hours and provide regular updates on remediation.
