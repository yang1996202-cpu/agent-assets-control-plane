# Local Agent Contract

If you are an AI agent running on this machine, follow this contract before you touch local CLIs, MCP servers, agent apps, skills, downloaded tools, or project assets.

## Source Of Truth

- Start file: `__HOME__/AGENT_START_HERE.md`
- Human guide: `__ASSETS_HOME__/README.md`
- Machine registry: `__ASSETS_HOME__/registry.json`
- Project index: `__ASSETS_HOME__/projects.json`
- macOS system trace index: `__ASSETS_HOME__/macos-signals.json`
- macOS system trace review: `__ASSETS_HOME__/macos-signals-review.json`
- Auto-discovery output: `__ASSETS_HOME__/discovered.json`
- Discovery review: `__ASSETS_HOME__/discovery-review.json`
- Static dashboard: `__ASSETS_HOME__/dashboard.html`
- Live dashboard command: `agent-assets-dashboard --serve --open`
- MCP registry: `__MCP_HOME__/registry.json`
- Stable command directory: `__BIN_DIR__`
- Durable project/download directory: `__PROJECTS_DIR__`

## Required Behavior

1. Before searching random dotdirs, run `agent-assets-list` or read `__ASSETS_HOME__/registry.json`.
2. If the registry does not contain the tool, run `agent-assets-discover` and inspect `__ASSETS_HOME__/discovered.json`.
3. Treat `__BIN_DIR__` as the stable command surface for agent-facing tools.
4. Treat `__BIN_DIR__/*-mcp` as the stable stdio MCP surface.
5. Keep package-manager internals where they are.
6. Put durable clones, downloaded repos, and project outputs under `__PROJECTS_DIR__`.
7. Register new agent-facing tools immediately with `agent-assets-register`.
8. If the new thing is an MCP server, also update `__MCP_HOME__/registry.json`.
9. When looking for old GitHub clones, downloaded repos, source packages, or scattered project folders, inspect `__ASSETS_HOME__/projects.json` or run `agent-assets-projects`.
10. When checking macOS login items, background items, launchd jobs, privileged helpers, running services, or local listening ports, inspect `__ASSETS_HOME__/macos-signals.json` or run `agent-assets-macos-signals`.
11. If the user wants a visual inventory, start `agent-assets-dashboard --serve --open`.
12. Never store secrets in registries.

## Minimal Snippet For New Agents

Read `__HOME__/AGENT_START_HERE.md` first, then follow `__ASSETS_HOME__/AGENT_CONTRACT.md` before using or installing local CLI/MCP/Agent assets.
