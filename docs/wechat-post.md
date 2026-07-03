# 我造了一个工具，专门治 AI Agent 的"工具散落病"

## 一、问题：你的 AI 工具正在到处流浪

如果你最近在用 Claude Code、Cursor、Codex 或者其他 AI Agent 工具，大概率已经遇到了同一个麻烦：

**工具装了一大堆，但每开一个新会话，Agent 都要从头找一遍。**

MCP 服务器藏在 `~/.claude.json` 里，CLI 工具从 npm、uv、pip、brew 不同渠道灌进来，Skill 包 clone 到各个 dotdir，项目代码散落在 `~/projects` 各处。

更烦的是，当你跟不是当初安装那个工具的 Agent 说"帮我用 XX 工具做件事"，它往往会反问："这个工具装在哪？路径是什么？"——你得手动告诉它，每次都要。

这不是 Agent 不够聪明，是**本地工具生态根本没有一个统一的索引**。

## 二、常见的"伪解决方案"

我试过几种整理思路，发现都有坑：

**方案 A：把所有工具搬到同一个目录。**
不现实。npm、pip、Homebrew 都有自己的管理逻辑，硬搬会搞坏包管理器的依赖追踪。

**方案 B：每个 Agent 平台自己管自己的配置。**
Claude 有 MCP 配置，Cursor 有 settings.json，Windsurf 有自己的一套——结果是三套索引，互不打通。

**方案 C：每次让 Agent 自己搜。**
Agent 会遍历一堆 dotdir，搜到很多噪声，还经常问用户确认。效率低，体验差。

这三个方案的共同问题是：**要么违背技术现实，要么增加用户负担。**

## 三、我的解法：Control Plane，不是搬家

我做了一个叫 **Agent Assets Control Plane** 的开源工具。核心思路很简单：

> **不搬任何东西，只建立一个稳定的契约和一份可视的清单。**

它有两个面：

**给机器读的——Agent Contract。**

本地固定位置放几个文件：
- `~/AGENT_START_HERE.md` —— Agent 第一入口
- `~/.config/agent-assets/registry.json` —— 已注册资产总账
- `~/.config/mcp/registry.json` —— MCP 服务器索引

任何新 Agent 上来先读这些文件，就能知道本地有什么工具、在哪里、怎么用，不用反复问用户。

**给人看的——Dashboard。**

本地起一个网页（`http://127.0.0.1:17654/`），可视化展示：
- 已注册的 CLI 工具、MCP 服务器、Skill 包
- 扫描发现但待审核的候选工具
- 每个资产的健康状态和入口路径

人可以看到 Agent 看到了什么，也可以手动审核、注册、忽略某个发现项。
![[Pasted image 20260605224522.png]]

## 四、从 SaaS 解决方案到 Agent 基础设施

我以前做 SaaS 解决方案顾问，最深的体会是：**客户买的不是功能，是治理。**

一个系统功能再强，如果配置散落、权限混乱、没人知道谁改了什么，客户最终会用不起来。AI Agent 生态现在正走在这条老路上——工具爆发式增长，但治理层还没跟上。

Agent Assets Control Plane 本质上就是把 SaaS 领域的"配置治理"思路搬到了个人本地环境。不是为了炫技，是为了让 Agent 生态从"能跑"进化到"好管"。

## 五、怎么用

一行安装：

```bash
git clone https://github.com/yang1996202-cpu/agent-assets-control-plane.git ~/projects/agent-assets-control-plane
cd ~/projects/agent-assets-control-plane
./scripts/install.sh
```

装完后，本地会多几个命令：

```bash
agent-assets-discover    # 扫描本地机器
agent-assets-dashboard   # 启动可视化面板
agent-assets-list        # 列出已注册资产
agent-assets-register    # 手动登记新工具
```

给 Agent 的指令也只需要一句话：

> Read `~/AGENT_START_HERE.md` first, then follow the local agent-assets rules.

## 六、开源，欢迎来用

这个项目已经放在 GitHub 上了，MIT 协议，没有任何商业限制。

https://github.com/yang1996202-cpu/agent-assets-control-plane

它现在还是 v0.1.0，功能骨架已经搭好：扫描、注册、列表、面板。下一步会加 dashboard 上的操作按钮、更强的 Schema 校验、以及打包安装。

如果你也受够了 Agent 每次都要问"这个工具在哪"，可以试一下。有问题直接提 Issue，有想法欢迎 PR。

**Agent 工具散落在各处不是问题，没有治理层才是。**
