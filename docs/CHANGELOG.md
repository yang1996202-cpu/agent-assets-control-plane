# Changelog

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
