# Agent Assets Control Plane

A local control plane for AI-agent-facing tools.

Two linked surfaces, one source of truth:

- **Agent contract** — plain files that tell any new agent where local CLIs, MCP servers, skills, projects, and registries live.
- **Human dashboard** — a browser UI that scans and visualizes the same assets so you can see what is installed, registered, or needs review.

This project does **not** move package-manager internals into one directory. npm, uv, pip, Homebrew, and apps keep their own storage. It standardizes the control plane:

- stable wrappers in `~/.local/bin`
- registry files in `~/.config/agent-assets`
- historical project index in `~/.config/agent-assets/projects.json`
- macOS login/background/service trace index in `~/.config/agent-assets/macos-signals.json`
- macOS trace review decisions in `~/.config/agent-assets/macos-signals-review.json`
- MCP registry in `~/.config/mcp`
- durable projects under `~/projects`
- local dashboard at `http://127.0.0.1:17654/`

## Why

Agent stacks become unmanageable fast: tools scatter across package managers, MCP servers hide in host configs, and every new agent asks "where is X?"

The fix is not "one folder for everything." It is a stable local contract plus a visible inventory.

## Install

```bash
git clone https://github.com/yang1996202-cpu/agent-assets-control-plane.git ~/projects/agent-assets-control-plane
cd ~/projects/agent-assets-control-plane
./scripts/install.sh
```

Creates `~/AGENT_START_HERE.md`, registry files, and CLI wrappers.

## Run

```bash
# Static dashboard
agent-assets-dashboard

# Live dashboard with one-click scan
agent-assets-dashboard --serve --open

# Scan from CLI
agent-assets-discover

# Index downloaded / cloned / legacy project folders without moving files
agent-assets-projects

# Index macOS login/background/launchd/process traces without changing them
agent-assets-macos-signals

# List registered assets
agent-assets-list
agent-assets-list mcp

# Register a tool
agent-assets-register \
  --id example-tool \
  --category cli \
  --entrypoint ~/.local/bin/example-tool \
  --source ~/projects/example-tool \
  --note "What this tool does"
```

## Tell A New Agent

> Read `~/AGENT_START_HERE.md` first, then follow the local agent-assets rules.

The agent inspects the registry and discovery output before asking you where a tool lives.

## Security

Never put secrets into registries. Record only where the host stores them.

The dashboard is for localhost only. Do not expose it on a public interface.

## Status

Early v0. File-based registry, local scanner, local dashboard, project index, macOS trace index, dashboard review actions, and one-click cross-check. Planned: schema validation and packaged install.
