"""Agent Assets Dashboard — HTML 渲染函数。

背景：dashboard 需要把资产、MCP、项目、发现候选、运行时、系统信号等数据渲染成 HTML。
这些函数原本全部内嵌在 dashboard 入口脚本里。
设计意图：把纯渲染逻辑（字符串拼接）拆到独立模块，与数据获取和 HTTP 服务解耦。
关键约束：
- 所有 HTML escape 走 lib.h；路径 chip 走 lib.chip。
- 本模块不直接读取文件或执行外部命令，只接收已处理好的数据。
"""

import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import urllib.parse

import agent_assets_common as lib
import agent_assets_dashboard_data as data
import agent_assets_dashboard_paths as paths


# ---- 系统信号：厂商→产品人话映射 ----
PRODUCT_MAP = [
    ("openclaw", "OpenClaw 网关", "你的 OpenClaw agent 网关服务"),
    ("gbrain", "gbrain 记忆服务", "你的 gbrain 本地记忆 MCP"),
    ("cc-connect", "cc-connect 桥接", "你的消息桥接脚本"),
    ("asset-dashboard", "本控制台", "就是这个 Agent Assets 控制台"),
    ("new-api-macos", "new-api 网关", "你装的 AI API 网关"),
    ("run_server.sh", "自定义脚本", "你自己的服务脚本"),
    ("run_refresh_loop.sh", "自定义脚本", "你自己的刷新循环脚本"),
    ("run_morning_brief.sh", "自定义脚本", "你自己的早报脚本"),
    ("com.docker.vmnetd", "Docker 网络守护", "Docker 系统级虚拟网络守护"),
    ("com.docker.socket", "Docker socket", "Docker 系统级 socket 守护"),
    ("docker", "Docker", "Docker 容器引擎"),
    ("贝锐向日葵", "向日葵", "贝锐 Oray 远程控制（含多个组件）"),
    ("best oray", "向日葵", "贝锐 Oray 远程控制"),
    ("oray", "向日葵", "贝锐 Oray 远程控制"),
    ("todesk", "ToDesk", "ToDesk 远程控制（含卸载助手）"),
    ("youqu", "ToDesk", "ToDesk 远程控制"),
    ("clash-verge", "Clash Verge", "Clash Verge 网络代理"),
    ("clash-ver", "Clash Verge", "Clash Verge 网络代理"),
    ("clashxpro", "ClashX Pro", "ClashX Pro 网络代理"),
    ("west2online", "ClashX 系列", "西二在线 ClashX 代理辅助"),
    ("metacubex", "ClashX", "ClashX 网络代理"),
    ("clashx", "ClashX", "ClashX 网络代理"),
    ("sogou", "搜狗输入法", "搜狗输入法及语音/斗图插件"),
    ("squirrel", "鼠须管", "RIME 鼠须管输入法"),
    ("百度网盘", "百度网盘", "百度网盘"),
    ("baidu", "百度网盘", "百度网盘"),
    ("ninxsoft", "mist", "mist 系统镜像重装工具"),
    ("mist", "mist", "mist 系统镜像重装工具（作者 Nindi Gill）"),
    ("google.keystone", "Google 自动更新", "Google 软件后台更新服务"),
    ("googleupdater", "Google 自动更新", "Google 软件后台更新服务"),
    ("payguard", "支付宝控件", "支付宝安全控件"),
    ("alipay", "支付宝", "支付宝相关"),
    ("闪电说", "闪电说", "闪电说 App"),
    ("tanwei", "闪电说", "闪电说（武汉探微）"),
    ("codexbar", "CodexBar", "Codex 菜单栏辅助工具"),
    ("com.openai.codex", "OpenAI Codex", "OpenAI Codex 应用"),
    ("codex", "OpenAI Codex", "OpenAI Codex"),
    ("ima.copilot", "腾讯 ima", "腾讯 ima.copilot 知识助手"),
    ("autoclaw", "AutoClaw", "AutoClaw agent 应用"),
    ("夸克", "夸克", "夸克浏览器"),
    ("quark", "夸克", "夸克"),
    ("donglemonitor", "donglemonitor", "加密狗/许可证监控（待你确认用途）"),
    ("com.vortex", "Vortex 助手", "Vortex 应用辅助（待你确认）"),
    ("drivemanagerd", "drivemanagerd", "驱动管理守护（待你确认归属）"),
    ("播客", "Apple 播客", "macOS 系统自带"),
    ("股市", "Apple 股市", "macOS 系统自带"),
]


CONTROL_META = {
    "user-launchd": ("🟢", "你的·可开关", "~/Library/LaunchAgents 与 /Library/LaunchAgents，可在此控制"),
    "system-launchd": ("⚪", "系统级·别动", "/Library/LaunchDaemons 等系统守护，需 sudo，前端不操作"),
    "app-running": ("⚡", "在跑", "正在运行的应用进程；停止=杀进程，被 launchd 管的会自启"),
    "login-item": ("🔑", "登录项", "登录项/后台项，在系统设置 > 通用 > 登录项里管理"),
}


RUNTIME_GROUP_META = {
    "leak": ("⚠️", "泄漏", "同一指纹出现多次的进程，通常是 MCP / dev server 被重复拉起、没有回收。多实例会同时占内存和句柄。"),
    "zombie": ("🧟", "僵尸 Dev server", "serve / 监听类 dev server 还挂着，项目目录可能早就不存在或已经没人用。"),
    "ports": ("🔌", "端口占用", "本机监听端口清单。定位「谁占了 17654」这类问题用这个。"),
}


RUNTIME_CATEGORY_META = [
    ("mcp", "🤖", "MCP Servers", "被 Agent host 调用的 MCP server 进程，stdio / http 都有。"),
    ("agent-daemon", "🤖", "Agent Daemons", "Agent 框架自己的常驻 gateway / hub / watcher / browser daemon。"),
    ("dev-server", "🌐", "Dev Servers", "vite / next / webpack 等开发预览服务器，容易变成僵尸。"),
    ("support", "⚙️", "Support / Runtime", "支撑运行时，如当前 dashboard 自己、package manager、解释器。"),
    ("system", "🔒", "System", "系统级 daemon / agent / 服务。默认 asset-runtime 会过滤，加 --show-system 才出现。"),
    ("unknown", "❓", "Other / Unclassified", "没被规则归到上面的进程，可能藏着你想找的东西。"),
]


def render_chips(values, css_class=""):
    values = lib.listify(values)
    if not values:
        return '<span class="muted">无</span>'
    return "\n".join(lib.chip(v, css_class) for v in values)


def label_for_state(state):
    state_labels = {
        "registered": "已登记",
        "connected": "已连接",
        "failed": "失败",
        "unknown": "未知",
        "internal": "内部",
        "exec": "可执行",
        "file": "文件",
        "dir": "目录",
        "file-ref": "文件引用",
        "ref": "引用",
        "missing": "缺失",
        "broken-link": "坏链",
        "new": "待处理",
        "defer": "稍后处理",
        "ignore": "已忽略",
        "app": "应用",
        "mcp-wrapper": "MCP 包装器",
        "agent-command": "Agent 命令",
        "dashboard": "面板",
        "runtime": "运行时",
        "cli": "CLI",
        "canonical": "标准项目",
        "legacy": "旧位置",
        "download_candidate": "下载候选",
        "host_managed": "宿主管理",
        "registered_source": "已登记源码",
        "manual": "手动根目录",
        "linked": "已关联资产",
        "git-repo": "Git 仓库",
        "node-package": "Node 包",
        "python-package": "Python 包",
        "go-module": "Go 模块",
        "rust-package": "Rust 包",
        "skill": "Skill",
        "mcp-candidate": "MCP 候选",
        "cli-candidate": "CLI 候选",
        "documentation": "文档项目",
        "enabled": "已启用",
        "disabled": "已关闭",
        "running": "运行中",
        "not-running": "未运行",
        "listening": "监听端口",
        "privileged": "高权限",
        "attention": "需关注",
        "residual-candidate": "残留候选",
        "launch-agent": "LaunchAgent",
        "launch-daemon": "LaunchDaemon",
        "global-agent": "全局 Agent",
        "remote-control": "远控类",
        "network-proxy": "代理/网络",
        "agent-service": "Agent 服务",
        "updater": "更新器",
        "input-method": "输入法",
        "error": "异常",
        "confirmed": "已确认",
        "residual": "残留",
        "not-agent": "非 Agent",
    }
    return state_labels.get(state, state)


def render_filter_bar(section, items):
    visible_items = [(label, value, count) for label, value, count in items if count]
    if not visible_items:
        return ""
    buttons = [f'<button class="filter-chip active" data-filter-section="{lib.h(section)}" data-filter="">全部</button>']
    for label, value, count in visible_items:
        buttons.append(
            f'<button class="filter-chip" data-filter-section="{lib.h(section)}" data-filter="{lib.h(value)}">{lib.h(label)} <span>{count}</span></button>'
        )
    return f'<div class="filter-bar">{"".join(buttons)}</div>'


def render_asset_cards(agent_registry):
    return "\n".join(render_asset_card(asset_id, asset) for asset_id, asset in sorted(agent_registry.get("assets", {}).items()))


def asset_group(asset):
    categories = set(asset.get("category", []))
    if "unsorted" in categories:
        return "unsorted", "⚠ 待标记"
    if "agent" in categories:
        return "agent", "Agent"
    if "mcp" in categories:
        return "mcp", "MCP 服务"
    if "cli-tool" in categories:
        return "cli-tool", "命令行工具"
    if "skill" in categories:
        return "skill", "技能"
    if "project" in categories:
        return "project", "项目"
    if "config" in categories:
        return "config", "配置"
    if "support" in categories:
        return "support", "运行时 / 支撑"
    return "other", "其他"


def render_asset_sections(agent_registry):
    groups = {}
    for asset_id, asset in sorted(agent_registry.get("assets", {}).items()):
        group_key, group_label = asset_group(asset)
        groups.setdefault(group_key, {"label": group_label, "items": []})["items"].append((asset_id, asset))
    order = ["agent", "mcp", "cli-tool", "skill", "project", "config", "support", "unsorted", "other"]
    sections = []
    for group_key in order:
        group = groups.get(group_key)
        if not group:
            continue
        items = group["items"]
        if not items:
            continue
        cards = "\n".join(render_asset_card(asset_id, asset) for asset_id, asset in items)
        sections.append(f"""
        <div class="content-group" id="asset-group-{group_key}">
          <div class="content-group-head">
            <h3>{lib.h(group["label"])}</h3>
            <span class="count-pill">{len(items)} 项</span>
          </div>
          <div class="asset-grid">{cards}</div>
        </div>
        """)
    return "\n".join(sections)


def render_asset_filters(agent_registry):
    counts = {}
    for asset in agent_registry.get("assets", {}).values():
        group_key, _group_label = asset_group(asset)
        counts[group_key] = counts.get(group_key, 0) + 1
    items = [
        ("Agent", "agent", counts.get("agent", 0)),
        ("MCP 服务", "mcp", counts.get("mcp", 0)),
        ("命令行工具", "cli-tool", counts.get("cli-tool", 0)),
        ("技能", "skill", counts.get("skill", 0)),
        ("项目", "project", counts.get("project", 0)),
        ("配置", "config", counts.get("config", 0)),
        ("运行时 / 支撑", "support", counts.get("support", 0)),
        ("⚠ 待标记", "unsorted", counts.get("unsorted", 0)),
    ]
    return render_filter_bar("assets", items)


def asset_summary_chips(agent_registry):
    counts = {}
    for asset in agent_registry.get("assets", {}).values():
        group_key, _group_label = asset_group(asset)
        counts[group_key] = counts.get(group_key, 0) + 1
    items = [
        ("Agent", "agent", False),
        ("MCP 服务", "mcp", False),
        ("命令行工具", "cli-tool", False),
        ("技能", "skill", False),
        ("项目", "project", False),
        ("配置", "config", False),
        ("运行时 / 支撑", "support", False),
        ("⚠ 待标记", "unsorted", True),
    ]
    chips = []
    for label, key, warn in items:
        n = counts.get(key, 0)
        if n <= 0:
            continue
        cls = "asset-chip asset-chip-warn js-jump" if warn else "asset-chip js-jump"
        chips.append(f'<a class="{cls}" href="#asset-group-{key}"><b>{n}</b><span>{lib.h(label)}</span></a>')
    return "".join(chips)


def render_unsorted_block(agent_registry):
    items = [(aid, a) for aid, a in sorted(agent_registry.get("assets", {}).items()) if "unsorted" in set(lib.listify(a.get("category")))]
    if not items:
        return ""
    chips = "".join(f'<a class="tag-pending js-jump" href="#asset-group-unsorted">{lib.h(aid)}</a>' for aid, _a in items)
    return f'''
        <div class="pending-block">
          <h2>⚠ 待标记资产（{len(items)}）</h2>
          <p class="pending-hint">已登记但没归到主类型，等你拍板。点名字跳到「⚠ 待标记」分区去标记。</p>
          <div class="pending-tags">{chips}</div>
        </div>
'''


def render_crosscheck_block(signals_rows, signals_meta):
    rows = signals_rows or []
    meta = signals_meta or {}
    if not meta and not rows:
        return ""
    residual = [r for r in rows if "residual-candidate" in lib.listify(r.get("tags"))]
    launch = meta.get("launch_plists", 0)
    running = meta.get("running", 0)
    listening = meta.get("listening", 0)
    linked = meta.get("linked", 0)
    chips = "".join(
        f'<a class="tag-cross js-jump" href="#signals">{lib.h(r.get("label") or r.get("name") or r.get("identifier") or "?")}</a>'
        for r in residual[:12]
    )
    more = f'<span class="pending-hint">还有 {len(residual) - 12} 个，见系统信号 tab</span>' if len(residual) > 12 else ""
    summary_line = f"{launch} launchd · {running} 跑着 · {listening} 监听端口 · {linked} 已关联资产"
    return f'''
        <div class="crosscheck-block">
          <h2>⚡ 系统信号交叉验证（{summary_line}）</h2>
          <p class="pending-hint">{len(residual)} 个系统痕迹没登记进总账（residual），可能是漏网资产。点名字跳系统信号 tab。</p>
          <div class="pending-tags">{chips}{more}</div>
        </div>
'''


def render_asset_card(asset_id, asset):
    categories = ", ".join(asset.get("category", [])) or "未分类"
    group_key, _group_label = asset_group(asset)
    filter_tags = " ".join([group_key] + lib.listify(asset.get("category")))
    refs = []
    for key in ("stable_entrypoints", "mcp_urls", "config_paths", "data_paths", "source_paths", "project_paths", "skill_roots", "registries"):
        values = lib.listify(asset.get(key))
        if values:
            refs.append(f'<div class="asset-row"><strong>{lib.h(key)}</strong><div>{render_chips(values)}</div></div>')
    status = asset.get("status") or ""
    return f"""
    <article class="asset-card searchable" data-section="assets" data-filter-tags="{lib.h(filter_tags)}" data-text="{lib.h(asset_id)} {lib.h(categories)} {lib.h(json.dumps(asset, ensure_ascii=False))}">
      <div class="asset-head">
        <div>
          <h3>{lib.h(asset_id)}</h3>
          <p>{lib.h(categories)}</p>
        </div>
        <span class="badge">{lib.h(asset.get("category", ["资产"])[0]) if asset.get("category") else "资产"}</span>
      </div>
      {'<p class="status-text">' + lib.h(status) + '</p>' if status else ''}
      <div class="asset-refs">
        {''.join(refs)}
      </div>
    </article>
    """


def state_badge(state, label=None):
    state_labels = {
        "registered": "已登记",
        "connected": "已连接",
        "failed": "失败",
        "unknown": "未知",
        "internal": "内部",
        "exec": "可执行",
        "file": "文件",
        "dir": "目录",
        "file-ref": "文件引用",
        "ref": "引用",
        "missing": "缺失",
        "broken-link": "坏链",
        "new": "待处理",
        "defer": "稍后处理",
        "ignore": "已忽略",
        "app": "应用",
        "mcp-wrapper": "MCP 包装器",
        "agent-command": "Agent 命令",
        "dashboard": "面板",
        "runtime": "运行时",
        "cli": "CLI",
        "canonical": "标准项目",
        "legacy": "旧位置",
        "download_candidate": "下载候选",
        "host_managed": "宿主管理",
        "registered_source": "已登记源码",
        "manual": "手动根目录",
        "linked": "已关联资产",
        "git-repo": "Git 仓库",
        "node-package": "Node 包",
        "python-package": "Python 包",
        "go-module": "Go 模块",
        "rust-package": "Rust 包",
        "skill": "Skill",
        "mcp-candidate": "MCP 候选",
        "cli-candidate": "CLI 候选",
        "documentation": "文档项目",
        "enabled": "已启用",
        "disabled": "已关闭",
        "running": "运行中",
        "not-running": "未运行",
        "listening": "监听端口",
        "privileged": "高权限",
        "attention": "需关注",
        "residual-candidate": "残留候选",
        "launch-agent": "LaunchAgent",
        "launch-daemon": "LaunchDaemon",
        "global-agent": "全局 Agent",
        "remote-control": "远控类",
        "network-proxy": "代理/网络",
        "agent-service": "Agent 服务",
        "updater": "更新器",
        "input-method": "输入法",
        "error": "异常",
        "confirmed": "已确认",
        "residual": "残留",
        "not-agent": "非 Agent",
    }
    raw_text = label or state
    text = state_labels.get(raw_text, state_labels.get(state, raw_text))
    normalized = state.replace("_", "-")
    return f'<span class="state state-{lib.h(normalized)}">{lib.h(text)}</span>'


def render_project_filters(project_rows):
    counts = {}
    for row in project_rows:
        role = row.get("root_role", "")
        if role:
            counts[role] = counts.get(role, 0) + 1
        if row.get("linked_assets"):
            counts["linked"] = counts.get("linked", 0) + 1
        for kind in lib.listify(row.get("kind")):
            counts[kind] = counts.get(kind, 0) + 1
    return render_filter_bar("projects", [
        ("标准项目", "canonical", counts.get("canonical", 0)),
        ("旧位置", "legacy", counts.get("legacy", 0)),
        ("下载候选", "download_candidate", counts.get("download_candidate", 0)),
        ("宿主管理", "host_managed", counts.get("host_managed", 0)),
        ("已关联", "linked", counts.get("linked", 0)),
        ("Git 仓库", "git-repo", counts.get("git-repo", 0)),
        ("CLI 候选", "cli-candidate", counts.get("cli-candidate", 0)),
        ("MCP 候选", "mcp-candidate", counts.get("mcp-candidate", 0)),
    ])


def render_kind_badges(kinds):
    values = lib.listify(kinds)
    if not values:
        return '<span class="muted">未识别</span>'
    return " ".join(state_badge(value) for value in values[:5])


def render_project_rows(rows):
    if not rows:
        return '<tr><td colspan="6" class="muted">还没有项目索引。点击“刷新项目索引”生成第一版。</td></tr>'
    out = []
    for row in rows:
        role = row.get("root_role") or "legacy"
        linked = lib.listify(row.get("linked_assets"))
        status = "linked" if linked else role
        kinds = lib.listify(row.get("kind"))
        signals = lib.listify(row.get("signals"))
        entries = lib.listify(row.get("entrypoint_candidates"))
        filter_tags = " ".join([role, status] + kinds + signals)
        remote = row.get("git_remote") or ""
        signal_text = ", ".join(signals[:8]) if signals else "无"
        if len(signals) > 8:
            signal_text += f" +{len(signals) - 8}"
        out.append(f"""
        <tr class="searchable" data-section="projects" data-filter-tags="{lib.h(filter_tags)}" data-text="{lib.h(json.dumps(row, ensure_ascii=False))}">
          <td><strong>{lib.h(row.get("name", ""))}</strong><span class="subtle">{render_kind_badges(kinds)}</span></td>
          <td>{lib.chip(row.get("path", ""))}<span class="subtle">{lib.h(remote) if remote else "无 remote"}</span></td>
          <td>{state_badge(status)}</td>
          <td><span class="subtle">信号：{lib.h(signal_text)}</span><div>{render_chips(entries) if entries else '<span class="muted">无入口候选</span>'}</div></td>
          <td>{render_chips(linked) if linked else '<span class="muted">未关联</span>'}</td>
          <td class="note-cell">{lib.h(row.get("action_hint") or "")}</td>
        </tr>
        """)
    return "\n".join(out)


def render_mcp_rows(rows):
    out = []
    for row in rows:
        out.append(f"""
        <tr class="searchable" data-section="mcp" data-filter-tags="{lib.h(row["state"])} {lib.h(row["kind"])}" data-text="{lib.h(json.dumps(row, ensure_ascii=False))}">
          <td><strong>{lib.h(row["name"])}</strong><span class="subtle">{lib.h(row["kind"])}</span></td>
          <td>{lib.chip(row["entry"])}</td>
          <td>{state_badge(row["state"], row["health"])}</td>
          <td>{render_chips(row["hosts"])}</td>
          <td class="note-cell">{lib.h(row["note"])}</td>
        </tr>
        """)
    return "\n".join(out)


def render_entrypoint_rows(rows):
    out = []
    for row in rows:
        owner_text = ", ".join(row["owners"]) if row["owners"] else "未登记归属"
        out.append(f"""
        <tr class="searchable" data-section="entrypoints" data-filter-tags="{lib.h(row["kind"])} {lib.h(row["state"])}" data-text="{lib.h(row["path"])} {lib.h(owner_text)} {lib.h(row["state"])} {lib.h(row["kind"])}">
          <td>{lib.chip(row["path"])}</td>
          <td>{state_badge(row["kind"])}</td>
          <td>{state_badge(row["state"])}</td>
          <td>{lib.h(owner_text)}</td>
        </tr>
        """)
    return "\n".join(out)


def render_config_rows(agent_registry):
    configs = []
    configs.append(("start file", str(paths.START_FILE)))
    for key, value in agent_registry.get("policy", {}).items():
        if isinstance(value, str) and value.startswith("/"):
            configs.append((key, value))
    for key, value in agent_registry.get("indexes", {}).get("host_configs", {}).items():
        configs.append((key, value))
    out = []
    seen = set()
    for label, value in configs:
        if value in seen:
            continue
        seen.add(value)
        out.append(f"""
        <tr class="searchable" data-section="config" data-filter-tags="{lib.h(lib.path_state(value))}" data-text="{lib.h(label)} {lib.h(value)}">
          <td><strong>{lib.h(label)}</strong></td>
          <td>{lib.chip(value)}</td>
          <td>{state_badge(lib.path_state(value))}</td>
        </tr>
        """)
    return "\n".join(out)


def match_product(row):
    """按 identifier/name/label/developer 匹配厂商，返回 (中文名, 说明) 或 (None, None)。"""
    hay = " ".join(str(row.get(k) or "") for k in ("identifier", "name", "label", "developer", "id")).lower()
    for key, name, note in PRODUCT_MAP:
        if key in hay:
            return name, note
    return None, None


def humanize_signal(row):
    """返回 (人话标题, 说明)。匹配不到时用原名 + 开发者，并标'未识别'。"""
    name, note = match_product(row)
    raw_name = row.get("name") or row.get("label") or row.get("identifier") or "未命名"
    developer = (row.get("developer") or "").strip()
    if name:
        return name, (note or "")
    developer_hint = f"开发者：{developer}" if developer and developer.lower() != str(raw_name).lower() else "未识别·待你确认"
    return raw_name, (note or developer_hint)


def is_safe_to_control(row):
    """用户级（~/Library/LaunchAgents）和全局用户级（/Library/LaunchAgents）允许前端开关。

    系统守护目录（/Library/LaunchDaemons）需 sudo，前端不直接操作。
    """
    plist = row.get("launch_plist") or ""
    if not plist:
        return False
    home_agents = str(pathlib.Path.home() / "Library" / "LaunchAgents")
    global_agents = "/Library/LaunchAgents"
    role = row.get("launch_role")
    if role == "user-agent" and plist.startswith(home_agents + "/"):
        return True
    if role == "global-agent" and plist.startswith(global_agents + "/"):
        return True
    return False


def signal_control_key(row):
    """可控性分组键：user-launchd(可开关) / system-launchd(系统级) / app-running(在跑) / login-item(登录项)。"""
    plist = row.get("launch_plist") or ""
    if plist:
        role = row.get("launch_role")
        return "user-launchd" if role in {"user-agent", "global-agent"} else "system-launchd"
    if row.get("listeners") or row.get("running"):
        return "app-running"
    return "login-item"


def control_badge(key):
    icon, label, _ = CONTROL_META.get(key, ("❔", key, ""))
    return f'<span class="ctrl-badge ctrl-{key}">{icon} {lib.h(label)}</span>'


def _launchctl_disabled_set():
    """一次性查 launchctl 里被 disable 的用户级 service label 集合，用于回显'开机自启'状态。失败/超时返回空集。"""
    try:
        proc = subprocess.run(
            ["launchctl", "print-disabled", f"gui/{os.getuid()}"],
            capture_output=True, text=True, timeout=6,
        )
        if proc.returncode != 0:
            return set()
        disabled = set()
        for line in proc.stdout.splitlines():
            s = line.strip()
            if not s or s.lower().startswith("disabled"):
                continue
            low = s.lower()
            if "(true)" in s or "=> disabled" in low or low.endswith("disabled"):
                lbl = s.split("\t")[0].split("=>")[0].split()[0].strip().strip("\"'")
                if lbl and "." in lbl:
                    disabled.add(lbl)
        return disabled
    except Exception:
        return set()


def _signal_row_html(row, disabled):
    title, note = row.get("_human") or humanize_signal(row)
    raw_label = row.get("label") or row.get("name") or row.get("identifier") or "未命名"
    kind = row.get("_signal_kind") or "其他"
    plist = row.get("launch_plist") or ""
    safe = row.get("_safe")
    control = row.get("_control") or "login-item"
    linked = lib.listify(row.get("linked_assets"))
    tags = lib.listify(row.get("tags"))
    if row.get("launch_state") == "running" or row.get("running"):
        state, state_label = "running", "运行中"
    elif plist:
        state, state_label = "not-running", "未运行"
    else:
        state, state_label = "registered", "已登记"
    listeners = row.get("listeners") or []
    if listeners:
        port_text = ", ".join(str(l.get("name", "")) for l in listeners[:3])
        if len(listeners) > 3:
            port_text += f" +{len(listeners) - 3}"
    else:
        port_text = "—"
    exit_code = row.get("launch_last_exit_code")
    exit_text = "" if exit_code in (None, "", "(never exited)") else f" · exit {exit_code}"
    filter_tags = " ".join([state, control] + tags)
    # 操作区：仅用户级 LaunchAgent 且 plist 真实存在才给开关；其余只读提示
    actions = ""
    if safe and plist:
        cmd_label = row.get("label") or raw_label
        is_auto_disabled = cmd_label in disabled
        if state == "running":
            run_btn = f'<button class="table-action js-launchctl" title="立即停止该 LaunchAgent" data-plist="{lib.h(plist)}" data-label="{lib.h(cmd_label)}" data-action="bootout">⏸ 停止</button>'
        else:
            run_btn = f'<button class="table-action js-launchctl" title="立即启动该 LaunchAgent" data-plist="{lib.h(plist)}" data-label="{lib.h(cmd_label)}" data-action="bootstrap">▶ 启动</button>'
        if is_auto_disabled:
            auto_state = '<span class="auto-state off" title="当前不会随用户登录自动启动">自启·已禁用</span>'
            auto_btn = f'<button class="table-action js-launchctl" title="允许该 LaunchAgent 随用户登录自动启动" data-plist="{lib.h(plist)}" data-label="{lib.h(cmd_label)}" data-action="enable">开机启用</button>'
        else:
            auto_state = '<span class="auto-state on" title="当前会随用户登录自动启动">自启·已启用</span>'
            auto_btn = f'<button class="table-action js-launchctl" title="禁止该 LaunchAgent 随用户登录自动启动" data-plist="{lib.h(plist)}" data-label="{lib.h(cmd_label)}" data-action="disable">禁用自启</button>'
        actions = f'<div class="action-stack">{run_btn}{auto_btn}{auto_state}</div>'
    elif control == "user-launchd" and not safe:
        # plist 被删除或不在用户级目录：明确告诉用户为什么不能操作，同时保留当前真实状态
        home_agents = str(pathlib.Path.home() / "Library" / "LaunchAgents")
        if plist and not plist.startswith(home_agents + "/"):
            actions = '<span class="muted" title="plist 不在 ~/Library/LaunchAgents，前端无法开关">不在用户目录 · 不可操作</span>'
        elif plist and not os.path.isfile(plist):
            state_hint = "进程可能还在跑，但重启后无法自启" if state == "running" else "服务未运行且 plist 已丢失"
            actions = f'<span class="muted" title="{lib.h(state_hint)}">plist 已删除 · 不可操作</span>'
        else:
            actions = '<span class="muted">不可操作</span>'
    elif control == "system-launchd":
        actions = '<span class="muted" title="位于 /Library/LaunchDaemons，需用 sudo 在终端执行 launchctl">系统守护 · 需 sudo</span>'
    elif control == "login-item":
        actions = '<span class="muted">系统设置管理</span>'
    else:
        actions = '<span class="muted">—</span>'
    name_cell = f'<div><strong>{lib.h(title)}</strong></div>'
    if str(title) != str(raw_label):
        name_cell += f'<div class="subtle">{lib.h(raw_label)}</div>'
    if plist:
        name_cell += f'<div class="subtle plist-path">{lib.h(plist)}</div>'
    if note:
        name_cell += f'<div class="subtle">{lib.h(note)}</div>'
    return f"""
    <tr class="searchable" data-section="signals" data-control="{lib.h(control)}" data-filter-tags="{lib.h(filter_tags)}" data-text="{lib.h(raw_label)} {lib.h(title)} {lib.h(kind)} {lib.h(json.dumps(row, ensure_ascii=False))}">
      <td>{name_cell}</td>
      <td>{lib.h(kind)}</td>
      <td>{state_badge(state, state_label)}<span class="subtle">{lib.h(exit_text)}</span></td>
      <td><span class="subtle">{lib.h(port_text)}</span></td>
      <td>{render_chips(linked) if linked else '<span class="muted">未关联</span>'}</td>
      <td class="action-cell">{actions}</td>
    </tr>
    """


def render_macos_signals_rows(rows):
    if not rows:
        return '<p class="muted">还没有系统信号。运行 asset-macos-signals 生成。</p>'
    groups = {"user-launchd": [], "system-launchd": [], "app-running": [], "login-item": []}
    for row in rows:
        groups.setdefault(row.get("_control") or "login-item", []).append(row)
    for key in groups:
        groups[key].sort(key=lambda r: (
            0 if lib.listify(r.get("linked_assets")) else 1,
            (r.get("_human") or ("", ""))[0],
        ))
    disabled = _launchctl_disabled_set()

    # 横向筛选栏：按可控性分组
    control_buttons = [f'<button class="filter active" data-filter="">全部 ({len(rows)})</button>']
    for key in ["user-launchd", "system-launchd", "app-running", "login-item"]:
        grp = groups.get(key) or []
        if grp:
            icon, label, _ = CONTROL_META[key]
            control_buttons.append(f'<button class="filter" data-filter="{lib.h(key)}">{icon} {lib.h(label)} ({len(grp)})</button>')

    # 状态筛选
    state_counts = {}
    for row in rows:
        if row.get("launch_state") == "running" or row.get("running"):
            state_counts["running"] = state_counts.get("running", 0) + 1
        elif row.get("launch_plist"):
            state_counts["not-running"] = state_counts.get("not-running", 0) + 1
        else:
            state_counts["registered"] = state_counts.get("registered", 0) + 1
    state_buttons = [
        f'<button class="filter active" data-state-filter="">全部状态</button>',
        f'<button class="filter" data-state-filter="running">运行中 ({state_counts.get("running", 0)})</button>',
        f'<button class="filter" data-state-filter="not-running">未运行 ({state_counts.get("not-running", 0)})</button>',
        f'<button class="filter" data-state-filter="registered">已登记 ({state_counts.get("registered", 0)})</button>',
    ]

    parts = [
        f'<div class="filter-bar signals-filter-bar">{"".join(control_buttons)}</div>',
        f'<div class="filter-bar signals-state-filter-bar">{"".join(state_buttons)}</div>',
    ]
    for key in ["user-launchd", "system-launchd", "app-running", "login-item"]:
        grp = groups.get(key) or []
        if not grp:
            continue
        icon, label, note = CONTROL_META[key]
        parts.append(f"""
        <table class="signal-table" data-control="{lib.h(key)}">
          <caption><span class="ctrl-icon">{icon}</span> <strong>{lib.h(label)}</strong> <span class="muted">({len(grp)})</span><span class="subtle"> — {lib.h(note)}</span></caption>
          <thead><tr><th>名称</th><th>类型</th><th>状态</th><th>端口</th><th>关联</th><th class="action-cell">操作</th></tr></thead>
          <tbody>
        """)
        for row in grp:
            parts.append(_signal_row_html(row, disabled))
        parts.append("</tbody></table>")
    return "\n".join(parts)


def _runtime_cmd_short(cmd, limit=90):
    cmd = (cmd or "").strip()
    if len(cmd) <= limit:
        return cmd
    return cmd[: limit - 1] + "…"


def _aggregate_runtime_by_fp(processes):
    """按 fingerprint 聚合进程。返回 [{fp, category, pids, ports, cmd, cwds}]。"""
    groups = {}
    for p in processes:
        fp = p.get("fp") or p.get("cmd") or "?"
        g = groups.setdefault(
            fp,
            {
                "fp": fp,
                "category": p.get("category", "unknown"),
                "pids": [],
                "ports": set(),
                "cmd": p.get("cmd", ""),
                "cwds": set(),
            },
        )
        pid = p.get("pid")
        if pid and pid not in g["pids"]:
            g["pids"].append(pid)
        for port in lib.listify(p.get("ports")):
            g["ports"].add(port)
        if p.get("cwd"):
            g["cwds"].add(p["cwd"])
    for g in groups.values():
        g["pids"].sort(key=lambda x: int(x) if str(x).isdigit() else 0)
        g["ports"] = sorted(g["ports"])
        g["cwds"] = sorted(g["cwds"])
    return sorted(groups.values(), key=lambda g: (-len(g["pids"]), g["fp"]))


def _runtime_type_badge(category):
    mapping = {
        "mcp": ("MCP", "mcp"),
        "agent-daemon": ("Agent", "agent"),
        "dev-server": ("Dev", "dev"),
        "support": ("Support", "support"),
        "system": ("System", "system"),
    }
    label, cls = mapping.get(category, ("Other", "other"))
    return f'<span class="tag {cls}">{lib.h(label)}</span>'


def _cwd_badge(cwd):
    if not cwd or cwd == "/":
        return ""
    href = "file://" + urllib.parse.quote(str(cwd))
    return f'<a class="chip cwd-chip" href="{lib.h(href)}">{lib.h(cwd)}</a>'


def _runtime_table_row(pid_or_count, type_badge, ports, cmd, cwd, pids_for_kill, cmd_short, filter_tags=""):
    ports_html = ", ".join(ports) if ports else '<span class="muted">—</span>'
    cwd_html = _cwd_badge(cwd)
    kill_btns = _kill_buttons_for_pids(pids_for_kill, cmd_short) if pids_for_kill else ""
    return (
        f'<tr class="searchable" data-section="runtime" data-filter-tags="{lib.h(filter_tags)}">'
        f'<td class="col-pid">{pid_or_count}</td>'
        f'<td class="col-type">{type_badge}</td>'
        f'<td class="col-ports">{ports_html}</td>'
        f'<td class="col-cmd"><code>{lib.h(cmd_short)}</code>{cwd_html}</td>'
        f'<td class="col-action">{kill_btns}</td>'
        f'</tr>'
    )


def _kill_buttons_for_pids(pids, cmd_short):
    if not pids:
        return ""
    if len(pids) == 1:
        pid = pids[0]
        return (
            f'<div class="action-cell">'
            f'<button class="table-action js-kill-process" title="优雅终止 (SIGTERM)，给进程清理机会" data-pid="{lib.h(pid)}" data-cmd="{lib.h(cmd_short)}" data-mode="term">终止</button>'
            f'<button class="table-action js-kill-process danger" title="强制终止 (SIGKILL)，立即结束，无法拦截" data-pid="{lib.h(pid)}" data-cmd="{lib.h(cmd_short)}" data-mode="kill">强制</button>'
            f'</div>'
        )
    # Multi-instance: one "terminate all" / "force all" button that sends all pids.
    pids_json = lib.h(str(list(pids)).replace("'", '"'))
    return (
        f'<div class="action-cell">'
        f'<button class="table-action js-kill-process" title="优雅终止 (SIGTERM)" data-pid="{pids_json}" data-cmd="{lib.h(cmd_short)}" data-mode="term">全部终止</button>'
        f'<button class="table-action js-kill-process danger" title="强制终止 (SIGKILL)" data-pid="{pids_json}" data-cmd="{lib.h(cmd_short)}" data-mode="kill">全部强制</button>'
        f'</div>'
    )


def render_runtime_rows(data):
    """渲染 asset-runtime 报告：统一 5 列表格（PID/实例、类型、端口、命令/路径、操作）。"""
    if not data:
        return '<p class="muted">运行态盲区数据为空。</p>'
    if data.get("_error"):
        hint = f'<p class="subtle">{lib.h(data.get("_hint") or "")}</p>' if data.get("_hint") else ""
        return f'<p class="muted">运行态盲区采集失败：{lib.h(data["_error"])}</p>{hint}'

    processes = data.get("processes") or []
    leaks = data.get("leaks") or []
    ports = data.get("ports") or {}
    threshold = data.get("leak_threshold", 3)
    summary = data.get("summary") or {}

    parts = []

    # summary 行
    bits = []
    for key, label in (("leak", "泄漏"), ("zombie", "僵尸 dev server"), ("daemon", "常驻 daemon"), ("mcp", "MCP"), ("dev", "dev server")):
        val = summary.get(key)
        if val:
            bits.append(f"<strong>{val}</strong> {label}")
    if bits:
        parts.append(f'<p class="metric-line">{" · ".join(bits)}　·　泄漏阈值：同指纹 ≥ {lib.h(threshold)} 个</p>')

    table_head = """
    <table class="runtime-table">
      <thead>
        <tr>
          <th class="col-pid">PID / 实例</th>
          <th class="col-type">类型</th>
          <th class="col-ports">端口</th>
          <th class="col-cmd">命令 / 路径</th>
          <th class="col-action">操作</th>
        </tr>
      </thead>
      <tbody>
    """

    # 泄漏组
    if leaks:
        parts.append(f"""
        <details class="runtime-group" open>
          <summary class="runtime-group-title">
            <span>⚠️</span>
            <strong>泄漏</strong>
            <span class="muted">({len(leaks)})</span>
            <span class="subtle">— 同一指纹出现多次</span>
          </summary>
          {table_head}
        """)
        for row in leaks:
            fp = row.get("fingerprint") or "?"
            count = row.get("count", 0)
            matching = [p for p in processes if p.get("fp") == fp]
            pids = sorted([p.get("pid") for p in matching if p.get("pid")], key=lambda x: int(x) if str(x).isdigit() else 0)
            cat = matching[0].get("category", "unknown") if matching else "unknown"
            ports_set = set()
            cwds = set()
            for p in matching:
                ports_set.update(lib.listify(p.get("ports")))
                if p.get("cwd"):
                    cwds.add(p["cwd"])
            pid_list_text = ", ".join(str(x) for x in pids)
            if len(pids) == 1:
                pid_html = f'<code>{lib.h(pids[0])}</code>'
            else:
                pid_html = f'<strong title="PID: {lib.h(pid_list_text)}">{count}×</strong>'
            type_badge = _runtime_type_badge(cat)
            cmd_short = _runtime_cmd_short(fp)
            cwd = sorted(cwds)[0] if cwds else ""
            parts.append(_runtime_table_row(pid_html, type_badge, sorted(ports_set), fp, cwd, pids, cmd_short, filter_tags=f"{cat} leak"))
        parts.append("</tbody></table></details>")

    # 僵尸 dev server 组
    zombie_rows = [p for p in processes if p.get("severity") == "zombie"]
    if zombie_rows:
        parts.append(f"""
        <details class="runtime-group" open>
          <summary class="runtime-group-title">
            <span>🧟</span>
            <strong>僵尸 Dev server</strong>
            <span class="muted">({len(zombie_rows)})</span>
            <span class="subtle">— serve / 监听类 dev server 还挂着</span>
          </summary>
          {table_head}
        """)
        for p in sorted(zombie_rows, key=lambda r: r.get("pid", "")):
            pid = p.get("pid", "?")
            cat = p.get("category", "unknown")
            cmd_short = _runtime_cmd_short(p.get("cmd", ""))
            parts.append(_runtime_table_row(
                f'<code>{lib.h(pid)}</code>',
                _runtime_type_badge(cat),
                lib.listify(p.get("ports")),
                p.get("cmd", ""),
                p.get("cwd", ""),
                [pid],
                cmd_short,
                filter_tags="dev-server zombie",
            ))
        parts.append("</tbody></table></details>")

    # 按 category 分组
    non_alert = [p for p in processes if p.get("severity") not in ("leak", "zombie")]
    by_cat = {}
    for p in non_alert:
        by_cat.setdefault(p.get("category", "unknown"), []).append(p)

    group_titles = {
        "mcp": ("🤖", "MCP Servers", "被 Agent host 调用的 MCP server 进程"),
        "agent-daemon": ("🤖", "Agent Daemons", "Agent 框架自己的常驻 gateway / hub / watcher / browser daemon"),
        "dev-server": ("🌐", "Dev Servers", "vite / next / webpack 等开发预览服务器"),
        "support": ("⚙️", "Support / Runtime", "支撑运行时，如当前 dashboard 自己"),
        "system": ("🔒", "System", "系统级 daemon / 服务"),
        "unknown": ("❓", "Other / Unclassified", "没被规则归到上面的进程"),
    }

    for cat, (icon, label, note) in group_titles.items():
        grp = by_cat.get(cat)
        if not grp:
            continue
        aggregated = _aggregate_runtime_by_fp(grp)
        parts.append(f"""
        <details class="runtime-group" open>
          <summary class="runtime-group-title">
            <span>{icon}</span>
            <strong>{lib.h(label)}</strong>
            <span class="muted">({len(grp)})</span>
            <span class="subtle">— {lib.h(note)}</span>
          </summary>
          {table_head}
        """)
        for g in aggregated:
            cmd_short = _runtime_cmd_short(g["cmd"])
            fp_short = _runtime_cmd_short(g["fp"])
            cwd = g["cwds"][0] if g["cwds"] else ""
            pid_list_text = ", ".join(str(x) for x in g["pids"])
            if len(g["pids"]) > 1:
                pid_html = f'<strong title="PID: {lib.h(pid_list_text)}">{len(g["pids"])}×</strong>'
                display_cmd = fp_short
                pids_for_kill = g["pids"]
            else:
                pid_html = f'<code>{lib.h(g["pids"][0] if g["pids"] else "?")}</code>'
                display_cmd = cmd_short
                pids_for_kill = g["pids"]
            parts.append(_runtime_table_row(
                pid_html,
                _runtime_type_badge(cat),
                g["ports"],
                g["cmd"],
                cwd,
                pids_for_kill,
                display_cmd,
                filter_tags=cat,
            ))
        parts.append("</tbody></table></details>")

    # 端口占用组
    if ports:
        port_rows = sorted(ports.items())
        parts.append(f"""
        <details class="runtime-group" open>
          <summary class="runtime-group-title">
            <span>🔌</span>
            <strong>端口占用</strong>
            <span class="muted">({len(port_rows)})</span>
          </summary>
          <div class="ports-bar">
        """)
        for port_key, pid_list in port_rows:
            pids = lib.listify(pid_list)
            parts.append(f'<span class="port" title="PID: {lib.h(", ".join(str(x) for x in pids))}">{lib.h(port_key)}</span>')
        parts.append("</div></details>")

    if len(parts) <= 1:
        parts.append('<p class="muted">当前没有运行态数据。</p>')
    return "\n".join(parts)


def render_discovered_rows(rows, empty_label="没有匹配的候选项。"):
    out = []
    for row in rows:
        cats = ", ".join(row.get("categories", []))
        owners = ", ".join(row.get("owners", [])) or "unregistered"
        state = "registered" if row.get("registered") else row.get("review_status", "new")
        version = row.get("version") or ""
        actions = []
        if not row.get("registered"):
            path_value = lib.h(row.get("path", ""))
            if state != "defer":
                actions.append(f'<button class="table-action js-review" data-path="{path_value}" data-status="defer">稍后</button>')
            if state != "ignore":
                actions.append(f'<button class="table-action js-review" data-path="{path_value}" data-status="ignore">忽略</button>')
            if state in {"defer", "ignore"}:
                actions.append(f'<button class="table-action js-review" data-path="{path_value}" data-status="new">恢复待处理</button>')
        review_bits = [state_badge(state)]
        if row.get("review_action"):
            review_bits.append(f'<span class="subtle">{lib.h(row.get("review_action"))}</span>')
        if row.get("review_note"):
            review_bits.append(f'<span class="subtle">{lib.h(row.get("review_note"))}</span>')
        filter_tags = " ".join([state] + lib.listify(row.get("categories")))
        out.append(f"""
        <tr class="searchable" data-section="discovered" data-filter-tags="{lib.h(filter_tags)}" data-text="{lib.h(json.dumps(row, ensure_ascii=False))}">
          <td><strong>{lib.h(row.get("name", ""))}</strong><span class="subtle">{lib.h(cats)}</span></td>
          <td>{lib.chip(row.get("path", ""))}<span class="subtle">{lib.h(row.get("package_hint") or "")}</span></td>
          <td>{state_badge(state)}<span class="subtle">{lib.h(owners)}</span></td>
          <td>{''.join(review_bits)}</td>
          <td>{lib.h(version)}</td>
          <td class="action-cell">{''.join(actions) if actions else '<span class="muted">已入账</span>'}</td>
        </tr>
        """)
    if out:
        return "\n".join(out)
    return f'<tr><td colspan="6" class="muted">{lib.h(empty_label)}</td></tr>'


def discovered_table(rows, empty_label):
    return f"""
        <table>
          <thead><tr><th>名称</th><th>路径</th><th>登记状态</th><th>处理状态</th><th>版本</th><th>动作</th></tr></thead>
          <tbody>{render_discovered_rows(rows, empty_label)}</tbody>
        </table>
    """


def render_mcp_audit_rows(rows, empty_label, include_action=False):
    if not rows:
        colspan = 6 if include_action else 5
        return f'<tr><td colspan="{colspan}" class="muted">{lib.h(empty_label)}</td></tr>'
    out = []
    for row in rows:
        action = '<span class="muted">无</span>'
        if include_action:
            action = f'<button class="table-action primary js-register-mcp" data-location="{lib.h(row["location"])}">纳入总账</button>'
        out.append(f"""
        <tr class="searchable" data-section="mcp" data-filter-tags="{lib.h(row.get("state", "unknown"))} {lib.h(row.get("transport") or row.get("kind") or "")} {lib.h("host-only" if include_action else "registry-only")}" data-text="{lib.h(json.dumps(row, ensure_ascii=False))}">
          <td><strong>{lib.h(row.get("name", ""))}</strong><span class="subtle">{lib.h(row.get("host") or row.get("kind") or "")}</span></td>
          <td>{state_badge(row.get("state", "unknown"), row.get("health"))}</td>
          <td>{lib.chip(row.get("entry") or row.get("location") or "")}</td>
          <td>{lib.h(row.get("transport") or row.get("kind") or "")}</td>
          <td class="note-cell">{lib.h(row.get("location") or "")}</td>
          {f'<td class="action-cell">{action}</td>' if include_action else ''}
        </tr>
        """)
    return "\n".join(out)


def audit_table(rows, empty_label, include_action=False):
    action_head = "<th>动作</th>" if include_action else ""
    return f"""
        <table>
          <thead><tr><th>名称</th><th>状态</th><th>入口 / URL</th><th>类型</th><th>来源</th>{action_head}</tr></thead>
          <tbody>{render_mcp_audit_rows(rows, empty_label, include_action=include_action)}</tbody>
        </table>
    """


def render_mcp_filters(mcp_rows, mcp_audit):
    counts = {}
    for row in mcp_rows:
        for key in (row["state"], row["kind"]):
            counts[key] = counts.get(key, 0) + 1
    counts["host-only"] = len(mcp_audit["host_only"])
    counts["registry-only"] = len(mcp_audit["registry_only"])
    return render_filter_bar("mcp", [
        ("已连接", "connected", counts.get("connected", 0)),
        ("失败", "failed", counts.get("failed", 0)),
        ("stdio", "stdio", counts.get("stdio", 0)),
        ("HTTP", "http", counts.get("http", 0)),
        ("宿主未入账", "host-only", counts.get("host-only", 0)),
        ("总账孤立", "registry-only", counts.get("registry-only", 0)),
    ])


def render_entrypoint_filters(entrypoints):
    counts = {}
    for row in entrypoints:
        counts[row["kind"]] = counts.get(row["kind"], 0) + 1
        counts[row["state"]] = counts.get(row["state"], 0) + 1
    return render_filter_bar("entrypoints", [
        (label_for_state("app"), "app", counts.get("app", 0)),
        (label_for_state("mcp-wrapper"), "mcp-wrapper", counts.get("mcp-wrapper", 0)),
        (label_for_state("agent-command"), "agent-command", counts.get("agent-command", 0)),
        (label_for_state("dashboard"), "dashboard", counts.get("dashboard", 0)),
        (label_for_state("runtime"), "runtime", counts.get("runtime", 0)),
        (label_for_state("cli"), "cli", counts.get("cli", 0)),
        ("可用", "exec", counts.get("exec", 0) + counts.get("dir", 0) + counts.get("file", 0)),
        ("缺失", "missing", counts.get("missing", 0) + counts.get("broken-link", 0)),
    ])


def render_discovered_filters(discovered_rows):
    counts = {}
    for row in discovered_rows:
        state = "registered" if row.get("registered") else row.get("review_status", "new")
        counts[state] = counts.get(state, 0) + 1
        for category in lib.listify(row.get("categories")):
            counts[category] = counts.get(category, 0) + 1
    return render_filter_bar("discovered", [
        ("待处理", "new", counts.get("new", 0)),
        ("稍后", "defer", counts.get("defer", 0)),
        ("已忽略", "ignore", counts.get("ignore", 0)),
        ("已登记", "registered", counts.get("registered", 0)),
        ("CLI 候选", "cli-candidate", counts.get("cli-candidate", 0)),
        ("Agent 候选", "agent-candidate", counts.get("agent-candidate", 0)),
        ("MCP 包装器", "mcp-wrapper", counts.get("mcp-wrapper", 0)),
    ])


def render_config_filters(agent_registry):
    rows = [str(paths.START_FILE)]
    for key, value in agent_registry.get("policy", {}).items():
        if isinstance(value, str) and value.startswith("/"):
            rows.append(value)
    for value in agent_registry.get("indexes", {}).get("host_configs", {}).values():
        rows.append(value)
    counts = {}
    for value in rows:
        state = lib.path_state(value)
        counts[state] = counts.get(state, 0) + 1
    return render_filter_bar("config", [
        ("可用", "file", counts.get("file", 0) + counts.get("dir", 0) + counts.get("exec", 0) + counts.get("file-ref", 0)),
        ("缺失", "missing", counts.get("missing", 0) + counts.get("broken-link", 0)),
    ])


def _runtime_updated_at(runtime_data):
    if not runtime_data or runtime_data.get("_error"):
        return "未采集"
    return runtime_data.get("updated_at") or dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _runtime_summary(runtime_data):
    if not runtime_data or runtime_data.get("_error"):
        return {"leak": 0, "zombie": 0, "daemon": 0}
    s = runtime_data.get("summary", {})
    return {
        "leak": s.get("leak", 0),
        "zombie": s.get("zombie", 0),
        "daemon": s.get("daemon", 0),
    }


def render_alert_cards(runtime_data):
    summary = _runtime_summary(runtime_data)
    leak_ok = "ok" if summary["leak"] == 0 else ""
    zombie_ok = "ok" if summary["zombie"] == 0 else ""
    daemon_ok = "ok" if summary["daemon"] == 0 else ""
    return f"""
    <div class="card alert-card">
      <div class="card-title">需要关注</div>
      <div class="alert-grid">
        <div class="alert-item {leak_ok}"><b>{summary["leak"]}</b><span>泄漏（重复实例）</span></div>
        <div class="alert-item {zombie_ok}"><b>{summary["zombie"]}</b><span>僵尸 dev server</span></div>
        <div class="alert-item {daemon_ok}"><b>{summary["daemon"]}</b><span>异常 daemon</span></div>
      </div>
    </div>
    """


def render_runtime_filter_bar():
    return """
    <div class="filter-bar runtime-filter-bar">
      <button class="filter active" data-filter="">全部</button>
      <button class="filter" data-filter="mcp">MCP</button>
      <button class="filter" data-filter="agent-daemon">Agent</button>
      <button class="filter" data-filter="dev-server">Dev Server</button>
      <button class="filter" data-filter="support-system">支撑 / 系统</button>
      <button class="filter" data-filter="other">其他</button>
    </div>
    """


def render_cli_entrypoints(entrypoints):
    """已废弃：CLI 入口现在放在独立 tab 中展示，请使用 render_cli_section。"""
    return ""


def render_cli_section(entrypoints):
    """渲染 CLI 工具独立 tab：顶部横向筛选 + 单一大表格。

    不再用嵌套 details，用户直接点筛选按钮切换类别，一屏看完。
    对 kind=cli 的入口再按「是否在 ~/.local/bin 下」细分为 local_cli / other_cli。
    """
    if not entrypoints:
        return '<p class="muted">没有找到 CLI 入口。</p>'

    groups = {}
    for row in entrypoints:
        kind = row.get("kind", "other")
        if kind == "cli":
            path = str(row.get("path", ""))
            if path.startswith(str(lib.STABLE_BIN_DIR) + "/"):
                kind = "local_cli"
            else:
                kind = "other_cli"
        groups.setdefault(kind, []).append(row)

    order = [
        ("agent-command", "Agent 命令"),
        ("mcp-wrapper", "MCP 包装器"),
        ("local_cli", "本机 CLI 工具"),
        ("other_cli", "其他 CLI 入口"),
        ("runtime", "运行时 / 支撑"),
        ("dashboard", "控制台"),
        ("app", "应用入口"),
        ("other", "其他"),
    ]

    # 只渲染有数据的分组按钮
    filter_buttons = [f'<button class="filter active" data-filter="">全部 ({len(entrypoints)})</button>']
    for kind, label in order:
        rows = groups.get(kind, [])
        if rows:
            filter_buttons.append(f'<button class="filter" data-filter="{lib.h(kind)}">{lib.h(label)} ({len(rows)})</button>')

    all_rows = []
    for kind, _label in order:
        for row in groups.get(kind, []):
            all_rows.append((kind, row))

    body = _cli_entrypoint_rows(all_rows)
    return f"""
    <div class="filter-bar cli-filter-bar">
      {"".join(filter_buttons)}
    </div>
    <table class="data-table cli-table">
      <thead><tr><th>路径</th><th>类型</th><th>状态</th><th>归属</th></tr></thead>
      <tbody>{body}</tbody>
    </table>
    """


def _cli_entrypoint_rows(rows):
    out = []
    for kind, row in rows:
        owner_text = ", ".join(row.get("owners", [])) if row.get("owners") else "未登记归属"
        filter_tags = kind
        out.append(f"""
        <tr class="searchable" data-section="cli" data-filter-tags="{lib.h(filter_tags)}">
          <td>{lib.chip(row.get("path", ""))}</td>
          <td>{state_badge(kind)}</td>
          <td>{state_badge(row.get("state", "unknown"))}</td>
          <td>{lib.h(owner_text)}</td>
        </tr>
        """)
    return "\n".join(out)


def render_action_log():
    """渲染操作记录 tab：展示用户在 dashboard 上的 kill / launchctl 操作历史，并支持撤销 launchctl。

    设计意图：
    - 结果列只显示简短状态（成功/失败），避免技术性错误文案撑坏表格。
    - 失败原因默认折叠，用户需要时才展开看详情。
    - 提供清空记录按钮，方便用户清理过期或测试记录。
    """
    log = data.load_action_log()
    entries = log.get("entries", [])
    if not entries:
        return '<p class="muted">暂无操作记录。终止进程或开关 LaunchAgent 后会自动记录。</p>'

    launchctl_undo_map = {
        "bootstrap": "bootout",
        "bootout": "bootstrap",
        "enable": "disable",
        "disable": "enable",
    }

    rows = []
    for entry in entries[:50]:
        action = entry.get("action", "")
        mode = entry.get("mode", "")
        detail = entry.get("detail", "")
        result_text = str(entry.get("result", ""))
        # 判断成功/失败：后端成功时返回 "已..."，失败时包含「无法」「失败」「错误」等词
        lower_result = result_text.lower()
        is_ok = result_text.startswith("已") and not any(w in lower_result for w in ("失败", "错误", "无法"))
        if is_ok:
            status_badge = '<span class="log-status ok">成功</span>'
            detail_html = ""
        else:
            status_badge = '<span class="log-status err">失败</span>'
            # 失败原因折叠展示，避免撑坏表格
            detail_html = f'<details class="log-detail"><summary>查看原因</summary><pre>{lib.h(result_text)}</pre></details>'

        undo_btn = ""
        if action == "launchctl" and detail and mode in launchctl_undo_map:
            undo_action = launchctl_undo_map[mode]
            undo_label = {"bootout": "停止", "bootstrap": "启动", "enable": "启用自启", "disable": "禁用自启"}.get(undo_action, undo_action)
            undo_btn = f'<button class="table-action js-launchctl-undo" data-plist="{lib.h(detail)}" data-action="{lib.h(undo_action)}" data-original="{lib.h(mode)}">撤销：{lib.h(undo_label)}</button>'

        mode_label = mode
        if action == "launchctl":
            mode_label = {"bootstrap": "启动", "bootout": "停止", "enable": "启用自启", "disable": "禁用自启"}.get(mode, mode)
        elif action == "kill-process":
            mode_label = {"term": "优雅终止", "kill": "强制终止"}.get(mode, mode)

        rows.append(f"""
        <tr>
          <td class="col-time">{lib.h(entry.get("time", ""))}</td>
          <td class="col-action">{lib.h(action)}</td>
          <td class="col-target">{lib.h(entry.get("target", ""))}</td>
          <td class="col-mode">{lib.h(mode_label)}</td>
          <td class="col-result">{status_badge}{detail_html}</td>
          <td class="col-undo">{undo_btn}</td>
        </tr>
        """)
    return f"""
    <div class="card">
      <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
        <span>操作记录（最近 50 条）</span>
        <button class="table-action js-clear-action-log" title="清空所有操作记录">清空记录</button>
      </div>
      <table class="data-table action-log-table">
        <thead><tr><th>时间</th><th>动作</th><th>目标</th><th>模式</th><th>结果</th><th>撤销</th></tr></thead>
        <tbody>{"\n".join(rows)}</tbody>
      </table>
    </div>
    """
