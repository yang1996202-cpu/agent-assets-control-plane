# 分类迁移 dry-run（历史决策记录）

> **状态（2026-06）**：分类模型已落地为 dashboard 8 分类（见 `concept-model.md` 第八节）。本 dry-run 未执行写入；逐条迁移已被通用的 8 分类分组取代。下方为本机 58 条私有资产快照，发布前按 `open-source-boundary.md` 评估。

> 每条：旧 category → 新 category ＋ 会丢弃的旧标签。**确认后才写 registry。**


**新分类计数**：agent 12 · mcp 8 · cli-tool 8 · skill 6 · project 2 · config 1 · support 11 · unsorted 10


## agent（12）

| 资产 | 旧 category | → 新 category | 丢弃 |
|---|---|---|---|
| alice | agent-app, cli, mcp-server, memory, skill-root | agent, app | agent-app, cli, mcp-server, memory, skill-root |
| claude-code | agent-host, cli, mcp-host | agent, cli | agent-host, mcp-host |
| openclaw | agent-host, cli, app-runtime | agent, cli | agent-host, app-runtime |
| hermes-agent | agent-host, cli, browser-automation | agent, cli | agent-host, browser-automation |
| gemini-cli | cli, agent-host, model-cli | agent, cli | agent-host, model-cli |
| Claude.app | agent-app, agent-host, cli | agent, app | agent-app, agent-host, cli |
| OpenCode.app | agent-app, agent-host, cli | agent, app | agent-app, agent-host, cli |
| AutoClaw.app | agent-app, cli | agent, app | agent-app, cli |
| workbuddy | agent-app, agent-host, skill-root, mcp, local-http | agent, app | agent-app, agent-host, skill-root, mcp, local-http |
| trae | agent-app | agent, app | agent-app |
| opencode-app | agent-app | agent, app | agent-app |
| antigravity-ide | agent-app | agent, app | agent-app |

## mcp（8）

| 资产 | 旧 category | → 新 category | 丢弃 |
|---|---|---|---|
| gbrain | cli, mcp, memory | mcp | cli, memory |
| mcp-context7 | mcp | mcp | — |
| mcp-notebooklm | mcp | mcp | — |
| mcp-wechat | mcp, project-tool | mcp | project-tool |
| mcp-docker | mcp | mcp | — |
| mcp-exa | mcp, remote-http | mcp | remote-http |
| workbuddy-connector-proxy | mcp, local-http | mcp | local-http |
| ask-gemini-mcp | mcp, cli, unconfigured-mcp | mcp | cli, unconfigured-mcp |

## cli-tool（8）

| 资产 | 旧 category | → 新 category | 丢弃 |
|---|---|---|---|
| alice-and-brain-cli-family | cli, agent-bridge | cli-tool, cli | agent-bridge |
| cc-connect | cli, agent-bridge, messaging-bridge | cli-tool, cli | agent-bridge, messaging-bridge |
| coze-cli | cli, cloud-agent-platform | cli-tool, cli | cloud-agent-platform |
| feishu-lark-cli-family | cli, feishu, lark | cli-tool, cli | feishu, lark |
| localtunnel | cli, network-tunnel | cli-tool, cli | network-tunnel |
| playwright-cli | cli, browser-automation, test-tool | cli-tool, cli | browser-automation, test-tool |
| cloudflare-wrangler | cli, deployment, cloudflare | cli-tool, cli | deployment, cloudflare |
| github-cli | cli, git, github | cli-tool, cli | git, github |

## skill（6）

| 资产 | 旧 category | → 新 category | 丢弃 |
|---|---|---|---|
| gstack | workflow, skill-pack | skill | workflow, skill-pack |
| opencode-openclaw-helpers | cli, agent-helper, skill-manager | skill | cli, agent-helper, skill-manager |
| shared-agents-skills | skill-root, shared-skill-pool, cross-agent-convention | skill | skill-root, shared-skill-pool, cross-agent-convention |
| vercel-skills-cli | cli, skill-manager, package-installer | skill | cli, skill-manager, package-installer |
| openskills | cli, skill-manager | skill | cli, skill-manager |
| guizang-social-card-skill | skill, claude-code-skill | skill | claude-code-skill |

## project（2）

| 资产 | 旧 category | → 新 category | 丢弃 |
|---|---|---|---|
| opencli | cli, browser-automation, project-tool | project | cli, browser-automation, project-tool |
| agent-assets-control-plane-repo | project-tool, open-source, agent-assets | project | project-tool, open-source, agent-assets |

## config（1）

| 资产 | 旧 category | → 新 category | 丢弃 |
|---|---|---|---|
| agent-assets-dashboard | dashboard, local-ui, agent-assets, launchd-service, cli | config | dashboard, local-ui, agent-assets, launchd-service, cli |

## support（11）

| 资产 | 旧 category | → 新 category | 丢弃 |
|---|---|---|---|
| uv-tools | package-manager, cli-runtime | support | package-manager, cli-runtime |
| legacy-nowledge-mem | legacy-memory, cli | support | legacy-memory, cli |
| node-package-managers | package-manager, cli-runtime | support | package-manager, cli-runtime |
| cagent | cli, agent-runtime | support | cli, agent-runtime |
| package-manager-npm | package-manager, cli-runtime | support | package-manager, cli-runtime |
| package-manager-pnpm | package-manager, cli-runtime | support | package-manager, cli-runtime |
| package-manager-bun | package-manager, cli-runtime | support | package-manager, cli-runtime |
| package-manager-homebrew | package-manager, macos | support | package-manager, macos |
| package-manager-pip3 | package-manager, python | support | package-manager, python |
| package-manager-uv | package-manager, python | support | package-manager, python |
| package-manager-gem | package-manager, ruby | support | package-manager, ruby |

## unsorted（10）

| 资产 | 旧 category | → 新 category | 丢弃 |
|---|---|---|---|
| codex-coco | agent-host, mcp-host, skill-host, cli | unsorted | agent-host, mcp-host, skill-host, cli |
| cursor | agent-host, mcp-host | unsorted | agent-host, mcp-host |
| agent-assets-system | registry, onboarding, local-agent-contract, dashboard, project-index, macos-signals | unsorted | registry, onboarding, local-agent-contract, dashboard, project-index, macos-signals |
| boss-cli | cli, project-tool, auth-sensitive | unsorted | cli, project-tool, auth-sensitive |
| clawhub-cli | cli, skill-manager, openclaw | unsorted | cli, skill-manager, openclaw |
| codexbar | agent-app, cli | unsorted | agent-app, cli |
| claude-skill-hub | agent-host, cli, skill-manager | unsorted | agent-host, cli, skill-manager |
| codebuddy | agent-app, skill-root, connector-marketplace | unsorted | agent-app, skill-root, connector-marketplace |
| qclaw | agent-app | unsorted | agent-app |
| codex-proxy | agent-app | unsorted | agent-app |

## 会被丢弃的旧标签（你要决定：全丢，还是某些保留）

| 旧标签 | 出现次数 |
|---|---|
| cli | 18 |
| agent-app | 12 |
| agent-host | 10 |
| package-manager | 9 |
| cli-runtime | 5 |
| skill-manager | 5 |
| skill-root | 4 |
| project-tool | 4 |
| mcp-host | 3 |
| browser-automation | 3 |
| memory | 2 |
| local-http | 2 |
| agent-bridge | 2 |
| dashboard | 2 |
| agent-assets | 2 |
| python | 2 |
| mcp-server | 1 |
| skill-host | 1 |
| workflow | 1 |
| skill-pack | 1 |
| remote-http | 1 |
| agent-helper | 1 |
| legacy-memory | 1 |
| registry | 1 |
| onboarding | 1 |
| local-agent-contract | 1 |
| project-index | 1 |
| macos-signals | 1 |
| local-ui | 1 |
| launchd-service | 1 |
| auth-sensitive | 1 |
| app-runtime | 1 |
| messaging-bridge | 1 |
| openclaw | 1 |
| cloud-agent-platform | 1 |
| feishu | 1 |
| lark | 1 |
| model-cli | 1 |
| network-tunnel | 1 |
| test-tool | 1 |
| deployment | 1 |
| cloudflare | 1 |
| agent-runtime | 1 |
| unconfigured-mcp | 1 |
| open-source | 1 |
| git | 1 |
| github | 1 |
| mcp | 1 |
| connector-marketplace | 1 |
| shared-skill-pool | 1 |
| cross-agent-convention | 1 |
| package-installer | 1 |
| macos | 1 |
| ruby | 1 |
| claude-code-skill | 1 |
