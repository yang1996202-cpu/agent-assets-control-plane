# Changelog

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
