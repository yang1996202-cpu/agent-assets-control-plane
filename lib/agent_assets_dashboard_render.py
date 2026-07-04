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
# 默认只保留通用、无个人环境色彩的映射。用户可在 ~/.config/agent-assets/product-map.json
# 中按自己机器增删；安装脚本会从 templates/agent-assets/product-map.example.json 复制一份。
_DEFAULT_PRODUCT_MAP = [
    ("asset-dashboard", "Agent Assets 控制台", "本 dashboard"),
    ("com.docker.vmnetd", "Docker 网络守护", "Docker 系统级虚拟网络守护"),
    ("com.docker.socket", "Docker socket", "Docker 系统级 socket 守护"),
    ("docker", "Docker", "Docker 容器引擎"),
    ("google.keystone", "Google 自动更新", "Google 软件后台更新服务"),
    ("googleupdater", "Google 自动更新", "Google 软件后台更新服务"),
    ("播客", "Apple 播客", "macOS 系统自带"),
    ("股市", "Apple 股市", "macOS 系统自带"),
]


def _load_product_map():
    """加载用户自定义的厂商→产品映射；没有或损坏时返回默认最小映射。"""
    if paths.PRODUCT_MAP.exists():
        try:
            data = lib.load_json(paths.PRODUCT_MAP)
            entries = data.get("map") if isinstance(data, dict) else data
            if isinstance(entries, list):
                return [tuple(item) for item in entries if isinstance(item, (list, tuple)) and len(item) >= 2]
        except Exception:
            pass
    return _DEFAULT_PRODUCT_MAP


PRODUCT_MAP = _load_product_map()



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
    # 自定义 label 优先使用；没有时才按 state 查表，避免「已停止（进程已退出）」
    # 这种自定义文案被 state_labels 里的「未运行」覆盖掉。
    text = label if label else state_labels.get(state, state)
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
                # launchd Label 不强制要求含点；中文/短名称也要支持
                if lbl and lbl not in {"{", "}"} and not lbl.lower().startswith("disabled"):
                    disabled.add(lbl)
        return disabled
    except Exception:
        return set()


def _render_linked_assets(linked):
    """截断渲染系统信号的「关联」列。

    背景：linked_assets 可能包含很长的 chip（如 `agent-assets-system:stable_entrypoints`），
    全部渲染会把表格行撑得很高。
    设计意图：最多显示 1 个 chip；超过 1 个时显示为「首个 chip + `+N`」badge，
    并用 title 属性暴露完整列表，保持行高紧凑。
    约束：无关联时返回「未关联」占位；传入值会被 lib.listify 统一处理。
    """
    values = lib.listify(linked)
    if not values:
        return '<span class="muted">未关联</span>'
    first = lib.chip(values[0])
    if len(values) == 1:
        return first
    full = ", ".join(str(v) for v in values)
    return f'{first}<span class="linked-more" title="{lib.h(full)}">+{len(values) - 1}</span>'


def _pid_exists(pid):
    """检查某个 pid 当前是否还活着（不发送信号，只检测）。

    背景：对 root 运行的系统守护进程（/Library/LaunchDaemons）执行 os.kill(pid, 0)
          时，当前用户可能没权限发信号，会抛 PermissionError(EPERM)，但进程其实是存在的。
          如果把它当成不存在，就会出现「状态显示未运行，但资源列仍有 CPU/内存」的矛盾。
    设计意图：区分「进程不存在(ESRCH)」和「存在但没权限(EPERM)」，前者才返回 False。
    约束：传入非数字、负值等非法 pid 时返回 False；权限不足但进程存在时返回 True。
    """
    try:
        os.kill(int(pid), 0)
        return True
    except PermissionError:
        return True
    except (ProcessLookupError, OSError, ValueError, TypeError):
        return False


def _signal_row_html(row, disabled, resource_html, show_title=True):
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
        # 实时 PID 校验：如果快照显示 running 但实际 pid 已不存在（用户在系统外杀掉、
        # 或 launchctl 状态已变但快照未刷新），按实际进程是否存在修正状态。
        pids = [p.get("pid") for p in (row.get("processes") or []) if p.get("pid")]
        if pids and not any(_pid_exists(pid) for pid in pids):
            state, state_label = "not-running", "已停止（进程已退出）"
    elif plist:
        state, state_label = "not-running", "未运行"
    else:
        state, state_label = "registered", "登录项/扩展"
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
    if show_title:
        name_cell = f'<div><strong>{lib.h(title)}</strong></div>'
        if str(title) != str(raw_label):
            name_cell += f'<div class="subtle">{lib.h(raw_label)}</div>'
    else:
        name_cell = f'<div class="subtle group-subname">{lib.h(raw_label)}</div>'
    if plist:
        name_cell += f'<div class="subtle plist-path">{lib.h(plist)}</div>'
    if note:
        name_cell += f'<div class="subtle">{lib.h(note)}</div>'
    state_sort_value = {"running": 0, "not-running": 1, "registered": 2}.get(state, 3)
    resource_sort_value = 0 if resource_html == "—" else 1
    return f"""
    <tr class="searchable" data-section="signals" data-control="{lib.h(control)}" data-filter-tags="{lib.h(filter_tags)}" data-text="{lib.h(raw_label)} {lib.h(title)} {lib.h(kind)} {lib.h(json.dumps(row, ensure_ascii=False))}">
      <td class="col-name">{name_cell}</td>
      <td class="col-type">{lib.h(kind)}</td>
      <td class="col-state" data-sort-value="{state_sort_value}">{state_badge(state, state_label)}<span class="subtle">{lib.h(exit_text)}</span></td>
      <td class="col-resource" data-sort-value="{resource_sort_value}">{lib.h(resource_html)}</td>
      <td class="col-ports"><span class="subtle">{lib.h(port_text)}</span></td>
      <td class="col-linked">{_render_linked_assets(linked)}</td>
      <td class="action-cell">{actions}</td>
    </tr>
    """


def render_macos_signals_rows(rows, process_list=None):
    """渲染「系统信号」tab；若传入 process_list，会给 running 行补充 CPU / 内存资源。"""
    if not rows:
        return '<p class="muted">还没有系统信号。运行 asset-macos-signals 生成。</p>'
    groups = {"user-launchd": [], "system-launchd": [], "app-running": [], "login-item": []}
    for row in rows:
        groups.setdefault(row.get("_control") or "login-item", []).append(row)
    for key in groups:
        # 先按人话标题（忽略大小写）聚合，再把已关联的置顶；
        # 这样同一产品（如 gbrain 记忆服务）的多行会相邻，避免被 Google 自动更新等插开。
        groups[key].sort(key=lambda r: (
            str((r.get("_human") or humanize_signal(r))[0]).lower(),
            0 if lib.listify(r.get("linked_assets")) else 1,
        ))
    disabled = _launchctl_disabled_set()
    process_lookup = _build_process_lookup(process_list)

    # 横向筛选栏：按可控性分组
    control_buttons = [f'<button class="filter active" data-filter="">全部 ({len(rows)})</button>']
    for key in ["user-launchd", "system-launchd", "app-running", "login-item"]:
        grp = groups.get(key) or []
        if grp:
            icon, label, _ = CONTROL_META[key]
            control_buttons.append(f'<button class="filter" data-filter="{lib.h(key)}">{icon} {lib.h(label)} ({len(grp)})</button>')

    parts = [
        f'<div class="filter-bar signals-filter-bar">{"".join(control_buttons)}</div>',
    ]
    for key in ["user-launchd", "system-launchd", "app-running", "login-item"]:
        grp = groups.get(key) or []
        if not grp:
            continue
        icon, label, note = CONTROL_META[key]
        parts.append(f"""
        <table class="signal-table" data-control="{lib.h(key)}">
          <caption><span class="ctrl-icon">{icon}</span> <strong>{lib.h(label)}</strong> <span class="muted">({len(grp)})</span><span class="subtle"> — {lib.h(note)}</span></caption>
          <thead><tr><th class="col-name sortable" data-sort="name">名称</th><th class="col-type sortable" data-sort="type">类型</th><th class="col-state sortable" data-sort="state">状态</th><th class="col-resource sortable" data-sort="resource">资源</th><th class="col-ports">端口</th><th class="col-linked">关联</th><th class="action-cell">操作</th></tr></thead>
          <tbody>
        """)
        # 预计算每个展示标题出现的次数，用于判断是否需要分组
        from collections import Counter
        title_counts = Counter(str((r.get("_human") or humanize_signal(r))[0]) for r in grp)
        current_group_title = None
        for row in grp:
            title, _ = row.get("_human") or humanize_signal(row)
            group_title = str(title)
            if group_title != current_group_title:
                if title_counts[group_title] > 1:
                    parts.append(f'<tr class="signal-group-header"><td colspan="7"><strong>{lib.h(group_title)}</strong></td></tr>')
                current_group_title = group_title
            resource_html = _signal_resource_text(row, process_lookup)
            # 如果该标题只有一行，仍显示标题；多行时组内行只显示服务名
            parts.append(_signal_row_html(row, disabled, resource_html, show_title=(title_counts[group_title] <= 1)))
        parts.append("</tbody></table>")
    return "\n".join(parts)


def _runtime_cmd_short(cmd, limit=90):
    cmd = (cmd or "").strip()
    if len(cmd) <= limit:
        return cmd
    return cmd[: limit - 1] + "…"


def _format_rss(kb):
    """把 KB 内存格式化成人类可读字符串（MB / GB）。"""
    try:
        kb = int(kb or 0)
    except (TypeError, ValueError):
        return "—"
    if kb <= 0:
        return "—"
    if kb >= 1024 * 1024:
        return f"{kb / (1024 * 1024):.2f} GB"
    return f"{kb / 1024:.1f} MB"


def _aggregate_runtime_by_fp(processes):
    """按 fingerprint 聚合进程。返回 [{fp, category, pids, ports, rss, cmd, cwds}]。"""
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
                "rss": 0,
                "cmd": p.get("cmd", ""),
                "cwds": set(),
            },
        )
        pid = p.get("pid")
        if pid and pid not in g["pids"]:
            g["pids"].append(pid)
        for port in lib.listify(p.get("ports")):
            g["ports"].add(port)
        g["rss"] += int(p.get("rss", 0) or 0)
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
        "app": ("App", "app"),
    }
    label, cls = mapping.get(category, ("Other", "other"))
    return f'<span class="tag {cls}">{lib.h(label)}</span>'


def _cwd_badge(cwd):
    if not cwd or cwd == "/":
        return ""
    href = "file://" + urllib.parse.quote(str(cwd))
    return f'<a class="chip cwd-chip" href="{lib.h(href)}">{lib.h(cwd)}</a>'


def _runtime_table_row(pid_or_count, type_badge, ports, rss, cmd, cwd, pids_for_kill, cmd_short, filter_tags=""):
    ports_html = ", ".join(ports) if ports else '<span class="muted">—</span>'
    cwd_html = _cwd_badge(cwd)
    kill_btns = _kill_buttons_for_pids(pids_for_kill, cmd_short) if pids_for_kill else ""
    return (
        f'<tr class="searchable" data-section="runtime" data-filter-tags="{lib.h(filter_tags)}">'
        f'<td class="col-pid">{pid_or_count}</td>'
        f'<td class="col-type">{type_badge}</td>'
        f'<td class="col-ports">{ports_html}</td>'
        f'<td class="col-rss">{lib.h(_format_rss(rss))}</td>'
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
          <th class="col-rss">内存</th>
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
            total_rss = 0
            for p in matching:
                ports_set.update(lib.listify(p.get("ports")))
                total_rss += int(p.get("rss", 0) or 0)
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
            parts.append(_runtime_table_row(pid_html, type_badge, sorted(ports_set), total_rss, fp, cwd, pids, cmd_short, filter_tags=f"{cat} leak"))
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
                p.get("rss", 0),
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
                g["rss"],
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


def _format_cpu(value, show_zero=False):
    """把 CPU 百分比格式化成人类可读字符串。show_zero=True 时 0 也显示 0.0%。"""
    try:
        cpu = float(value or 0)
    except (TypeError, ValueError):
        return "—"
    if cpu <= 0 and not show_zero:
        return "—"
    return f"{cpu:.1f}%"


_APP_BUNDLE_RE = re.compile(r"/Applications/([^/]+\.app)/")


def _process_display_name(cmd):
    """从原始命令提取干净易读的进程/应用名称。

    规则优先级：
    1. /Applications/Xxx.app 里的进程 → 返回 Xxx.app
    2. 解释器跑的脚本 → 返回「解释器 脚本名」
    3. 系统路径 → 只返回 basename
    4. 其他 → 返回第一个 token 的 basename
    """
    cmd = (cmd or "").strip()
    if not cmd:
        return "未知进程"
    # 去掉 login shell 的前导横杠
    if cmd.startswith("-"):
        cmd = cmd[1:].lstrip()
    # 1. 应用 bundle
    m = _APP_BUNDLE_RE.search(cmd)
    if m:
        return m.group(1)
    # 取第一个 token
    first = cmd.split(None, 1)[0]
    # 2. 解释器 + 脚本
    interpreters = ("node", "python", "python3", "bun", "deno", "ruby", "php")
    base_first = os.path.basename(first)
    if base_first.lower().startswith(interpreters):
        rest = cmd[len(first):].strip()
        script = rest.split(None, 1)[0] if rest else ""
        script_base = os.path.basename(script) if script else ""
        if script_base:
            return f"{base_first} {script_base}"
        return base_first
    # 3/4. basename
    name = os.path.basename(first)
    return name if name else first


def _usage_bar_html(value, max_value, label, css_class):
    """生成一个克制的小进度条，类似 iOS / macOS 活动监视器的用量条。

    设计意图：把数值和图形分离，减少单元格内的视觉噪音；
             进度条只用来在同列中快速对比相对大小，不抢进程名的注意力。
    约束：返回的 HTML 用在「系统进程」表格的 CPU / 内存列；max_value 为 0 时按 1 处理避免除零。
    """
    try:
        pct = (float(value or 0) / max(float(max_value or 0), 1)) * 100
    except (TypeError, ValueError):
        pct = 0
    pct = min(100, max(0, pct))
    return f'''
    <div class="usage-cell" title="{lib.h(label)}">
      <div class="usage-bar {lib.h(css_class)}">
        <div class="usage-bar-fill" style="width:{pct:.1f}%"></div>
      </div>
      <span class="usage-value">{lib.h(label)}</span>
    </div>
    '''


def _build_process_lookup(processes):
    """把进程列表按 pid 建成查找表，key 统一为字符串，方便与 signals 里的 pid 匹配。"""
    lookup = {}
    for p in processes or []:
        pid = p.get("pid")
        if pid is None:
            continue
        key = str(pid)
        if key not in lookup:
            lookup[key] = p
    return lookup


def _signal_resource_text(row, process_lookup):
    """计算一个系统信号行对应的运行进程资源文本。

    背景：signals 数据里只记录 pid，不记录 CPU / RSS；dashboard 已经在采进程列表，
          可以按 pid 匹配，把资源用量补充显示在表格里。
    设计意图：只读渲染层补充，不动 macos-signals.json 的采集逻辑。
    约束：
    - 仅对 running=true 且 processes 非空的行计算；其余返回 "—"。
    - 多进程资源做聚合，因为有些服务会拉起多个子进程。
    - 进程列表里匹配不到任何 pid 时返回 "—"。
    """
    if not row.get("running"):
        return "—"
    procs = row.get("processes") or []
    if not procs:
        return "—"

    total_cpu = 0.0
    total_rss = 0
    matched = False
    for p in procs:
        pid = p.get("pid")
        if pid is None:
            continue
        info = process_lookup.get(str(pid))
        if not info:
            continue
        matched = True
        try:
            total_cpu += float(info.get("cpu") or 0)
        except (TypeError, ValueError):
            pass
        try:
            total_rss += int(info.get("rss") or 0)
        except (TypeError, ValueError):
            pass

    if not matched:
        return "—"

    cpu_text = _format_cpu(total_cpu, show_zero=True)
    rss_text = _format_rss(total_rss) if total_rss > 0 else "—"
    return f"CPU {cpu_text} · 内存 {rss_text}"


def _aggregate_system_processes(processes):
    """把原始进程列表按「可读名称」聚合，消除 Chrome Helper / 微信多进程等重复行。

    背景：macOS 上现代应用（浏览器、微信、Electron 应用）会拉起大量 helper/渲染进程，
          如果不聚合，表格会被同一应用的几十行占满，高占用反而被淹没。
    设计意图：按 _process_display_name 聚合，同名进程合并为一条，CPU 和内存做加总，
             保留所有 PID 用于终止操作；分类取组内最常见的非 unknown 值。
    约束：返回的聚合行包含 pids 列表、聚合后的 cpu/rss、代表性 cmd 和 category。
    """
    groups = {}
    for p in processes:
        cmd = p.get("cmd", "")
        name = _process_display_name(cmd)
        g = groups.setdefault(
            name,
            {
                "name": name,
                "pids": [],
                "rss": 0,
                "cpu": 0.0,
                "cmd": cmd,
                "categories": [],
            },
        )
        pid = p.get("pid")
        if pid:
            g["pids"].append(pid)
        g["rss"] += int(p.get("rss", 0) or 0)
        g["cpu"] += float(p.get("cpu", 0) or 0)
        g["categories"].append(p.get("category", "unknown"))

    for g in groups.values():
        cats = [c for c in g["categories"] if c != "unknown"]
        if not cats:
            cats = g["categories"]
        g["category"] = max(set(cats), key=cats.count) if cats else "unknown"
        g["pids"].sort(key=lambda x: int(x) if str(x).isdigit() else 0)
    return sorted(groups.values(), key=lambda g: (-g["rss"], -g["cpu"]))


def _format_gb(value, digits=2):
    """把 GB 数值格式化为人类可读字符串。"""
    try:
        gb = float(value or 0)
    except (TypeError, ValueError):
        return "—"
    if gb <= 0:
        return "0 GB"
    if gb < 1:
        return f"{gb * 1024:.1f} MB"
    return f"{gb:.{digits}f} GB"


def _render_memory_summary_card(mem_stats, processes_total_rss_gb):
    """渲染系统进程页顶部的内存总览卡片。

    背景：进程列表的 RSS 加总只是用户态可见进程的一部分，远小于系统实际已用内存。
          如果不展示系统级内存统计，用户会以为 dashboard 统计有误。
    设计意图：用类似 macOS 活动监视器的口径展示总内存、已用、App、联动（Wired）、
             被压缩、缓存文件、可用/空闲，并在下方说明「进程列表只覆盖部分用户态进程」。
    约束：mem_stats 为 None 时不渲染；processes_total_rss_gb 用于对比说明。
    """
    if not mem_stats:
        return ""

    total = mem_stats.get("total_gb", 0)
    used = mem_stats.get("used_gb", 0)
    app = mem_stats.get("app_gb", 0)
    wired = mem_stats.get("wired_gb", 0)
    compressed = mem_stats.get("compressed_gb", 0)
    file_backed = mem_stats.get("file_backed_gb", 0)
    free = mem_stats.get("free_gb", 0)
    available = mem_stats.get("available_gb", 0)
    used_pct = (used / total * 100) if total else 0

    def _bar(label, value, color):
        pct = (value / total * 100) if total else 0
        return (
            f'<div class="mem-bar-row">'
            f'<span class="mem-bar-label">{lib.h(label)}</span>'
            f'<div class="mem-bar-track"><div class="mem-bar-fill {lib.h(color)}" style="width:{pct:.1f}%"></div></div>'
            f'<span class="mem-bar-value">{lib.h(_format_gb(value))}</span>'
            f'</div>'
        )

    return f"""
    <div class="memory-summary card">
      <div class="memory-summary-head">
        <div>
          <h4>内存总览</h4>
          <div class="memory-total">已用 {lib.h(_format_gb(used))} / 总计 {lib.h(_format_gb(total))} <span class="muted">({used_pct:.1f}%)</span></div>
        </div>
        <div class="memory-availability">可用 {lib.h(_format_gb(available))}</div>
      </div>
      <div class="memory-bars">
        {_bar("App 内存", app, "app")}
        {_bar("联动内存", wired, "wired")}
        {_bar("被压缩", compressed, "compressed")}
        {_bar("缓存文件", file_backed, "cached")}
      </div>
      <p class="memory-hint muted">
        下方进程列表只包含本 dashboard 采集到的用户态进程（合计约 {lib.h(_format_gb(processes_total_rss_gb))}），
        不包含 kernel、系统守护进程、压缩页、文件缓存等，因此会小于系统总已用内存。
      </p>
    </div>
    """


def _render_top_processors(aggregated, max_cpu, max_rss):
    """渲染「高占用进程」顶部卡片：左侧 Top 5 CPU，右侧 Top 5 内存。

    设计意图：参考 Stats / macOS 活动监视器，把最值得关注的进程直接放在页面顶部，
             用户不用滚动和搜索就能看到当前谁最吃资源。
    约束：聚合后的数据已经按应用合并，不会出现 Chrome Helper 占满榜单的情况。
    """
    if not aggregated:
        return ""

    top_cpu = sorted(aggregated, key=lambda g: -g["cpu"])[:5]
    top_rss = sorted(aggregated, key=lambda g: -g["rss"])[:5]

    def _item_html(g, value, max_value, css_class, formatter):
        return (
            f'<div class="top-proc-item">'
            f'<span class="top-proc-name" title="{lib.h(g["cmd"])}">{lib.h(g["name"])}</span>'
            f'{_usage_bar_html(value, max_value, formatter(value), css_class)}'
            f'</div>'
        )

    cpu_items = "\n".join(_item_html(g, g["cpu"], max_cpu, "cpu", lambda v: _format_cpu(v, True)) for g in top_cpu)
    rss_items = "\n".join(_item_html(g, g["rss"], max_rss, "mem", _format_rss) for g in top_rss)

    return f"""
    <div class="top-processors card">
      <div class="top-proc-grid">
        <div class="top-proc-col">
          <h4>⚡ 高 CPU 占用</h4>
          {cpu_items}
        </div>
        <div class="top-proc-col">
          <h4>🧠 高内存占用</h4>
          {rss_items}
        </div>
      </div>
    </div>
    """


def render_system_processes_rows(processes, mem_stats=None):
    """渲染「系统进程」tab：内存总览 + 高占用 + 聚合表格。

    设计意图：
    - 顶部先给系统级内存总览，解释「为什么进程列表加总小于实际占用」。
    - 参考 Stats 的高占用进程卡片，把 Top CPU / Top 内存放在最显眼的位置。
    - 按应用名称聚合，避免 Chrome / WeChat / Electron Helper 等把表格撑爆。
    - 表格默认按内存降序，支持表头排序和分类筛选。
    """
    if not processes:
        return '<p class="muted">没有采集到系统进程数据。运行 asset-runtime --show-system 生成。</p>'

    aggregated = _aggregate_system_processes(processes)
    if not aggregated:
        return '<p class="muted">没有可展示的系统进程。</p>'

    # 分类统计（基于聚合后的行）
    cat_counts = {}
    for g in aggregated:
        cat = g["category"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    non_system = [g for g in aggregated if g["category"] != "system"]
    default_rows = non_system if non_system else aggregated

    max_cpu = max((g["cpu"] for g in aggregated), default=0) or 1
    max_rss = max((g["rss"] for g in aggregated), default=0) or 1

    # 筛选按钮
    filter_buttons = [f'<button class="filter" data-filter="">全部 ({len(aggregated)})</button>']
    if non_system:
        filter_buttons.append(f'<button class="filter active" data-filter="user">用户进程 ({len(non_system)})</button>')
    user_cats = [("app", "App"), ("mcp", "MCP"), ("dev-server", "Dev Server"), ("support", "Support")]
    other_cats = [("system", "System"), ("unknown", "Unknown")]
    for cat, label in user_cats + other_cats:
        n = cat_counts.get(cat, 0)
        if n:
            filter_buttons.append(f'<button class="filter" data-filter="{lib.h(cat)}">{lib.h(label)} ({n})</button>')

    # 默认按内存降序
    default_rows.sort(key=lambda g: (-g["rss"], -g["cpu"]))

    def _row_html(g):
        name = g["name"]
        cat = g["category"]
        type_badge = _runtime_type_badge(cat)
        filter_tags = f"{cat} user" if cat != "system" else cat
        pid_hint = f"PID {', '.join(str(p) for p in g['pids'])}" if len(g["pids"]) <= 3 else f"{len(g['pids'])} 个进程"
        kill_btns = _kill_buttons_for_pids(g["pids"], name) if g["pids"] else ""
        return (
            f'<tr class="searchable" data-section="system-processes" data-filter-tags="{lib.h(filter_tags)}">'
            f'<td class="col-name"><strong title="{lib.h(g["cmd"])}">{lib.h(name)}</strong><span class="pid-hint">{lib.h(pid_hint)}</span></td>'
            f'<td class="col-cpu" data-sort-value="{g["cpu"]:.3f}">{_usage_bar_html(g["cpu"], max_cpu, _format_cpu(g["cpu"], True), "cpu")}</td>'
            f'<td class="col-rss" data-sort-value="{g["rss"]}">{_usage_bar_html(g["rss"], max_rss, _format_rss(g["rss"]), "mem")}</td>'
            f'<td class="col-type">{type_badge}</td>'
            f'<td class="col-action">{kill_btns}</td>'
            f'</tr>'
        )

    out_rows = [_row_html(g) for g in default_rows]
    top_section = _render_top_processors(aggregated, max_cpu, max_rss)
    processes_total_rss_gb = sum(g["rss"] for g in aggregated) / (1024 * 1024)
    memory_section = _render_memory_summary_card(mem_stats, processes_total_rss_gb)

    return f"""
    {memory_section}
    {top_section}
    <div class="filter-bar system-processes-filter-bar">
      {"".join(filter_buttons)}
    </div>
    <div class="processes-panel">
      <table class="data-table system-processes-table" data-sortable>
        <thead>
          <tr>
            <th class="col-name sortable" data-sort="name">进程</th>
            <th class="col-cpu sortable" data-sort="cpu">CPU</th>
            <th class="col-rss sortable desc" data-sort="rss">内存</th>
            <th class="col-type">类型</th>
            <th class="col-action">操作</th>
          </tr>
        </thead>
        <tbody>{"\n".join(out_rows)}</tbody>
      </table>
    </div>
    """


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


def render_runtime_filter_bar(runtime_data=None):
    """渲染运行态顶部分类筛选按钮，按实际进程数动态显示并带计数。

    背景：旧版硬编码了「Agent」「MCP」「Dev Server」等按钮，用户点击「Agent」时
          若本机没有 `agent-daemon` 分类进程，会以为功能坏了。
    设计意图：根据当前 runtime 数据里的真实分类统计，只显示有数据的按钮，并标注数量；
             把「Agent」改成「Agent Daemon」，避免与「Agent 应用」混淆。
    约束：category 只可能为 mcp / agent-daemon / dev-server / support / system / unknown / app；
          support 与 system 合并为一个「支撑 / 系统」按钮，与前端 JS 过滤逻辑保持一致。
    """
    processes = (runtime_data or {}).get("processes") or []
    counts = {"mcp": 0, "agent-daemon": 0, "dev-server": 0, "support": 0, "system": 0, "unknown": 0}
    for p in processes:
        cat = p.get("category", "unknown")
        if cat in counts:
            counts[cat] += 1
    support_system = counts["support"] + counts["system"]
    total = len(processes)

    buttons = [f'<button class="filter active" data-filter="">全部 ({total})</button>']
    if counts["mcp"]:
        buttons.append(f'<button class="filter" data-filter="mcp">MCP ({counts["mcp"]})</button>')
    if counts["agent-daemon"]:
        buttons.append(f'<button class="filter" data-filter="agent-daemon">Agent Daemon ({counts["agent-daemon"]})</button>')
    if counts["dev-server"]:
        buttons.append(f'<button class="filter" data-filter="dev-server">Dev Server ({counts["dev-server"]})</button>')
    if support_system:
        buttons.append(f'<button class="filter" data-filter="support-system">支撑 / 系统 ({support_system})</button>')
    if counts["unknown"]:
        buttons.append(f'<button class="filter" data-filter="other">其他 ({counts["unknown"]})</button>')

    return f"""
    <div class="filter-bar runtime-filter-bar">
      {"".join(buttons)}
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
