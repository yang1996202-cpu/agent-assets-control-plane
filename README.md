# Agent Assets Control Plane

**本机运行态观测台**（2026-06 定位演进）。

A local control plane for AI-agent-facing tools.

> **定位演进**：最初是"AI Agent 资产控制面"——登记所有资产让 Agent 知道装了啥。
> 实测预登记必然失败（工具流动快、手动维护零容错、registry 长期和实际脱节）：Agent 自己能查本机装了啥（多问一句即可），预登记是反向添乱。
> 所以核心收缩为**观测运行态盲区**——什么在后台跑、有没有泄漏、有没有僵尸 dev server、哪些常驻、占哪些端口。
> 这不需要维护纪律，跑一次扫一次。详见 `docs/architecture.md` 的 Runtime Observation。

四个观测入口：

- `agent-assets-dashboard` — 仪表盘 `http://127.0.0.1:17654`（MCP audit / 系统信号 / 发现候选 / runtime 盲区）
- `asset-runtime` — 进程盲区扫描：泄漏（如 context7-mcp 被多 host 各拉一份）、僵尸 dev server、常驻 daemon、端口占用
- `asset-macos-signals` — launchd 全景 + 开机自启 + 端口监听
- `agent-assets-discover` — 磁盘上的 CLI / 工具入口清点

> **退役**：`registry.json` 静态索引 + `agent-assets-register` 不再强制喂，当历史快照。
> **保留**：Agent contract（路径指引）——Agent 查"X 装哪了"仍有用，按需查，不是预登记。

Two linked surfaces, one source of truth:

- **Agent contract** — plain files that tell any new agent where local CLIs, MCP servers, skills, projects, and registries live.
- **Human dashboard** — a browser UI that scans and visualizes the same assets so you can see what is installed, registered, or needs review.

This project does **not** move package-manager internals into one directory. npm, uv, pip, Homebrew, and apps keep their own storage. It standardizes the control plane:

- stable wrappers in `~/.local/bin`
- registry files in `~/.config/agent-assets`
- historical project index in `~/.config/agent-assets/projects.json`
- MCP registry in `~/.config/mcp`
- durable projects under `~/projects`
- local dashboard at `http://127.0.0.1:17654/`

## Why

Agent stacks become unmanageable fast: tools scatter across package managers, MCP servers hide in host configs, and every new agent asks "where is X?"

The fix is not "one folder for everything." It is a stable local contract plus a visible inventory.

**但更深的盲区是运行态**：装得多、跑得多，后台一堆看不见的东西——MCP 被多个 host 各拉一份（泄漏）、开发预览服务器忘关（僵尸）、各种 daemon 常驻、端口被占。这些登记簿看不到（它们没绑 plist、不在 registry），只有按需扫描运行态才照得出来。观测台就是干这个的。

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

# --- 运行态观测（核心，按需跑、只读）---
# 进程盲区：泄漏 / 僵尸 dev server / 常驻 daemon / 端口占用
asset-runtime
asset-runtime --json          # 结构化输出（dashboard 消费）

# launchd 全景 + 开机自启 + 端口监听
asset-macos-signals

# --- 静态清点（保留能力，不再强制登记）---
# Scan from CLI
agent-assets-discover

# Index downloaded / cloned / legacy project folders without moving files
agent-assets-projects

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

Early v0. 运行态观测台（核心）：`asset-runtime`（进程盲区）、`asset-macos-signals`（launchd / 开机自启）、`agent-assets-dashboard`（仪表盘）。保留能力：file-based registry、local scanner、project index、dashboard review、one-click cross-check。registry 登记退役为可选。Planned：schema validation、packaged install、runtime 视图深化（进程树反查 / CPU 内存排序）。
