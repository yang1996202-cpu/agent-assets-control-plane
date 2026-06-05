# Agent Assets Control Plane

A local control plane for AI-agent-facing tools.

It has two linked surfaces:

- **Agent contract**: plain files that tell any new agent where local CLIs, MCP servers, skills, projects, wrappers, and registries live.
- **Human dashboard**: a browser UI that scans and visualizes local agent assets so the user can see what is installed, what is registered, and what needs review.

The project does **not** move package-manager internals into one directory. npm, Bun, uv, pip, Homebrew, Docker, and apps keep their own storage. This project standardizes the control plane:

- stable wrappers in `~/.local/bin`
- registry files in `~/.config/agent-assets`
- MCP registry in `~/.config/mcp`
- durable project clones under `~/projects`
- a local dashboard at `http://127.0.0.1:17654/`

## Why

Modern agent stacks become unmanageable quickly:

- CLI tools land in different package-manager folders.
- MCP servers are split across host configs, wrappers, HTTP URLs, and app settings.
- Skill roots can contain symlinks and duplicates.
- New agents repeatedly ask the user where things are.

The fix is not "put every file in one folder." The fix is a stable local contract plus a visible inventory.

## Install

This repo is dependency-light: Python 3 plus standard library.

```bash
git clone <this-repo-url> ~/projects/agent-assets-control-plane
cd ~/projects/agent-assets-control-plane
./scripts/install.sh
```

The installer creates:

- `~/.local/bin/agent-assets-dashboard`
- `~/.local/bin/agent-assets-discover`
- `~/.local/bin/agent-assets-register`
- `~/.local/bin/agent-assets-list`
- `~/.local/bin/agent-assets-contract`
- `~/AGENT_START_HERE.md`
- `~/.config/agent-assets/AGENT_CONTRACT.md`
- `~/.config/agent-assets/README.md`
- `~/.config/agent-assets/registry.json`
- `~/.config/agent-assets/discovery-review.json`
- `~/.config/mcp/registry.json`

## Run

Generate a static dashboard:

```bash
agent-assets-dashboard
```

Run a live dashboard with a one-click scan button:

```bash
agent-assets-dashboard --serve --open
```

Default URL:

```text
http://127.0.0.1:17654/
```

Scan from CLI:

```bash
agent-assets-discover
```

List registered assets:

```bash
agent-assets-list
agent-assets-list mcp
agent-assets-list --json
```

Register a tool:

```bash
agent-assets-register \
  --id example-tool \
  --category cli \
  --entrypoint ~/.local/bin/example-tool \
  --source ~/projects/example-tool \
  --note "What this tool does"
```

## Tell A New Agent

Give any new agent this instruction:

```text
Read ~/AGENT_START_HERE.md first, then follow the local agent-assets rules.
```

The agent should inspect the registry and discovery output before asking the user where a local tool lives.

## Configuration

Defaults are based on the current user:

- `AGENT_ASSETS_HOME`: defaults to `~/.config/agent-assets`
- `AGENT_ASSETS_MCP_HOME`: defaults to `~/.config/mcp`
- `AGENT_ASSETS_BIN_DIR`: defaults to `~/.local/bin`
- `AGENT_ASSETS_PROJECTS_DIR`: defaults to `~/projects`
- `AGENT_ASSETS_PORT`: defaults to `17654`
- `AGENT_ASSETS_SCAN_DIRS`: optional path-list override for discovery

## Security

Never put secrets into registries.

Do not store:

- API keys
- bearer tokens
- Authorization headers
- cookies
- passwords
- private keys

Record only where the host stores secrets, not the secret values.

The dashboard is intended for localhost use. Do not expose it on a public interface.

## Project Status

This is an early v0 extracted from a working local setup. The first public shape is intentionally small:

- file-based registry
- local scanner
- local dashboard
- simple review states: `new`, `defer`, `ignore`, `registered`

Planned next steps:

- dashboard buttons for register/ignore/defer
- stronger schema validation
- launchd/systemd helper generation
- packaged install command

