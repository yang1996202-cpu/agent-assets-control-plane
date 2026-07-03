# Agent Assets Control Plane — 维护交接

更新时间：2026-06-26

给新窗口、新 Agent 或未来的自己接着维护本项目用。先读 `README.md` 和 `docs/architecture.md`，本文件补「怎么维护」。

## 定位（一句话）

**本机运行态观测台**，不是资产登记簿。核心是把运行态盲区（后台泄漏 / 僵尸 dev server / 常驻 daemon / 端口占用）照出来。registry 已退役为历史快照，不再强制登记。详见 README 的 Why 段和 architecture 的 Runtime Observation 段。

## 仓库地图

### `bin/`（可执行，install.sh 装到 `~/.local/bin`）

| 脚本 | 安装名 | 职责 |
|---|---|---|
| `agent-assets-dashboard` | `agent-assets-dashboard` | 仪表盘：serve + 静态 HTML，MCP audit / 系统信号 / runtime / launchctl 开关 |
| `agent-assets-runtime` | `asset-runtime`（短名） | 进程盲区扫描：泄漏 / 僵尸 / 常驻 / 端口，`--json` |
| `agent-assets-macos-signals` | `asset-macos-signals`（短名） | launchd 全景 + 开机自启 + 端口监听 + 登录项，写 `macos-signals.json` |
| `agent-assets-discover` | `agent-assets-discover` | 入口目录扫描（daily / deep），写 `discovered.json` |
| `agent-assets-projects` | `agent-assets-projects` | 索引 `~/projects`，写 `projects.json` |
| `agent-assets-register` | `agent-assets-register` | 写 registry（带 secret 自动拒绝） |
| `agent-assets-list` | `agent-assets-list` | 打印 registry（表格 / `--json`） |
| `agent-assets-contract` | `agent-assets-contract` | 打印 AGENT_CONTRACT 内容 |

**命名约定**：默认长名 `agent-assets-*`；`asset-runtime` 和 `asset-macos-signals` 用短名（运行态观测旁路系列，与 dashboard 的 runtime / 系统信号 tab 对应）。dashboard 代码对短名有 legacy 回退。改功能时只需改 `bin/` 源文件，`install.sh` 重装即生效；本机若额外做了指向 `~/.local/bin/agent-assets-*` 的短名 wrapper，会自动跟进。

### 其他

- `scripts/install.sh` — 装命令 + 渲染 `templates/` 到 `~/AGENT_START_HERE.md`、`~/.config/agent-assets/`、`~/.config/mcp/`（用 `__HOME__` 等占位符 sed 替换）。
- `templates/` — `AGENT_START_HERE.md`、`AGENT_CONTRACT.md`、`registry.example.json`、`discovery-review.example.json` 等占位符模板。
- `tests/smoke.sh` — `py_compile` + install + 各命令 dry-run，打印 `smoke-ok`。
- `docs/` — `architecture`（怎么工作）、`concept-model`（8 分类定义）、`publish` / `open-source-boundary`（发布边界）、`wechat-post`（对外文案草稿，勿动）。

## 数据流（两条，不交叉）

1. **contract 链（可写）**：`discover` → `discovered.json` → `registry.json` + `mcp/registry.json` → dashboard。
2. **runtime 旁路（只读，不写 registry）**：`ps` / `lsof` / `launchd` / BTM → `asset-runtime` / `asset-macos-signals` → dashboard（系统信号 tab + runtime tab）。

registry 在 runtime 旁路里**不被写入**。观测不靠维护纪律：跑一次扫一次，过时就重扫。

## dashboard 能力速查

- `GET /api/status` — summary（assets / mcp / runtime 计数）。
- `POST /api/scan?mode=daily|deep` — 重跑 discovery + MCP health。
- `POST /api/review`（JSON body）— 保存 review 决策（new / defer / ignore）。
- `POST /api/launchctl`（JSON body）— 开关 `~/Library/LaunchAgents` 下的 plist（bootstrap / bootout / enable / disable）。
- `POST /api/kill-process`（JSON body）— 终止 runtime 白名单进程（term / kill）。
- 资产按 **8 分类**分组渲染：`agent` / `mcp` / `cli-tool` / `skill` / `project` / `config` / `support` / `unsorted`（定义见 `concept-model.md`，代码在 `asset_group`）。

## 验证命令

```bash
python3 -m py_compile bin/agent-assets-*
./tests/smoke.sh
python3 bin/agent-assets-macos-signals --no-write      # 采集但不写文件
python3 bin/agent-assets-runtime --json | python3 -m json.tool
agent-assets-dashboard --serve --port 17654            # 起 dashboard 后另开终端：
curl -sS http://127.0.0.1:17654/api/status | python3 -m json.tool
```

## 维护红线

- **不搬包管理器内部目录**（npm / pip / brew / bun storage、Homebrew Cellar）。只给 agent 要调用的东西做 `~/.local/bin` wrapper 或 symlink。
- **dashboard 只绑 `127.0.0.1`**，不暴露公网。
- **registry 永不存 secret**（`register` 脚本对带 secret 的输入自动拒绝）。
- **仓库不内置 launchd plist**；常驻 dashboard 由用户自配（本机可在 `~/Library/LaunchAgents` 手配）。
- **registry 登记已退役为可选**；核心是 runtime 观测，不是台账完整性。不要把"登记越全越好"当目标。
- 改 `bin/` 功能后跑 `py_compile` + `smoke.sh`；改 `templates/` 占位符要和 `install.sh` 的 sed 替换键一致。

## 最近提交

- `aba5f85` Redo dashboard: 8-category model, system signals, launchd toggle
- `e2e2d62` Refine agent assets dashboard workflow
- `87072fa` Improve dashboard workflow and filters
- `6c9d854` Add project handoff document
- `f6c0f54` Add deep audit scan and fix skill counts

## 接手一句话

核心不是「扫越多路径越好」或「登记越全越好」，而是把运行态盲区照出来。registry 是历史快照，runtime 观测才是主菜。
