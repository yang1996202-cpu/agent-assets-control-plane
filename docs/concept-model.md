# Agent Assets 概念模型（待你拍板）

> 在改任何代码前，先把"资产怎么分类、dashboard 怎么显示"定死。
> 你过一遍，改/砍/加。定稿后才统一重做总览页 + 清理 registry。

## 一、核心病根

registry 现在 58 个资产，贴了 **50 多种** category 标签，还有 `agent-host` 这种没人懂的概念。

根因：`category` 一个字段塞了**三个维度**的信息，标准还来自**三处**：
- 类型（agent / mcp / skill…）
- 形态（cli / app / http…）
- 功能（browser-automation / messaging-bridge…）

来源：① 你手写进 registry 的、② discover 扫描自动打的、③ dashboard 兜底硬加的——三处标准打架，所以同一个东西标签不同。

## 二、新分类：主类型（每资产一个，互斥）

| 主类型 | 是什么 | 判定（一句话） | 现有例子 |
|---|---|---|---|
| **agent** | 能自主干活的 AI 主体 | 你会"跟它对话、让它干活" | claude-code, codex, cursor, alice, gemini-cli |
| **mcp** | MCP 服务 | 被 agent 调用的 stdio/http server | context7, notebooklm, wechat-mcp |
| **cli-tool** | 命令行工具（不是 agent） | 你调用它，但它不"对话" | git, rg, asset-list |
| **skill** | 技能包 / 技能库 | SKILL.md 集合 | claude 的 skill 目录 |
| **project** | 项目 / 工作区 | 一个代码或内容项目 | `~/projects/xxx` |
| **config** | 配置 / 规则 / 契约 | 告诉 agent 规则的文件 | AGENT_CONTRACT, registry 本身 |
| **support** | 运行时 / 支撑设施 | 跑上面东西的底座 | python, package-manager, launchd |
| **unsorted** | 待你人工标记 | 规则分不清、需你定的（临时区，不是永久类） | codex 系列、claude-skill-hub 等 |

> `unsorted` 是**临时区**：规则分不清的先放这，dashboard 会高亮"待标记 N"，你有空标记后归入其他 7 类。它不是永久分类，目标是清零。

## 三、形态标签（可选，补充说明，不互斥）

`cli` / `app` / `service` / `http` / `stdio`

一个 agent 可以同时是 `cli`。形态不抢主类型的位置。

## 四、Agent 只分两种（砍掉 host）

- **CLI agent**：命令行形态 → claude-code, codex, gemini-cli, hermes
- **app agent**：图形 app 形态 → Claude.app, Cursor.app, Alice, workbuddy

旧的 `agent-host`（claude-code / gemini-cli / codex / cursor / openclaw / hermes / claude-skill-hub / Claude.app / OpenCode.app / workbuddy）全部按形态归入上面两种。**不再有"宿主"这个概念。**

## 五、MCP 按宿主看

- 每个 MCP 记录被哪些宿主引用（你已有 4 个宿主配置：claude / cursor / workbuddy / project_xz）。
- 显示按宿主分组："**claude 用 X 个 / cursor 用 Y 个 / 共享 Z 个**"。
- 健康检查也**分宿主跑**，不再用 `claude mcp list` 一个宿主冒充全局。

## 六、总览页只回答一句："你现在该做什么"

- 大字突出：**待处理 N**（扫描发现、没登记、等你拍板）。
- 其他（agent 数 / MCP / 入口 / 台账）降到一行小字，或移到各自页。
- 砍掉"Agent 主体 App12 / Host10"这种没人懂的数字。

## 七、其他概念（人话定义）

- **入口**：agent 该调用的稳定命令。只看两件事：在不在、是不是坏链。
- **台账**：就是 registry——你登记了哪些资产。
- **待处理**：扫描发现、还没登记、等你决定（登记 / 忽略 / 稍后）的候选。
- **台账差异**：某东西"宿主配置里有"但"台账里没记"，或反之。

## 八、落地顺序（你拍板后我才动）

1. 我写脚本，按上表**提议**每个资产的新主类型 + 形态（58 条）。
2. 你逐条确认 / 改（快）。
3. 重做总览页（只突出待处理）。
4. 收敛 registry（category → 主类型 + 形态）。

## 需要你拍板

1. 主类型 **7 类**够不够？要加 / 砍哪个？
2. Agent 砍 host、分 CLI / app —— 确认？
3. MCP 按宿主分组 + 健康分宿主查 —— 确认？
4. 总览只突出"待处理"，其他降级 —— 确认？
