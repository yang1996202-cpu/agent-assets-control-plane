# Agent Assets Control Plane

[![CI](https://github.com/yang1996202-cpu/agent-assets-control-plane/actions/workflows/ci.yml/badge.svg)](https://github.com/yang1996202-cpu/agent-assets-control-plane/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](pyproject.toml)

> **Local runtime observatory for AI-agent-facing tools on macOS.**

This project answers one question: **what is running on this machine right now?**

Agent stacks scatter tools across package managers, MCP servers hide in host configs, dev servers get forgotten, and launchd services silently auto-start. Pre-registering every tool in a static registry does not scale. Instead, Agent Assets Control Plane scans the local runtime on demand and shows you:

- running processes (apps, agents, MCP servers, dev servers, system daemons)
- memory and CPU usage per process
- listening ports and who owns them
- macOS launchd services, login items, and startup items
- discovered CLI entrypoints and project roots

It is read-first, opinionated-second: it does not move files or install software unless you explicitly ask.

## Platform

**macOS only.** The dashboard relies on `launchctl`, `lsof`, and macOS-specific plist paths. Linux/Windows support would require separate collectors.

## Install

```bash
git clone https://github.com/yang1996202-cpu/agent-assets-control-plane.git
cd agent-assets-control-plane
./scripts/install.sh
```

`install.sh` copies CLI wrappers to `~/.local/bin`, library modules to `~/.local/lib/agent-assets`, and config files to `~/.config/agent-assets`. Make sure `~/.local/bin` is on your `PATH`.

## Usage

```bash
# Launch the live dashboard and open it in your browser
agent-assets-dashboard --serve --open

# Or generate a static HTML snapshot
agent-assets-dashboard

# Runtime scan from the terminal
asset-runtime
asset-runtime --json

# macOS launchd / startup / login item scan
asset-macos-signals
```

The live dashboard runs on `http://127.0.0.1:17654` and binds to localhost only.

## What each tool does

| Tool | Purpose |
|---|---|
| `agent-assets-dashboard` | Browser UI: runtime, system signals, CLI tools, action log |
| `asset-runtime` | Process scan: leaks, zombie dev servers, daemons, ports, CPU/memory |
| `asset-macos-signals` | launchd plists, BTM, login items, system extensions, port listeners |
| `agent-assets-discover` | Disk scan for CLI / MCP / agent entrypoints |
| `agent-assets-projects` | Index `~/projects` and other project roots without moving files |
| `agent-assets-list` | Print registry contents |
| `agent-assets-register` | Manually register a tool (optional, registry is no longer required) |

## Configuration

After installation, config files live in `~/.config/agent-assets`:

| File | Purpose |
|---|---|
| `registry.json` | Static asset registry (optional) |
| `product-map.json` | Friendly names for system-signal vendors (e.g. map `oray` to `向日葵`) |
| `discovery-review.json` | Review decisions for discovered candidates |
| `action-log.json` | Dashboard kill / launchctl action history |

Edit `product-map.json` to add your own vendor-to-name mappings. A full example ships at `templates/agent-assets/product-map.example.json`.

Edit `runtime-classification.json` to teach `asset-runtime` about your own MCP servers, agent daemons, and support tools. A full example ships at `templates/agent-assets/runtime-classification.example.json`.

## Screenshots

> Screenshots will be added here before the first stable release. Run `agent-assets-dashboard --serve --open` to see the live UI.

## Development

```bash
python3 -m unittest discover -s tests -v
```

All code is pure Python standard library; no `pip install` is required.

## Security

- The dashboard binds to `127.0.0.1` only. Do not expose it on a public interface.
- `kill-process` and `launchctl` actions are gated by whitelists and path checks.
- Never store secrets in registry or config files; record only where your host stores them.

## License

MIT. See [LICENSE](LICENSE).
