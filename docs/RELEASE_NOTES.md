# Release Notes

## v0.1.0

**发布日期**：2026-07-03

### 新增能力

- **本机运行态观测台**：无需手动维护台账，运行 `asset-runtime` 和 `asset-macos-signals` 即可发现后台泄漏、僵尸 dev server、常驻 daemon 和端口占用。
- **本地 Dashboard**：访问 `http://127.0.0.1:17654` 查看资产、MCP audit、runtime、系统信号四个视图，支持一键扫描。
- **8 分类资产模型**：Agent、MCP、命令行工具、技能、项目、配置、运行时/支撑、待标记，dashboard 按主类型分组展示。
- **MCP 宿主透视**：dashboard 按 host（Claude / Cursor / WorkBuddy / 自定义项目）分组展示 MCP 引用，并标识「宿主配置里有但台账没记」的漏网项。
- **系统信号交叉验证**：整合 launchd plist、BTM、登录项、系统扩展和端口监听，标记需关注的残留痕迹。

### 改进

- dashboard 内部模块化，便于后续扩展。
- 新增公共工具模块，减少跨脚本重复代码。
- 核心函数补充单元测试，smoke test 一键验证安装链路。

### 使用方式

```bash
# 运行态观测（核心）
asset-runtime
asset-macos-signals

# 启动 dashboard
agent-assets-dashboard --serve --open

# 磁盘扫描与项目索引（保留能力）
agent-assets-discover
agent-assets-projects
```

### 已知限制

- dashboard 仅绑定 `127.0.0.1`，不支持远程访问。
- registry 登记已退役为可选历史快照，不再强制维护。
- 当前仅支持 macOS（`asset-macos-signals` 依赖 launchd / BTM）。
