# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`obsidian-web-mcp` is a Python MCP server exposing read/write access to an Obsidian vault over Streamable HTTP, gated by OAuth 2.0 + bearer auth, designed to run behind a Cloudflare Tunnel. This repo is a community-maintained fork of `jimprosser/obsidian-web-mcp` — see README.md for fork positioning, integrated contributors, and the AI-tooling disclosure in CONTRIBUTING.md.

## Commands

Uses `uv` (Python 3.12+). All commands assume repo root as CWD.

```bash
uv sync                                                  # install deps
uv run pytest tests/ -v                                  # run all tests
uv run pytest tests/test_tools.py::test_vault_read -v    # run one test
uv run vault-mcp                                         # start the server
```

The server requires `VAULT_PATH`, `VAULT_MCP_TOKEN`, and `VAULT_OAUTH_CLIENT_SECRET` in env. Full config table is in README.

No linter, formatter, or type checker is configured (no `ruff`/`black`/`mypy`/pre-commit). Style is whatever the existing code shows.

## Architecture

Starlette app wrapping a FastMCP instance. Understanding how the layers compose requires reading several files together.

**Request lifecycle** (`src/obsidian_vault_mcp/server.py:main`):

1. `mcp.streamable_http_app()` produces the base MCP app.
2. A GET/HEAD probe at `/` is inserted (MCP spec 2025-06-18 requires it to return `MCP-Protocol-Version`).
3. OAuth routes from `oauth.py` are prepended.
4. `BearerAuthMiddleware` (`auth.py`) wraps the whole app. Its exemption list (`_AUTH_EXEMPT_PATHS` / `_AUTH_EXEMPT_METHOD_PATHS`) covers OAuth endpoints and the spec probe; everything else requires `Authorization: Bearer $VAULT_MCP_TOKEN` validated via `hmac.compare_digest`.
5. Each `@mcp.tool` in `server.py` is a thin shim: construct a Pydantic input from `models.py`, delegate to the implementation in `tools/{read,write,search,manage}.py`.

**Fallback trap**: if custom app assembly raises, `main()` falls back to `mcp.run()` which runs **without auth**. Any change that might break app assembly needs testing against this path; a silent fallback to an unauthenticated server is a real risk.

**OAuth vs bearer split**: OAuth endpoints (`/authorize`, `/oauth/token`, `/oauth/register`, `/.well-known/*`) are how Claude negotiates the bearer token in the first place — chicken-and-egg, so they're exempt from bearer auth. Every actual tool call after that is bearer-authenticated. These are two separate auth systems that share no state beyond the eventual token.

**Path security invariant**: every filesystem operation must route through `vault.py:resolve_vault_path()`, which blocks null bytes, dot-prefixed components (so `.obsidian`, `.git`, `.trash` stay unreachable), and paths resolving outside `VAULT_PATH`. When adding a new tool this is non-negotiable — don't call `Path(VAULT_PATH / x)` directly.

**Atomic writes**: `vault.py:write_file_atomic()` writes to a tempfile in the target's directory then `os.replace()`s. This is what keeps Obsidian Sync from ever seeing a partial file. Don't bypass with `path.write_text()`.

**Frontmatter index** (`frontmatter_index.py`): process-wide singleton, started once in `server.py:main()` with `atexit` stop. **Not** per-session — the MCP lifespan fires on each new session and re-scheduling the same watchdog observer crashes. A watchdog observer feeds `.md` changes into a debounced flush (`FRONTMATTER_INDEX_DEBOUNCE` seconds in `config.py`) so bulk saves coalesce into one reparse. All mutations hold a `threading.Lock`.

**Public-URL detection** (`oauth.py`): OAuth discovery metadata must advertise the public `https://` URL, not the internal `http://` that `request.base_url` returns behind a tunnel. A `_public_base_url(request)` helper has tiered detection: `VAULT_PUBLIC_BASE_URL` env → `X-Forwarded-Proto`/`X-Forwarded-Host` → `CF-Visitor` (Cloudflare) → force https when non-loopback. Get this wrong and MCP clients fail discovery.

**Config loading** (`config.py`): plain module-level env reads at import time. Tests monkeypatch `config.VAULT_PATH` directly in the `vault_dir` fixture rather than relying on reimport — when adding a new env-driven setting that tests need, update the fixture too.

## Testing conventions

- All tests use the `vault_dir` fixture in `tests/conftest.py`, which creates a tmp vault with sample `.md` files (including frontmatter + an `.obsidian/` dir to exercise exclusion) and monkeypatches `VAULT_PATH` + `VAULT_MCP_TOKEN`.
- Tests exercise tool implementation functions directly, not over the MCP transport. There is no integration test for the HTTP/auth layer — verify those manually if touched.
- Purely functional: no network, no external services, no real vault.
