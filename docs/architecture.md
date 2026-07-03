# Architecture

> **定位（2026-06 演进）**：本项目核心是**本机运行态观测台**，不是资产登记簿。
> 登记失败的根本原因：工具流动快、手动维护零容错，registry 长期和实际脱节。
> Agent 自己能查本机装了啥（多问一句即可），预登记是反向添乱；但运行态盲区
> （后台进程泄漏、僵尸 dev server、常驻 daemon、端口占用）Agent 和人都看不清——这才是要观测的。
> 下面的 contract + dashboard 登记链作为"保留能力"留存；运行态观测（signals / runtime）是独立旁路，不进 registry。

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

## Runtime Observation（旁路，不进 registry）

运行态观测不走登记链，是独立旁路，按需跑、只读快照，直接喂 dashboard：

```text
ps / lsof / launchd / BTM
        |
        +-- asset-runtime        → 进程盲区：泄漏 / 僵尸 dev server / 常驻 daemon / 端口
        +-- asset-macos-signals  → launchd 全景 + 开机自启 + 端口监听
                |
                v
        agent-assets-dashboard   （系统信号 tab + runtime tab）
```

registry.json 在这条链里**不被写入**。观测不靠维护纪律：跑一次扫一次，过时就重扫。

四个观测入口：`agent-assets-dashboard`（仪表盘 127.0.0.1:17654）/ `asset-runtime`（进程盲区）/ `asset-macos-signals`（开机自启）/ `agent-assets-discover`（磁盘工具入口清点）。

## Review States

Discovered items are not automatically trusted.

- `new`: needs a human or agent decision
- `defer`: plausible asset, not registered yet
- `ignore`: known noise
- `registered`: covered by the formal registry

