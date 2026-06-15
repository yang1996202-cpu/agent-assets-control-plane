# Agent Assets Registry

This directory is the local control plane for agent-facing assets.

## View

```bash
agent-assets-dashboard --serve --open
agent-assets-discover
agent-assets-projects
agent-assets-macos-signals
agent-assets-list
agent-assets-list --json
agent-assets-contract --snippet
```

Live dashboard:

- `http://127.0.0.1:17654/`

## Rules

- Keep package-manager internals where their ecosystems put them.
- Use `__BIN_DIR__` for stable agent-callable wrappers.
- Use `__BIN_DIR__/*-mcp` for stable stdio MCP wrappers.
- Put durable clones/downloads/projects under `__PROJECTS_DIR__`.
- Use `__ASSETS_HOME__/projects.json` to review old downloaded, cloned, or scattered project folders before moving anything.
- Use `__ASSETS_HOME__/macos-signals.json` to review macOS login/background/launchd/service traces before changing anything.
- Use `__ASSETS_HOME__/macos-signals-review.json` to keep dashboard decisions for those system traces.
- Do not put secrets into registries.

## Register A New Asset

```bash
agent-assets-register \
  --id example-tool \
  --category cli \
  --entrypoint __BIN_DIR__/example-tool \
  --source __PROJECTS_DIR__/example-tool \
  --note "What this tool does"
```

If it is an MCP server, also update `__MCP_HOME__/registry.json`.
