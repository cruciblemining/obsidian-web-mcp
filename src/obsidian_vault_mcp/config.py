import os
from pathlib import Path

# Vault configuration
VAULT_PATH = Path(os.environ.get("VAULT_PATH", os.path.expanduser("~/Obsidian/MyVault")))
VAULT_MCP_TOKEN = os.environ.get("VAULT_MCP_TOKEN", "")
VAULT_MCP_PORT = int(os.environ.get("VAULT_MCP_PORT", "8420"))

# OAuth 2.0 client credentials (for Claude app integration)
VAULT_OAUTH_CLIENT_ID = os.environ.get("VAULT_OAUTH_CLIENT_ID", "vault-mcp-client")
VAULT_OAUTH_CLIENT_SECRET = os.environ.get("VAULT_OAUTH_CLIENT_SECRET", "")

# DNS rebinding protection: additional allowed hostnames beyond localhost.
# Comma-separated list, e.g. "vault-mcp.example.com,vault-mcp.example.net"
# The standard localhost/127.0.0.1/[::1] entries are always included.
VAULT_MCP_ALLOWED_HOSTS: list[str] = [
    h.strip()
    for h in os.environ.get("VAULT_MCP_ALLOWED_HOSTS", "").split(",")
    if h.strip()
]

# Post-write hook command (optional).
# When set, this shell command is executed fire-and-forget after every vault
# mutation.  Two env vars are injected:
#   MCP_OPERATION  — e.g. "created", "updated", "deleted", "moved"
#   MCP_PATHS      — colon-separated vault-relative paths of affected files
VAULT_MCP_POST_WRITE_CMD = os.environ.get("VAULT_MCP_POST_WRITE_CMD", "")

# Optional HTTP heartbeat URL (push-style health checks).
# When set, the server GETs this URL every HEARTBEAT_INTERVAL seconds.
# Works with Uptime Kuma, Healthchecks.io, Cronitor, or any push endpoint.
VAULT_MCP_HEARTBEAT_URL = os.environ.get("VAULT_MCP_HEARTBEAT_URL", "")
VAULT_MCP_HEARTBEAT_INTERVAL = int(os.environ.get("VAULT_MCP_HEARTBEAT_INTERVAL", "60"))

# Public base URL override (optional).
# When set, OAuth metadata endpoints advertise this URL instead of deriving
# it from request headers. Useful behind proxies/tunnels (Cloudflare Tunnel
# uses CF-Visitor, standard reverse proxies use X-Forwarded-Proto; explicit
# override sidesteps all detection). Example: "https://vault-mcp.example.com".
VAULT_PUBLIC_BASE_URL = os.environ.get("VAULT_PUBLIC_BASE_URL", "").strip().rstrip("/")

# Safety limits
MAX_CONTENT_SIZE = 1_000_000  # 1MB max write size
MAX_BATCH_SIZE = 20           # Max files per batch operation
MAX_SEARCH_RESULTS = 50       # Max results per search
DEFAULT_SEARCH_RESULTS = 20
MAX_LIST_DEPTH = 5            # Max directory recursion depth
CONTEXT_LINES = 2             # Default lines of context in search results

# Directories to never expose or modify
EXCLUDED_DIRS = {".obsidian", ".trash", ".git", ".DS_Store"}

# Frontmatter index refresh interval (seconds)
FRONTMATTER_INDEX_DEBOUNCE = 5.0

# Rate limiting (requests per minute) -- track in-memory, enforce per-token
RATE_LIMIT_READ = 100
RATE_LIMIT_WRITE = 30
