# Agent Assets Control Plane Handoff

更新时间：2026-06-06

这份文档给新窗口、新 Agent 或未来的自己接着维护本项目用。先读这里，再读仓库 README 和本机资产入口文件。

## 一句话目标

这个项目不是单纯做 CLI 列表，而是给本机 Agent 资产做一个可解释的控制面板：把 CLI、MCP、Agent App、skill、配置文件、稳定入口和待确认资产放到一个地方，让用户不用到处翻 dotdir、包管理器目录和项目目录。

## 新窗口先读什么

1. `/Users/yang/AGENT_START_HERE.md`
2. `/Users/yang/.config/agent-assets/AGENT_CONTRACT.md`
3. `/Users/yang/projects/agent-assets-control-plane/docs/HANDOFF.md`
4. `/Users/yang/projects/agent-assets-control-plane/README.md`
5. `/Users/yang/projects/agent-assets-control-plane/docs/architecture.md`

## 当前仓库和服务

- 项目仓库：`/Users/yang/projects/agent-assets-control-plane`
- GitHub remote：`https://github.com/yang1996202-cpu/agent-assets-control-plane.git`
- live 面板：`http://127.0.0.1:17654/`
- LaunchAgent：`/Users/yang/Library/LaunchAgents/com.yang.agent-assets-dashboard.plist`
- 本机实际脚本：
  - `/Users/yang/.local/bin/asset-dashboard`
  - `/Users/yang/.local/bin/asset-discover`
  - `/Users/yang/.local/bin/asset-list`
  - `/Users/yang/.local/bin/asset-register`
  - `/Users/yang/.local/bin/agent-contract`
- 开源仓库脚本：
  - `/Users/yang/projects/agent-assets-control-plane/bin/agent-assets-dashboard`
  - `/Users/yang/projects/agent-assets-control-plane/bin/agent-assets-discover`
  - `/Users/yang/projects/agent-assets-control-plane/bin/agent-assets-list`
  - `/Users/yang/projects/agent-assets-control-plane/bin/agent-assets-register`

注意：本机脚本是 `/Users/yang` 定制版；仓库脚本是环境变量泛化版。改功能时通常要两边同步，但不要把本机硬编码直接拷进仓库版。

## 本机核心数据文件

- Agent 资产总账：`/Users/yang/.config/agent-assets/registry.json`
- Agent 资产说明：`/Users/yang/.config/agent-assets/README.md`
- Agent 接入合约：`/Users/yang/.config/agent-assets/AGENT_CONTRACT.md`
- 发现结果：`/Users/yang/.config/agent-assets/discovered.json`
- 发现 review 状态：`/Users/yang/.config/agent-assets/discovery-review.json`
- 生成的静态面板：`/Users/yang/.config/agent-assets/dashboard.html`
- MCP 总账：`/Users/yang/.config/mcp/registry.json`
- MCP 说明：`/Users/yang/.config/mcp/README.md`

## 当前已完成

### 1. 资产总账和稳定入口

已建立中央资产总账和 MCP 总账。Agent 查本机工具前，应先读总账或运行：

```bash
/Users/yang/.local/bin/asset-list
```

新装 Agent 相关资产时，应登记：

```bash
/Users/yang/.local/bin/asset-register --id <name> ...
```

原则：包管理器内部目录不要硬搬。重要工具统一做 wrapper 或 symlink 到 `/Users/yang/.local/bin`。

### 2. live 面板

面板在 `http://127.0.0.1:17654/`，由 launchd 保持运行。

面板菜单：

- `总览`：整体状态、MCP、入口、待确认、技能数量。
- `资产`：已登记资产。
- `MCP`：MCP 服务、入口、健康状态、宿主引用。
- `入口`：Agent 应调用的稳定 wrapper / command。
- `发现`：日常扫描或深度盘点结果。
- `技能`：skill 根目录和数量口径。
- `配置`：规则、总账、宿主配置位置。

### 3. 日常扫描和深度盘点

现在有两个扫描模式：

- `刷新日常扫描`：低噪声，只扫可信入口目录。
- `运行深度盘点`：审计模式，多扫常见 App / Agent 目录。

命令：

```bash
/Users/yang/.local/bin/asset-discover --mode daily
/Users/yang/.local/bin/asset-discover --mode deep
```

API：

```bash
curl -X POST 'http://127.0.0.1:17654/api/scan?mode=daily'
curl -X POST 'http://127.0.0.1:17654/api/scan?mode=deep'
```

当前 live 面板停留在 `deep` 结果，因为最后一次验证跑了深度盘点。点 `刷新日常扫描` 会回到低噪声日常视图。

### 4. `gh` 和 PATH 问题

`gh` 已处理：

- Homebrew 原路径：`/opt/homebrew/bin/gh`
- 稳定入口：`/Users/yang/.local/bin/gh`
- 登记资产：`github-cli`

根因：Codex App 进程 PATH 没有 `/opt/homebrew/bin`，所以不能假设 App 启动的 Agent 能找到 Homebrew CLI。以后遇到类似问题，优先做稳定 wrapper，不要单纯扩大 PATH。

### 5. `gbrain` wrapper

`gbrain` 原入口 `/Users/yang/.bun/bin/gbrain` 使用 `#!/usr/bin/env bun`。App 启动的 Agent PATH 找不到 Bun 时会失败。

已新增稳定入口：

```bash
/Users/yang/.local/bin/gbrain
```

它会先补 `/Users/yang/.bun/bin`，再执行真实 gbrain。

注意：这只解决 CLI PATH 问题。`gbrain` MCP 仍有 PGLite WASM 初始化失败问题，属于另一个运行时问题。

### 6. skill 数量口径已修正

旧面板显示 1300+ 个 skill，口径错了。原因是递归扫描把 gstack 内部多宿主副本、嵌套 skill、symlink 都算进了真实技能数。

现在主数字改成顶层技能数：

- 顶层技能数：`365`
- 顶层路径：`370`
- 递归发现：`1408`
- 递归去重：`1300`
- 嵌套/递归项：`1038`

面板上 `365` 是主指标；`1408` 只作为诊断指标。

## 当前状态快照

最后一次验证时，`/api/status` 返回：

```json
{
  "assets": 36,
  "mcp_total": 9,
  "mcp_connected": 5,
  "entrypoints": 66,
  "valid_entrypoints": 66,
  "candidates": 110,
  "unregistered": 17,
  "needs_review": 11,
  "deferred": 0,
  "ignored": 6,
  "skills_unique": 365,
  "skills_paths": 370,
  "skills_recursive_paths": 1408,
  "skills_recursive_unique": 1300,
  "skills_aliases": 108,
  "skills_nested": 1038,
  "scan_mode": "deep"
}
```

深度盘点当前待确认项：

- `/Applications/AutoClaw.app`
- `/Users/yang/Applications/Claude Code URL Handler.app`
- `/Applications/Claude.app`
- `/Applications/Codex Proxy.app`
- `/Applications/CodexBar.app`
- `/Applications/Cursor.app`
- `/Applications/Lark.app`
- `/Applications/OpenClaw.app`
- `/Applications/OpenCode.app`
- `/Applications/QClaw.app`
- `/Applications/WorkBuddy.app`

这些不是错误，而是深度盘点发现的候选 App。下一步应让用户决定哪些登记、哪些忽略。

## 已知问题和注意事项

### 1. 不要把全盘扫描当日常扫描

日常扫描应低噪声，只扫可信入口目录。深度盘点才用于审计。不要把 `/`、整个 `/Users/yang` 或所有项目目录直接加入日常扫描。

正确产品逻辑：

- 日常扫描：快、低噪声、稳定。
- 深度盘点：更宽、更慢、有待确认项。
- 登记晋升：用户确认后，把重要资产登记进总账，并做稳定入口。

### 2. 不要乱翻或移动包管理器目录

不要搬：

- Bun global package storage
- npm global package storage
- pip site-packages
- Homebrew Cellar
- Docker internals

只给 Agent 需要调用的东西做 `/Users/yang/.local/bin` wrapper 或 symlink。

### 3. 不要覆盖用户未提交改动

仓库当前还有用户自己的未提交内容：

- `docs/wechat-post.md`
- `illustrations/`

后续提交时只 `git add` 自己改的文件，不要顺手提交或改动这些内容，除非用户明确要求。

### 4. MCP 健康不是全绿

最后一次健康状态：

- connected：`alice`、`notebooklm-mcp`、`wechat`、`context7`、`exa`
- failed：`MCP_DOCKER`、`gbrain`

`gbrain` MCP 失败不是因为 wrapper 缺失，而是 PGLite WASM 初始化问题。

## 建议下一步

### P0：给深度盘点候选做确认动作

面板现在能发现待确认项，但还不能在 UI 里点“登记 / 忽略 / 稍后处理”。下一步应做：

- 每个候选项显示建议动作。
- 加 `登记`、`忽略`、`稍后处理` 按钮。
- 写入 `/Users/yang/.config/agent-assets/discovery-review.json` 或调用 `asset-register`。

### P1：把 App 资产分类做得更准

深度盘点抓到了 Claude、Cursor、OpenClaw、WorkBuddy 等 App。下一步应给这些 App 更清晰的分类：

- Agent App
- MCP host
- CLI host
- Desktop helper
- 不相关 App

### P2：README / docs 同步

目前功能比 README 更先进。需要更新：

- `/Users/yang/projects/agent-assets-control-plane/README.md`
- `/Users/yang/projects/agent-assets-control-plane/docs/architecture.md`
- `/Users/yang/projects/agent-assets-control-plane/docs/open-source-boundary.md`

重点写清楚日常扫描 vs 深度盘点、skill 统计口径、wrapper 策略。

### P3：做安装后的初始化体验

开源用户安装后应该能跑：

```bash
scripts/install.sh
agent-assets-dashboard --serve --port 17654
```

并看到自己的 registry 模板、扫描结果和待确认项。

## 常用验证命令

```bash
python3 -m py_compile \
  /Users/yang/.local/bin/asset-dashboard \
  /Users/yang/.local/bin/asset-discover \
  /Users/yang/projects/agent-assets-control-plane/bin/agent-assets-dashboard \
  /Users/yang/projects/agent-assets-control-plane/bin/agent-assets-discover

/Users/yang/projects/agent-assets-control-plane/tests/smoke.sh

curl -sS http://127.0.0.1:17654/api/status | python3 -m json.tool

/Users/yang/.local/bin/asset-discover --mode daily
/Users/yang/.local/bin/asset-discover --mode deep

launchctl print gui/$(id -u)/com.yang.agent-assets-dashboard
```

## 最近提交

- `f6c0f54 Add deep audit scan and fix skill counts`
- `1f21d1f Clarify dashboard tab context`
- `6af2955 Localize dashboard and detect GitHub CLI`

## 交接给新 Agent 的一句话

先读 `/Users/yang/AGENT_START_HERE.md` 和 `/Users/yang/projects/agent-assets-control-plane/docs/HANDOFF.md`。本项目的核心不是“扫描越多路径越好”，而是把散落的 CLI、MCP、Agent App、skill 和配置变成低噪声、可确认、可登记、可调用的本机 Agent 资产账本。
