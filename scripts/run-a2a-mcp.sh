#!/usr/bin/env bash
# Launch A2A-over-git MCP over stdio. Identity: .git/agents/whoami (not in this script).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "mcp_a2a: missing $ROOT/.venv — run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi
if [[ ! -f "$ROOT/.git/agents/whoami" ]]; then
  echo "mcp_a2a: missing .git/agents/whoami — e.g. echo analyst-agent > .git/agents/whoami" >&2
  exit 1
fi
exec "$ROOT/.venv/bin/python" -m mcp_a2a
