# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| `0.8.x` (current pre-release line) | :white_check_mark: |
| `0.7.x` and older | :x: |

Security fixes are shipped on the latest release line. Upgrade to the newest `v0.8.x` tag before reporting an issue that may already be fixed.

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Use GitHub's private vulnerability reporting:

1. Open the [Security advisories](https://github.com/anusara-bemal/synfig-mcp/security/advisories) page.
2. Choose **Report a vulnerability**.
3. Include the affected version/tag, platform, reproduction steps, and impact.

You can expect:

- acknowledgement within **48 hours**,
- an initial assessment within **5 business days**,
- coordinated disclosure after a fix is available.

If GitHub private reporting is unavailable, contact the repository owner through their GitHub profile and request a private channel.

## Scope

In scope:

- the Python MCP server (`server/`),
- the native Studio bridge and patches (`bridge/`),
- build, packaging, and release workflows,
- the container image and published release artifacts.

Out of scope:

- vulnerabilities in upstream Synfig Studio or third-party libraries that are already public and have an upstream fix (report them upstream; tell us if our pinned build is affected),
- issues that require an already-compromised local account or physical access,
- social engineering.

## Security model

- The live bridge binds to loopback and requires a per-session token stored in a user-only file.
- HTTP transport refuses non-loopback binding without an explicit token.
- File operations are sandboxed to configured workspace roots, including symlink/junction resolution.
- Asset downloads resolve DNS first and block loopback, private, link-local, and cloud-metadata addresses.
- SVG assets are DOM-sanitized; raster downloads are magic-byte validated.
- Tool output derived from documents is wrapped with an untrusted-content notice.
- Workflows use least-privilege permissions and publish only from immutable `v*` tags.

See [docs/security.md](docs/security.md) for the full threat model.
