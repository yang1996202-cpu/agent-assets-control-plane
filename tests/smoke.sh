#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_HOME="${TMPDIR:-/tmp}/agent-assets-control-plane-smoke"
rm -rf "$TMP_HOME"
mkdir -p "$TMP_HOME"
python3 -m py_compile "$ROOT"/bin/agent-assets-*
python3 -m json.tool "$ROOT/templates/agent-assets/registry.example.json" >/dev/null
python3 -m json.tool "$ROOT/templates/agent-assets/discovery-review.example.json" >/dev/null
python3 -m json.tool "$ROOT/templates/mcp/registry.example.json" >/dev/null

AGENT_ASSETS_USER_HOME="$TMP_HOME" \
AGENT_ASSETS_SCAN_DIRS="$TMP_HOME/.local/bin" \
"$ROOT/scripts/install.sh" >/dev/null

export AGENT_ASSETS_LIB_DIR="$TMP_HOME/.local/lib/agent-assets"

AGENT_ASSETS_USER_HOME="$TMP_HOME" "$TMP_HOME/.local/bin/agent-assets-list" >/dev/null
AGENT_ASSETS_USER_HOME="$TMP_HOME" AGENT_ASSETS_SCAN_DIRS="$TMP_HOME/.local/bin" "$TMP_HOME/.local/bin/agent-assets-discover" >/dev/null
AGENT_ASSETS_USER_HOME="$TMP_HOME" "$TMP_HOME/.local/bin/agent-assets-projects" >/dev/null
python3 -m json.tool "$TMP_HOME/.config/agent-assets/projects.json" >/dev/null
AGENT_ASSETS_USER_HOME="$TMP_HOME" AGENT_ASSETS_SCAN_DIRS="$TMP_HOME/.local/bin" "$TMP_HOME/.local/bin/agent-assets-dashboard" >/dev/null

PYTHONPATH="$ROOT/lib" python3 -m unittest discover -s "$ROOT/tests" -p 'test_*.py'

echo "smoke-ok"
