# Agent Start Here

You are working on this user's machine. Read this file before touching local CLIs, MCP servers, agent apps, skills, downloaded tools, or project assets.

## User-Facing Shortcut

The user should only need to say:

> Read `__HOME__/AGENT_START_HERE.md` first and follow the local agent-assets rules.

If you are an agent, this is enough context. Do not ask the user to manually explain where every local tool is installed.

## Fixed Entrypoints

- Start file: `__HOME__/AGENT_START_HERE.md`
- Agent contract: `__ASSETS_HOME__/AGENT_CONTRACT.md`
- Asset registry: `__ASSETS_HOME__/registry.json`
- Project index: `__ASSETS_HOME__/projects.json`
- Discovery output: `__ASSETS_HOME__/discovered.json`
- Discovery review: `__ASSETS_HOME__/discovery-review.json`
- Human guide: `__ASSETS_HOME__/README.md`
- Static dashboard: `__ASSETS_HOME__/dashboard.html`
- Live dashboard command: `agent-assets-dashboard --serve --open`
- MCP registry: `__MCP_HOME__/registry.json`
- Stable command directory: `__BIN_DIR__`
- stdio MCP wrappers: `__BIN_DIR__/*-mcp`
- Durable projects/downloads/clones: `__PROJECTS_DIR__`

## Required Behavior

1. Use the tool directly when it is already available or you know the stable entrypoint in `__BIN_DIR__`.
2. If the command is missing, PATH-dependent, ambiguous, or appears to be installed but not callable, read the registry or run `agent-assets-list` before saying it is unavailable.
3. If the registry does not contain the tool, run `agent-assets-discover` before asking the user to identify paths manually.
4. Read `__MCP_HOME__/registry.json` before changing MCP host configs.
5. For GBrain memory, prefer the configured GBrain MCP tool/server. Do not use `gbrain search` as an automatic fallback; the CLI may be degraded even when the HTTP MCP is healthy.
6. Register new agent-facing CLIs, MCPs, agent apps, skill packs, and downloaded tools during setup.
7. If a new asset is an MCP server, update the MCP registry too.
8. When looking for old GitHub clones, downloaded repos, source packages, or scattered project folders, inspect `__ASSETS_HOME__/projects.json` or run `agent-assets-projects`.
9. New durable clones, downloaded repos, and project outputs still belong under `__PROJECTS_DIR__`.
10. If the user wants a visual inventory, start `agent-assets-dashboard --serve --open`.
11. Never write tokens, API keys, Authorization headers, cookies, passwords, or private keys into registries.
