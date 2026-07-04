# Changelog

## 2026-07-04 03:35

### [BUG] 修复中文/无点 launchd Label 禁用状态识别错误

| 字段 | 内容 |
|---|---|
| **问题/需求** | 「闪电说」Label 为中文（不含点），用户点击「禁用自启」后操作记录显示成功，但界面仍显示「自启·已启用」。 |
| **根因/方案** | `_launchctl_disabled_set()` 解析 `launchctl print-disabled` 输出时，错误地过滤掉不含 `.` 的 Label，导致中文或短名称服务被排除在已禁用集合外。移除该点号限制，仅排除花括号和 header 行。 |
| **改动范围** | `lib/agent_assets_dashboard_render.py`、`tests/test_dashboard_render.py`、`docs/CHANGELOG.md` |
| **影响面** | 中文 Label、短名称 Label 的 LaunchAgent 禁用/启用状态现在能正确显示；补充了针对中文 Label 的单元测试。 |
| **状态** | ✅ 已完成 |

## 2026-07-04 03:25

### [FEAT] 系统信号实时 PID 校验 + 后台每 5 分钟自动刷新

| 字段 | 内容 |
|---|---|
| **问题/需求** | 用户在系统外杀掉腾讯 ima 等后台进程后，dashboard 仍显示「运行中」；搜狗输入法等 launchd 服务操作后，同一应用的多服务状态不一致。 |
| **根因/方案** | `macos-signals.json` 是快照，会滞后。渲染层对所有 running 行做实时 PID 存在性校验：如果快照显示 running 但实际 pid 已不存在，状态显示为「已停止（进程已退出）」。同时在 dashboard 服务启动一个后台线程，每 5 分钟静默刷新一次系统信号并重写页面，让快照不会过旧。 |
| **改动范围** | `lib/agent_assets_dashboard_render.py`（新增 `_pid_exists`、实时校验扩展到所有 running 行）、`lib/agent_assets_dashboard_api.py`（后台定时刷新线程 + 锁）、`docs/CHANGELOG.md` |
| **影响面** | 系统信号 tab 对后台进程和 launchd 服务的状态更准确；launchctl 操作后的刷新与定时刷新通过锁互斥；不改动 macos-signals 采集逻辑。 |
| **状态** | ✅ 已完成 |

## 2026-07-04 03:10

### [FEAT] 系统信号：「已登记」改名「登录项/扩展」，同应用多服务分组展示

| 字段 | 内容 |
|---|---|
| **问题/需求** | 「已登记」状态含义不清；同应用（如搜狗输入法、Docker、向日葵）会拆成多个 launchd 服务行，用户看不懂为什么一个应用出现多次。 |
| **根因/方案** | 「已登记」其实是登录项/系统扩展/后台项，没有 launchd plist 可操作，改名为「登录项/扩展」更直观。对系统信号表格按展示标题分组：同一应用多个服务时，顶部显示应用名组头，组内只显示具体服务标识，避免重复和混乱。 |
| **改动范围** | `lib/agent_assets_dashboard_render.py`、`lib/agent_assets_dashboard_html.py`、`docs/CHANGELOG.md` |
| **影响面** | 系统信号 tab 状态筛选按钮从「已登记」变为「登录项/扩展」；同应用多服务合并展示；无测试破坏。 |
| **状态** | ✅ 已完成 |

## 2026-07-04 02:55

### [REFACTOR] install.sh 自动清理旧二进制与过期缓存文件

| 字段 | 内容 |
|---|---|
| **问题/需求** | 本机残留多个早期版本的二进制（`asset-dashboard`、`asset-discover` 等）和缓存/报告/备份文件，容易跟新版路径解析冲突，导致重复出现旧 bug。 |
| **根因/方案** | `scripts/install.sh` 增加清理步骤：删除已废弃的 `asset-*` 旧二进制、删除当前代码不再引用的 `macos-signals-review.json`、`PROJECT_STATUS.md`、`skill-inventory-report.*`、`registry.json.bak*` 等文件。 |
| **改动范围** | `scripts/install.sh`、`docs/CHANGELOG.md`；本机已手动清理 `~/.local/bin/` 旧二进制与 `~/.config/agent-assets/` 过期文件。 |
| **影响面** | 重新运行 `install.sh` 会自动保持环境干净；减少旧文件导致的路径冲突和误调用。 |
| **状态** | ✅ 已完成 |

## 2026-07-04 02:50

### [BUG] 系统信号刷新失败：旧二进制 `agent-assets-macos-signals` 与 LaunchAgent 指向过期 `asset-dashboard`

| 字段 | 内容 |
|---|---|
| **问题/需求** | 系统信号 tab 顶部显示「系统信号刷新失败：unrecognized arguments: --skip-btm」；常驻 dashboard 的 LaunchAgent 指向的是 6 月的旧 `asset-dashboard` 二进制。 |
| **根因/方案** | `install.sh` 把新版 `agent-assets-macos-signals` 安装为 `asset-macos-signals`，但 `lib/agent_assets_dashboard_paths.py` 优先查找旧名 `agent-assets-macos-signals`，该旧文件仍留在 `~/.local/bin` 且不支持 `--skip-btm`。同时 `~/Library/LaunchAgents/com.yang.agent-assets-dashboard.plist` 仍指向旧 `asset-dashboard`。修复路径解析优先查找 `asset-macos-signals`、保留旧名兜底；`install.sh` 安装后删除会冲突的旧名；更新 LaunchAgent plist 指向 `agent-assets-dashboard` 并重新加载；清理过期的 `asset-dashboard`、`asset-discover`、`asset-list`、`asset-projects`、`asset-register` 等旧二进制。 |
| **改动范围** | `lib/agent_assets_dashboard_paths.py`、`scripts/install.sh`、`docs/CHANGELOG.md`；本机配置 `~/Library/LaunchAgents/com.yang.agent-assets-dashboard.plist`、`~/.local/bin` 旧二进制。 |
| **影响面** | 系统信号刷新不再因旧二进制报错；常驻 dashboard 现在由新版 `agent-assets-dashboard` 启动；本机旧二进制清理后减少路径冲突。 |
| **状态** | ✅ 已完成 |

## 2026-07-04 02:30

### [BUG] 修复 launchctl 操作后页面刷新不可靠，优化系统信号关联列展示

| 字段 | 内容 |
|---|---|
| **问题/需求** | 系统信号 tab 点击「停止/启动/禁用自启/启用自启」后页面立即 reload，但后端异步刷新需 4 秒，用户常看到旧状态；「关联」列长 chip 把行撑得很高，表格难看。 |
| **根因/方案** | 后端：`handle_launchctl()` 执行命令后立即用 `launchctl print` 校验真实状态并修正 `action_zh`；后台刷新失败时将 `_refresh_error` 写入 `macos-signals.json`，成功时将 `last_signals_refresh_at` 写入 `dashboard-state.json`。前端：`js-launchctl` / `js-launchctl-undo` 点击后禁用按钮、toast 提示，轮询 `/api/status` 的 `last_signals_refresh_at`，最多 12 秒后 reload。渲染：系统信号「关联」列最多显示 1 个 chip，超出用 `+N` badge 并 title 展示完整列表；表格列宽与垂直对齐优化，避免换行撑高。 |
| **改动范围** | `lib/agent_assets_dashboard_api.py`、`lib/agent_assets_dashboard_html.py`、`lib/agent_assets_dashboard_render.py`、`lib/agent_assets_dashboard_paths.py`、`tests/test_dashboard_api.py`、`tests/test_dashboard_render.py`、`docs/PRD.md`、`docs/CHANGELOG.md` |
| **影响面** | 系统信号 tab 的 launchctl 操作交互改为轮询等待；`/api/status` 新增 `last_signals_refresh_at`；系统信号表格「关联」列与操作区视觉更紧凑；不改动采集逻辑，向后兼容。 |
| **状态** | ✅ 已完成 |

## 2026-07-04 02:24

### [FEAT] 系统进程 UI 清爽化，系统信号新增进程资源列

| 字段 | 内容 |
|---|---|
| **问题/需求** | 系统进程 tab 视觉风格与其它板块不一致、表格信息噪音大；系统信号 tab 看不到 running 服务对应的 CPU / 内存占用。 |
| **根因/方案** | 系统进程：统一使用卡片式面板、更克制的细进度条 + 数值布局、弱化 PID、高亮当前排序列，筛选按钮精简为全部 / 用户进程 / App / MCP / Dev Server / Support / system / unknown。系统信号：渲染层按 pid 匹配 `collect_all_processes()` 返回的进程列表，为 running 且 processes 非空的服务补充「资源」列，格式 `CPU X% · 内存 Y MB`。 |
| **改动范围** | `lib/agent_assets_dashboard_render.py`、`lib/agent_assets_dashboard_html.py`、`tests/test_dashboard_render.py`、`docs/CHANGELOG.md` |
| **影响面** | 系统进程 tab 视觉更清爽、排序与筛选行为不变；系统信号 tab 新增「资源」列，macos-signals.json 采集逻辑未改动；dashboard 生成后无需重启即可看到新静态页面。 |
| **状态** | ✅ 已完成 |

## 2026-07-03 18:15

### [BUG] launchctl 停止服务后 dashboard 仍显示「运行中」

| 字段 | 内容 |
|---|---|
| **问题/需求** | 在 dashboard 系统信号 tab 点击「停止」百度网盘服务（`netdisk_service`）后，`launchctl` 实际已 unload，但页面刷新后仍显示「运行中」。 |
| **根因/方案** | dashboard 在 `launchctl` 操作后虽然会在后台刷新信号，但等待时间仅 2 秒，且未显式重写静态 HTML；同时旧 dashboard 进程缓存了修改前的 API 模块。将等待时间延长至 4 秒，显式调用 `data.refresh_signals(skip_btm=True)` 并记录错误日志，随后调用 `html_module.write_dashboard(..., run_signals=True)` 重写页面；重启 dashboard 服务以加载最新代码。 |
| **改动范围** | `lib/agent_assets_dashboard_api.py`、`docs/CHANGELOG.md` |
| **影响面** | 系统信号 tab 的启动/停止/启用自启/禁用自启操作后，页面约 4 秒后会自动同步最新状态；若刷新失败会在服务端日志记录。 |
| **状态** | ✅ 已完成 |

## 2026-07-03 13:45

### [REFACTOR] 开源打磨：个人信息外置、README、CONTRIBUTING、CI

| 字段 | 内容 |
|---|---|
| **问题/需求** | 开源前需要清理与用户个人环境强耦合的内容（中文应用映射、个人工具识别规则），并补齐 README、CONTRIBUTING、CI 等基础设施。 |
| **根因/方案** | 将 `PRODUCT_MAP` 和进程分类规则从核心代码移到 `~/.config/agent-assets/` 下的 JSON 配置，由安装脚本从示例模板复制；重写 README.md 明确平台与使用方式；新增 CONTRIBUTING.md；新增 GitHub Actions CI 工作流；新增 docs/RELEASE_NOTES.md 模板；删除过期的 GitHub Release v0.1.0。 |
| **改动范围** | `bin/agent-assets-runtime`、`lib/agent_assets_dashboard_paths.py`、`lib/agent_assets_dashboard_render.py`、`scripts/install.sh`、`README.md`、`CONTRIBUTING.md`、`.github/workflows/ci.yml`、`templates/agent-assets/product-map.example.json`、`templates/agent-assets/runtime-classification.example.json`、`docs/FEATURES.md`、`docs/CHANGELOG.md`、`docs/RELEASE_NOTES.md` |
| **影响面** | 本机行为不变（配置已自动复制到 `~/.config/agent-assets/`）；代码库更适合公开 fork；新用户首次安装后可直接运行。 |
| **状态** | ✅ 已完成 |

## 2026-07-03 13:20

### [FEAT] 系统进程视图支持 GUI 应用、CPU 占用与表头排序

| 字段 | 内容 |
|---|---|
| **问题/需求** | 系统进程 tab 默认过滤掉了 GUI 应用（微信、Chrome 等），导致高内存进程看不到；页面顶部高占用卡片与其他 tab 风格不统一；CPU 列只显示 `—`，不够直观。 |
| **根因/方案** | `asset-runtime` 新增 `--show-apps` 参数，在系统进程视图中保留 GUI 应用并单独归类为 `app`；移除顶部高占用卡片区，改为统一的筛选按钮 + 可排序表格；CPU / 内存列增加可视化进度条；表头支持点击排序。 |
| **改动范围** | `bin/agent-assets-runtime`、`lib/agent_assets_dashboard_data.py`、`lib/agent_assets_dashboard_render.py`、`lib/agent_assets_dashboard_html.py`、`lib/agent_assets_dashboard_api.py`、`tests/test_runtime.py`、`tests/test_dashboard_data.py`、`docs/CHANGELOG.md` |
| **影响面** | 系统进程 tab 现在显示 GUI 应用进程；页面风格与 CLI 工具 / 运行态 tab 更一致；launchctl 对已停止服务重复点击「停止」不再误报失败。 |
| **状态** | ✅ 已完成 |

## 2026-07-03 12:35

### [FEAT] 新增系统进程视图与 RSS 内存字段

| 字段 | 内容 |
|---|---|
| **问题/需求** | dashboard 运行态视图缺少对全部系统进程的集中展示，runtime 进程行缺少内存占用信息，无法快速识别高内存泄漏或异常常驻进程。 |
| **根因/方案** | `asset-runtime` 的 ps 输出新增 `rss` 列并在 JSON 中携带；dashboard 新增「系统进程」tab，调用 `collect_all_processes()` 渲染完整进程表，支持按名称/类型筛选。 |
| **改动范围** | `bin/agent-assets-runtime`、`lib/agent_assets_dashboard_data.py`、`lib/agent_assets_dashboard_html.py`、`lib/agent_assets_dashboard_render.py` |
| **影响面** | dashboard 新增「系统进程」导航与表格；runtime JSON 输出新增 `rss` 字段；现有 dashboard 视图与 runtime 分类逻辑向后兼容。 |
| **状态** | ✅ 已完成 |

## 2026-07-03 08:20

### [REFACTOR] 项目工程化整理：公共模块、dashboard 拆分、单元测试与文档合规

| 字段 | 内容 |
|---|---|
| **问题/需求** | 项目定位已演进为「本机运行态观测台」，但代码组织仍停留在原型阶段：dashboard 单文件近 2800 行、工具函数跨脚本复制、无单元测试、缺少 AGENTS.md 要求的强制文档。 |
| **根因/方案** | 预登记模式被证明不可维护，核心转向只读运行态扫描；通过提取公共模块、拆分 dashboard、补单元测试、补齐文档，使工程实现与新的产品定位对齐。 |
| **改动范围** | `.gitignore`、`scripts/install.sh`、`bin/*`、`lib/*`、`tests/*`、`docs/*`；新增 `lib/agent_assets_dashboard_{paths,data,render,html,api}.py`；`bin/agent-assets-dashboard` 缩减为入口脚本；`bin/agent-assets-macos-signals` 的 host 识别改用 `lib.host_config_keys()`。 |
| **影响面** | 所有 CLI 脚本改为 import `lib/agent_assets_common.py`；dashboard 内部模块化但外部行为不变；install.sh 新增安装 `~/.local/lib/agent-assets/`；已有本机安装需重新运行 install。 |
| **状态** | ✅ 已完成 |

## 2026-06-26

### [FEAT] 运行态观测台定位落地与 dashboard 8 分类模型

| 字段 | 内容 |
|---|---|
| **问题/需求** | registry 预登记与实际环境必然脱节，agent/host 概念混乱，dashboard 总览信息过载。 |
| **根因/方案** | 把核心从「资产登记簿」改为「运行态观测台」；引入 8 分类主类型（agent / mcp / cli-tool / skill / project / config / support / unsorted）；新增 `asset-runtime` 进程盲区扫描与 `asset-macos-signals` launchd 全景。 |
| **改动范围** | `README.md`、`docs/architecture.md`、`docs/concept-model.md`、`docs/HANDOFF.md`、`bin/agent-assets-dashboard`、`bin/agent-assets-runtime`、`bin/agent-assets-macos-signals`、`scripts/install.sh` |
| **影响面** | registry 降为历史快照；dashboard 按 8 分类分组；新增运行态观测入口。 |
| **状态** | ✅ 已完成 |

## 2026-06-20

### [FEAT] 新增项目索引与 deep audit 扫描

| 字段 | 内容 |
|---|---|
| **问题/需求** | `~/projects` 之外的旧项目、下载目录、host workspace 缺乏统一索引。 |
| **根因/方案** | 新增 `agent-assets-projects` 索引多个根目录，按 `canonical` / `legacy` / `download_candidate` / `host_managed` 标注角色。 |
| **改动范围** | `bin/agent-assets-projects`、`bin/agent-assets-discover`、`bin/agent-assets-dashboard` |
| **影响面** | dashboard 新增 Projects tab；discover 支持 `deep` 模式。 |
| **状态** | ✅ 已完成 |
