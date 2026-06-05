# Architecture

Agent Assets Control Plane has two coupled surfaces.

## 1. Agent contract

These files are read by AI agents:

- `~/AGENT_START_HERE.md`
- `~/.config/agent-assets/AGENT_CONTRACT.md`
- `~/.config/agent-assets/registry.json`
- `~/.config/mcp/registry.json`

The goal is to stop agents from searching random dotdirs first or repeatedly asking the user where tools are installed.

## 2. Human dashboard

The dashboard renders the same registries for humans:

- registered assets
- MCP servers and health
- stable entrypoints
- discovered executable candidates
- skill roots and symlink/alias counts
- config files

The live dashboard exposes a local-only `POST /api/scan` endpoint that reruns discovery and refreshes MCP health.

## Data Flow

```text
package managers / apps / project clones
        |
        v
agent-assets-discover
        |
        v
discovered.json + discovery-review.json
        |
        v
registry.json + mcp/registry.json
        |
        v
agent-assets-dashboard
```

## Review States

Discovered items are not automatically trusted.

- `new`: needs a human or agent decision
- `defer`: plausible asset, not registered yet
- `ignore`: known noise
- `registered`: covered by the formal registry

