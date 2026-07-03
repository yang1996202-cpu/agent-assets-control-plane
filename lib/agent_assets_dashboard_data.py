"""Agent Assets Dashboard — 数据加载与业务模型函数。

背景：dashboard 需要从多个 registry / JSON / 外部命令输出里聚合资产、MCP、
项目、发现候选和运行时信息。这些函数原本全部内嵌在 dashboard 入口脚本里。
设计意图：把无状态/有明确业务语义的数据处理逻辑拆到独立模块，便于测试和复用。
关键约束：
- 本模块只负责数据读取、转换、缓存，不生成 HTML。
- 所有 JSON IO 走 lib.load_json / lib.write_json；路径常量走 paths 模块。
- collect_runtime 会维护一个进程白名单 RUNTIME_WHITELIST，供 API 层的 kill 校验使用。
"""

import datetime as dt
import json
import os
import pathlib
import subprocess

import agent_assets_common as lib
import agent_assets_dashboard_paths as paths


# 最近一次 collect_runtime() 拿到的进程白名单：{pid_str: {"cmd": str, "category": str}}。
# /api/kill-process 只接受 pid 在此白名单里的请求，避免前端伪造任意 pid。
RUNTIME_WHITELIST = {}


def load_action_log():
    """加载操作日志；文件不存在时返回空结构。"""
    data = lib.load_json(paths.ACTION_LOG)
    if not isinstance(data, dict):
        return {"entries": []}
    data.setdefault("entries", [])
    return data


def append_action_log(action, target, mode, result, detail=""):
    """在操作日志前部追加一条记录，保留最近 200 条。

    detail 用于存放可重放操作所需的额外上下文，如 launchctl 的 plist 路径。
    """
    log = load_action_log()
    entries = log.setdefault("entries", [])
    entries.insert(
        0,
        {
            "time": lib.now_iso(),
            "action": action,
            "target": target,
            "mode": mode,
            "result": str(result),
            "detail": detail,
        },
    )
    log["entries"] = entries[:200]
    log["updated_at"] = lib.now_iso()
    lib.write_json(paths.ACTION_LOG, log)


def clear_action_log():
    """清空操作日志文件；文件不存在时静默成功。"""
    if paths.ACTION_LOG.exists():
        lib.write_json(paths.ACTION_LOG, {"entries": [], "updated_at": lib.now_iso()})


def infer_source_path(raw_path, resolved_path, package_name):
    candidate = pathlib.Path(resolved_path or raw_path)
    if package_name and "node_modules" in candidate.parts:
        parts = list(candidate.parts)
        for idx, part in enumerate(parts):
            if part != "node_modules" or idx + 1 >= len(parts):
                continue
            if package_name.startswith("@") and idx + 2 < len(parts):
                joined = "/".join(parts[idx + 1 : idx + 3])
                if joined == package_name:
                    return str(pathlib.Path(*parts[: idx + 3]))
            elif parts[idx + 1] == package_name:
                return str(pathlib.Path(*parts[: idx + 2]))
    if candidate.exists():
        if candidate.is_dir():
            return str(candidate)
        return str(candidate.parent)
    return str(pathlib.Path(raw_path).parent)


def save_review_decision(path_value, status):
    review = lib.load_json(paths.REVIEW)
    review.setdefault("updated_at", dt.datetime.now().strftime("%Y-%m-%d"))
    review.setdefault("purpose", "Review decisions for auto-discovered executable candidates. ignored items remain visible as known noise but do not count as needs-review.")
    review_paths = review.setdefault("paths", {})
    if status == "new":
        review_paths.pop(path_value, None)
    else:
        action = {
            "ignore": "leave_unregistered",
            "defer": "review_later",
        }.get(status, "")
        note = {
            "ignore": "Marked from dashboard as known noise.",
            "defer": "Marked from dashboard for later review.",
        }.get(status, "")
        review_paths[path_value] = {
            "status": status,
            "action": action,
            "note": note,
        }
    lib.write_json(paths.REVIEW, review)


def register_discovered_candidate(path_value):
    discovered = lib.load_json(paths.DISCOVERED)
    rows = discovered.get("candidates", [])
    row = next((item for item in rows if item.get("path") == path_value), None)
    if not row:
        raise ValueError(f"candidate not found: {path_value}")

    registry = lib.load_json(paths.REGISTRY)
    assets = registry.setdefault("assets", {})
    asset_id = row.get("name") or pathlib.Path(path_value).name
    asset = assets.setdefault(asset_id, {})

    categories = []
    if path_value.endswith(".app"):
        categories.append("agent-app")
    if "mcp-wrapper" in row.get("categories", []):
        categories.extend(["mcp", "cli"])
    elif "agent-candidate" in row.get("categories", []):
        categories.extend(["agent-host", "cli"])
    else:
        categories.append("cli")
    lib.append_unique(asset, "category", categories)
    lib.append_unique(asset, "stable_entrypoints", [row.get("path")])
    lib.append_unique(asset, "source_paths", [infer_source_path(row.get("path"), row.get("resolved_path"), row.get("package_hint"))])

    notes = [f"Registered from dashboard discovery on {dt.datetime.now().strftime('%Y-%m-%d')}."]
    if not str(path_value).startswith(str(paths.STABLE_BIN_DIR) + "/"):
        notes.append(f"Entrypoint is outside {paths.STABLE_BIN_DIR}; consider adding a stable wrapper.")
    lib.append_unique(asset, "notes", notes)

    stable_bin = registry.setdefault("indexes", {}).setdefault("stable_bin_dir", {})
    stable_bin.setdefault("path", str(paths.STABLE_BIN_DIR))
    current = stable_bin.setdefault("current_known_agent_entrypoints", [])
    if str(path_value).startswith(str(paths.STABLE_BIN_DIR) + "/") and path_value not in current:
        current.append(path_value)

    registry["updated_at"] = dt.datetime.now().strftime("%Y-%m-%d")
    lib.write_json(paths.REGISTRY, registry)
    save_review_decision(path_value, "new")


def iter_mcp_servers(data, path_prefix=""):
    if isinstance(data, dict):
        for key, value in data.items():
            next_prefix = f"{path_prefix}.{key}" if path_prefix else key
            if key == "mcpServers" and isinstance(value, dict):
                for server_name, config in value.items():
                    yield next_prefix, server_name, config
            else:
                yield from iter_mcp_servers(value, next_prefix)
    elif isinstance(data, list):
        for idx, value in enumerate(data):
            yield from iter_mcp_servers(value, f"{path_prefix}[{idx}]")


def simplify_mcp_entry(config):
    if not isinstance(config, dict):
        return {"transport": "unknown", "entry": ""}
    if config.get("url"):
        return {"transport": "http", "entry": str(config.get("url"))}
    command = config.get("command")
    args = config.get("args") or []
    entry = " ".join([str(command)] + [str(arg) for arg in args if arg is not None]).strip()
    transport = "stdio" if command else str(config.get("type") or "unknown")
    return {"transport": transport, "entry": entry}


def collect_host_mcp_refs(agent_registry):
    refs = []
    host_configs = agent_registry.get("indexes", {}).get("host_configs", {})
    for host_key in lib.host_config_keys():
        config_path = host_configs.get(host_key)
        if not config_path:
            continue
        path_obj = pathlib.Path(config_path)
        if not path_obj.exists():
            continue
        try:
            data = lib.load_json(path_obj)
        except Exception:
            continue
        for prefix, name, config in iter_mcp_servers(data):
            simple = simplify_mcp_entry(config)
            refs.append({
                "host": host_key,
                "path": config_path,
                "location": f"{config_path}:{prefix}.{name}",
                "name": name,
                "transport": simple["transport"],
                "entry": simple["entry"],
                "config": config,
            })
    return refs


def build_mcp_audit(agent_registry, mcp_registry, mcp_rows):
    host_refs = collect_host_mcp_refs(agent_registry)
    host_locations = {row["location"] for row in host_refs}
    host_names = {row["name"] for row in host_refs}
    registry_refs = []
    for bucket_name in ("stdio_servers", "http_servers", "internal_servers"):
        for name, server in sorted(mcp_registry.get(bucket_name, {}).items()):
            for location in lib.listify(server.get("hosts") or server.get("host")):
                registry_refs.append({
                    "registry_name": name,
                    "location": location,
                    "kind": bucket_name,
                })
    registry_locations = {row["location"] for row in registry_refs}
    mcp_by_name = {row["name"]: row for row in mcp_rows}

    host_only = []
    for ref in host_refs:
        if ref["location"] in registry_locations:
            continue
        health_row = mcp_by_name.get(ref["name"])
        host_only.append({
            "name": ref["name"],
            "location": ref["location"],
            "host": ref["host"],
            "transport": ref["transport"],
            "entry": ref["entry"],
            "state": "new",
            "health": health_row["health"] if health_row else "未登记",
        })

    registry_only = []
    for ref in registry_refs:
        if ref["location"] in host_locations:
            continue
        health_row = mcp_by_name.get(ref["registry_name"])
        registry_only.append({
            "name": ref["registry_name"],
            "location": ref["location"],
            "kind": ref["kind"],
            "state": "defer",
            "health": health_row["health"] if health_row else "registry-only",
        })

    failed = [row for row in mcp_rows if row["state"] == "failed"]
    unregistered_connected = [row for row in host_only if row["name"] in host_names]

    return {
        "host_only": host_only,
        "registry_only": registry_only,
        "failed": failed,
        "host_refs": host_refs,
        "summary": {
            "host_only": len(host_only),
            "registry_only": len(registry_only),
            "failed": len(failed),
            "connected": sum(1 for row in mcp_rows if row["state"] == "connected"),
            "total": len(mcp_rows),
            "host_refs": len(host_refs),
            "unregistered_connected": len(unregistered_connected),
        },
    }


def register_mcp_from_host(location):
    agent_registry = lib.load_json(paths.REGISTRY)
    mcp_registry = lib.load_json(paths.MCP_REGISTRY)
    refs = collect_host_mcp_refs(agent_registry)
    ref = next((item for item in refs if item["location"] == location), None)
    if not ref:
        raise ValueError(f"host mcp config not found: {location}")

    if ref["transport"] == "http":
        bucket = mcp_registry.setdefault("http_servers", {})
        server = bucket.setdefault(ref["name"], {})
        if ref["entry"]:
            server["url"] = ref["entry"]
        lib.append_unique(server, "hosts", [location])
    else:
        bucket = mcp_registry.setdefault("stdio_servers", {})
        server = bucket.setdefault(ref["name"], {})
        command = str((ref.get("config") or {}).get("command") or "")
        if command:
            if pathlib.Path(command).is_absolute():
                server["wrapper"] = command
            else:
                server["underlying"] = ref["entry"]
        lib.append_unique(server, "hosts", [location])

    mcp_registry["updated_at"] = dt.datetime.now().strftime("%Y-%m-%d")
    lib.write_json(paths.MCP_REGISTRY, mcp_registry)


def register_all_host_only_mcp():
    agent_registry = lib.load_json(paths.REGISTRY)
    mcp_registry = lib.load_json(paths.MCP_REGISTRY)
    health, _health_raw = cached_mcp_health("cached")
    mcp_rows = collect_mcp(mcp_registry, health)
    audit = build_mcp_audit(agent_registry, mcp_registry, mcp_rows)
    locations = [row["location"] for row in audit["host_only"]]
    for location in locations:
        register_mcp_from_host(location)
    return locations


def collect_entrypoints(agent_registry):
    owners = {}
    categories = {}
    assets = agent_registry.get("assets", {})
    for asset_id, asset in assets.items():
        for entry in lib.listify(asset.get("stable_entrypoints")):
            owners.setdefault(entry, []).append(asset_id)
            categories.setdefault(entry, set()).update(asset.get("category", []))

    known = agent_registry.get("indexes", {}).get("stable_bin_dir", {}).get("current_known_agent_entrypoints", [])
    for entry in known:
        owners.setdefault(entry, [])

    rows = []
    for entry, owner_list in sorted(owners.items()):
        rows.append({
            "path": entry,
            "state": lib.path_state(entry),
            "owners": sorted(owner_list),
            "kind": entrypoint_kind(entry, categories.get(entry, set())),
        })
    return rows


def entrypoint_kind(entry, categories):
    """判断一个稳定入口属于哪类。"""
    name = pathlib.Path(entry).name
    lower = name.lower()
    if str(entry).endswith(".app"):
        return "app"
    if name.endswith("-mcp") or "mcp" in categories:
        return "mcp-wrapper"
    if "agent-host" in categories:
        return "agent-command"
    if "dashboard" in categories:
        return "dashboard"
    if "package-manager" in categories or "cli-runtime" in categories or "support" in categories:
        return "runtime"
    # 常见解释器 / 包管理器 / 运行时，即使没在 registry 里标 support，也归 runtime
    runtime_prefixes = ("python", "pip", "node", "npm", "npx", "bun", "deno", "uv", "cargo", "rustc", "go", "ruby", "gem", "bundle", "php", "composer")
    if lower.startswith(runtime_prefixes):
        return "runtime"
    # 系统级路径里的解释器工具
    if "/python.framework/" in str(entry).lower() or "/usr/local/bin/node" == str(entry).lower():
        return "runtime"
    return "cli"


def parse_health_text(combined):
    health = {}
    for raw_line in combined.splitlines():
        line = raw_line.strip()
        if ": " not in line or " - " not in line:
            continue
        name = line.split(":", 1)[0].strip()
        status = line.rsplit(" - ", 1)[-1].strip()
        if "Connected" in status:
            health[name] = {"state": "connected", "label": status}
        elif "Failed" in status:
            health[name] = {"state": "failed", "label": status}
        else:
            health[name] = {"state": "unknown", "label": status}
    return health


def cached_mcp_health(prefix):
    if not paths.MCP_HEALTH_CACHE.exists():
        return {}, prefix
    try:
        data = lib.load_json(paths.MCP_HEALTH_CACHE)
    except Exception:
        return {}, prefix
    raw = data.get("raw", "")
    health = data.get("health", {})
    updated = data.get("updated_at", "unknown")
    return health, f"{prefix}\nShowing cached MCP health from {updated}.\n\n{raw}".strip()


def parse_claude_mcp_health():
    if not paths.CLAUDE.exists():
        return cached_mcp_health("claude command missing")
    try:
        proc = subprocess.run(
            [str(paths.CLAUDE), "mcp", "list"],
            cwd=str(paths.HOME),
            capture_output=True,
            text=True,
            timeout=8,
        )
    except subprocess.TimeoutExpired:
        return cached_mcp_health("claude mcp list timed out after 8s")
    except OSError as exc:
        return cached_mcp_health(str(exc))

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    health = parse_health_text(combined)
    try:
        paths.MCP_HEALTH_CACHE.write_text(
            json.dumps(
                {
                    "updated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "health": health,
                    "raw": combined.strip(),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass
    return health, combined.strip()


def collect_mcp(mcp_registry, health):
    rows = []
    for name, server in sorted(mcp_registry.get("stdio_servers", {}).items()):
        rows.append({
            "name": name,
            "kind": "stdio",
            "entry": server.get("wrapper") or server.get("underlying") or server.get("package_path") or "",
            "hosts": lib.listify(server.get("hosts")),
            "state": health.get(name, {}).get("state", "registered"),
            "health": health.get(name, {}).get("label", "registered"),
            "note": server.get("status_note") or "",
        })
    for name, server in sorted(mcp_registry.get("http_servers", {}).items()):
        rows.append({
            "name": name,
            "kind": "http",
            "entry": server.get("url") or "",
            "hosts": lib.listify(server.get("hosts")),
            "state": health.get(name, {}).get("state", "registered"),
            "health": health.get(name, {}).get("label", "registered"),
            "note": server.get("secret_location") or "",
        })
    for name, server in sorted(mcp_registry.get("internal_servers", {}).items()):
        rows.append({
            "name": name,
            "kind": "internal",
            "entry": server.get("command") or "",
            "hosts": lib.listify(server.get("host")),
            "state": "internal",
            "health": "internal",
            "note": server.get("note") or "",
        })
    return rows


def refresh_discovery(include_versions=False, mode="daily"):
    if not paths.ASSET_DISCOVER.exists():
        return ""
    try:
        command = [str(paths.ASSET_DISCOVER), "--mode", mode]
        if include_versions:
            command.append("--versions")
        proc = subprocess.run(
            command,
            cwd=str(paths.HOME),
            capture_output=True,
            text=True,
            timeout=20,
        )
        return ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    except Exception as exc:
        return f"asset-discover failed: {exc}"


def refresh_current_discovery():
    current = lib.load_json(paths.DISCOVERED)
    mode = current.get("scan_mode") or "daily"
    if mode not in {"daily", "deep"}:
        mode = "daily"
    return refresh_discovery(mode=mode)


def collect_discovered():
    data = lib.load_json(paths.DISCOVERED)
    return data.get("candidates", []), data.get("updated_at", ""), data


def refresh_projects():
    if not paths.ASSET_PROJECTS.exists():
        return ""
    try:
        proc = subprocess.run(
            [str(paths.ASSET_PROJECTS)],
            cwd=str(paths.HOME),
            capture_output=True,
            text=True,
            timeout=45,
        )
        return ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    except Exception as exc:
        return f"agent-assets-projects failed: {exc}"


def collect_projects():
    data = lib.load_json(paths.PROJECT_INDEX)
    return data.get("projects", []), data.get("updated_at", ""), data


def collect_all_processes():
    """采集所有运行进程（含系统进程），用于「系统进程」监视页面。

    直接调用 asset-runtime --show-system --show-normal --json，复用其分类和去噪逻辑。
    如果 asset-runtime 不存在或失败，返回空列表。
    """
    if not paths.ASSET_RUNTIME.exists():
        return []
    try:
        proc = subprocess.run(
            [str(paths.ASSET_RUNTIME), "--json", "--show-system", "--show-normal", "--show-apps"],
            cwd=str(paths.HOME),
            capture_output=True,
            text=True,
            timeout=25,
        )
        if proc.returncode != 0:
            return []
        data = json.loads(proc.stdout or "{}")
        return data.get("processes", [])
    except Exception:
        return []


def refresh_signals(skip_btm=False):
    """重新运行 agent-assets-macos-signals 扫描并写入 macos-signals.json。

    用于 launchctl 操作后同步刷新状态，让用户立即看到真实结果。
    skip_btm=True 时跳过 sfltool 等可能触发密码提示的调用。
    命令不存在或执行失败时返回错误字符串，成功时返回空字符串。
    """
    if not paths.ASSET_MACOS_SIGNALS.exists():
        return f"agent-assets-macos-signals not found: {paths.ASSET_MACOS_SIGNALS}"
    try:
        cmd = [str(paths.ASSET_MACOS_SIGNALS)]
        if skip_btm:
            cmd.append("--skip-btm")
        proc = subprocess.run(
            cmd,
            cwd=str(paths.HOME),
            capture_output=True,
            text=True,
            timeout=60,
        )
        return ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip() if proc.returncode != 0 else ""
    except Exception as exc:
        return f"agent-assets-macos-signals failed: {exc}"


def collect_runtime():
    """调用 asset-runtime --json，只读，带超时保护。返回 dict 或 None（失败/不存在时）。"""
    if not paths.ASSET_RUNTIME.exists():
        return {"_error": "asset-runtime 未找到", "_hint": f"预期路径：{paths.ASSET_RUNTIME}"}
    try:
        proc = subprocess.run(
            [str(paths.ASSET_RUNTIME), "--json"],
            cwd=str(paths.HOME),
            capture_output=True,
            text=True,
            timeout=25,
        )
        if proc.returncode != 0:
            return {"_error": f"asset-runtime 退出码 {proc.returncode}", "_hint": (proc.stderr or "").strip()[:400]}
        data = json.loads(proc.stdout or "{}")
        # 刷新 kill 白名单：只允许最近一次 runtime 报告里出现过的 pid
        global RUNTIME_WHITELIST
        RUNTIME_WHITELIST = {}
        for p in (data.get("processes") or []):
            pid = p.get("pid")
            if pid:
                RUNTIME_WHITELIST[str(pid)] = {"cmd": p.get("cmd", ""), "category": p.get("category", "")}
        return data
    except subprocess.TimeoutExpired:
        return {"_error": "asset-runtime 超时（>25s）"}
    except json.JSONDecodeError as exc:
        return {"_error": f"asset-runtime JSON 解析失败：{exc}"}
    except FileNotFoundError as exc:
        return {"_error": f"asset-runtime 无法执行：{exc}"}
