#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_DIR="${AGENT_ASSETS_USER_HOME:-$HOME}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME_DIR/.config}"
ASSETS_HOME="${AGENT_ASSETS_HOME:-$CONFIG_HOME/agent-assets}"
MCP_HOME="${AGENT_ASSETS_MCP_HOME:-$CONFIG_HOME/mcp}"
BIN_DIR="${AGENT_ASSETS_BIN_DIR:-$HOME_DIR/.local/bin}"
PROJECTS_DIR="${AGENT_ASSETS_PROJECTS_DIR:-$HOME_DIR/projects}"

mkdir -p "$BIN_DIR" "$ASSETS_HOME" "$MCP_HOME" "$PROJECTS_DIR"

install -m 0755 "$ROOT/bin/agent-assets-dashboard" "$BIN_DIR/agent-assets-dashboard"
install -m 0755 "$ROOT/bin/agent-assets-discover" "$BIN_DIR/agent-assets-discover"
install -m 0755 "$ROOT/bin/agent-assets-register" "$BIN_DIR/agent-assets-register"
install -m 0755 "$ROOT/bin/agent-assets-list" "$BIN_DIR/agent-assets-list"
install -m 0755 "$ROOT/bin/agent-assets-contract" "$BIN_DIR/agent-assets-contract"

render_template() {
  local src="$1"
  local dst="$2"
  if [ -e "$dst" ]; then
    printf 'exists %s\n' "$dst"
    return
  fi
  sed \
    -e "s#__HOME__#$HOME_DIR#g" \
    -e "s#__ASSETS_HOME__#$ASSETS_HOME#g" \
    -e "s#__MCP_HOME__#$MCP_HOME#g" \
    -e "s#__BIN_DIR__#$BIN_DIR#g" \
    -e "s#__PROJECTS_DIR__#$PROJECTS_DIR#g" \
    "$src" > "$dst"
  printf 'created %s\n' "$dst"
}

render_template "$ROOT/templates/AGENT_START_HERE.md" "$HOME_DIR/AGENT_START_HERE.md"
render_template "$ROOT/templates/agent-assets/AGENT_CONTRACT.md" "$ASSETS_HOME/AGENT_CONTRACT.md"
render_template "$ROOT/templates/agent-assets/README.md" "$ASSETS_HOME/README.md"
render_template "$ROOT/templates/agent-assets/registry.example.json" "$ASSETS_HOME/registry.json"
render_template "$ROOT/templates/agent-assets/discovery-review.example.json" "$ASSETS_HOME/discovery-review.json"
render_template "$ROOT/templates/mcp/registry.example.json" "$MCP_HOME/registry.json"

printf '\nInstalled Agent Assets Control Plane.\n'
printf 'Start file: %s/AGENT_START_HERE.md\n' "$HOME_DIR"
printf 'Dashboard: %s/agent-assets-dashboard --serve --open\n' "$BIN_DIR"

