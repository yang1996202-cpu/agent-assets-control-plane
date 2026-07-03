"""Agent Assets Dashboard — HTTP 服务与路由。

背景：dashboard 支持两种模式：生成静态 HTML 文件，或启动本地 HTTP 服务器提供
实时刷新、一键扫描、MCP 登记、launchctl 控制、进程终止等交互。
设计意图：把 HTTP 服务相关逻辑（handler、kill/launchctl 安全校验、serve）独立出来，
上层入口脚本只需解析 CLI 并调用 serve / 静态生成。
关键约束：
- 仅绑定 127.0.0.1，避免外部访问。
- kill-process / launchctl 有严格的白名单和路径校验，禁止操作系统级进程。
"""

import http.server
import json
import os
import pathlib
import plistlib
import subprocess
import sys
import urllib.parse

import agent_assets_common as lib
import agent_assets_dashboard_data as data
import agent_assets_dashboard_html as html_module
import agent_assets_dashboard_paths as paths
import agent_assets_dashboard_render as render


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    server_version = "AgentAssetsDashboard/1.0"

    def send_text(self, text, content_type="text/plain; charset=utf-8", status=200, include_body=True):
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if include_body:
            self.wfile.write(data)

    def send_json(self, payload, status=200):
        self.send_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "application/json; charset=utf-8", status)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in {"/", "/dashboard.html"}:
            html_text, _summary = html_module.build_dashboard(run_discovery=False, refresh_mcp=False, run_projects=False, live=True)
            self.send_text(html_text, "text/html; charset=utf-8")
            return
        if parsed.path == "/favicon.ico":
            self.send_text("", "image/x-icon", status=204)
            return
        if parsed.path == "/api/status":
            _html_text, summary = html_module.build_dashboard(run_discovery=False, refresh_mcp=False, run_projects=False, live=True)
            self.send_json(summary)
            return
        self.send_json({"ok": False, "error": "not found"}, status=404)

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in {"/", "/dashboard.html"}:
            html_text, _summary = html_module.build_dashboard(run_discovery=False, refresh_mcp=False, run_projects=False, live=True)
            self.send_text(html_text, "text/html; charset=utf-8", include_body=False)
            return
        if parsed.path == "/api/status":
            _html_text, summary = html_module.build_dashboard(run_discovery=False, refresh_mcp=False, run_projects=False, live=True)
            self.send_text(json.dumps(summary, ensure_ascii=False) + "\n", "application/json; charset=utf-8", include_body=False)
            return
        self.send_text("", status=404, include_body=False)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/scan":
            query = urllib.parse.parse_qs(parsed.query)
            include_versions = query.get("versions", ["0"])[0] in {"1", "true", "yes"}
            mode = query.get("mode", ["daily"])[0]
            if mode not in {"daily", "deep"}:
                mode = "daily"
            try:
                self.send_json(html_module.run_scan(include_versions=include_versions, mode=mode))
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=500)
            return
        if parsed.path == "/api/reconcile":
            query = urllib.parse.parse_qs(parsed.query)
            mode = query.get("mode", ["daily"])[0]
            try:
                self.send_json(html_module.run_reconcile(mode=mode))
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=500)
            return
        if parsed.path == "/api/crosscheck":
            try:
                self.send_json(html_module.run_crosscheck())
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=500)
            return
        if parsed.path == "/api/projects/scan":
            try:
                self.send_json(html_module.run_project_scan())
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=500)
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            payload = {}
        if parsed.path == "/api/review":
            path_value = str(payload.get("path") or "")
            status = str(payload.get("status") or "")
            if not path_value or status not in {"new", "defer", "ignore"}:
                self.send_json({"ok": False, "error": "invalid review payload"}, status=400)
                return
            try:
                data.save_review_decision(path_value, status)
                data.refresh_current_discovery()
                html_module.write_dashboard(run_discovery=False, refresh_mcp=False, run_projects=False, live=False)
                self.send_json({"ok": True, "path": path_value, "status": status})
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=500)
            return
        if parsed.path == "/api/register-candidate":
            path_value = str(payload.get("path") or "")
            if not path_value:
                self.send_json({"ok": False, "error": "missing candidate path"}, status=400)
                return
            try:
                data.register_discovered_candidate(path_value)
                data.refresh_current_discovery()
                html_module.write_dashboard(run_discovery=False, refresh_mcp=False, run_projects=False, live=False)
                self.send_json({"ok": True, "path": path_value})
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=500)
            return
        if parsed.path == "/api/register-mcp":
            location = str(payload.get("location") or "")
            if not location:
                self.send_json({"ok": False, "error": "missing mcp location"}, status=400)
                return
            try:
                data.register_mcp_from_host(location)
                data.refresh_current_discovery()
                html_module.write_dashboard(run_discovery=False, refresh_mcp=False, run_projects=False, live=False)
                self.send_json({"ok": True, "location": location})
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=500)
            return
        if parsed.path == "/api/register-mcp-bulk":
            try:
                locations = data.register_all_host_only_mcp()
                data.refresh_current_discovery()
                html_module.write_dashboard(run_discovery=False, refresh_mcp=False, run_projects=False, live=False)
                self.send_json({"ok": True, "locations": locations, "count": len(locations)})
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=500)
            return
        if parsed.path == "/api/launchctl":
            result, http_status = handle_launchctl(payload)
            if http_status == 200:
                try:
                    html_module.write_dashboard(run_discovery=False, refresh_mcp=False, run_projects=False, live=False)
                except Exception:
                    pass
            self.send_json(result, status=http_status)
            return
        if parsed.path == "/api/kill-process":
            result, http_status = handle_kill_process(payload)
            self.send_json(result, status=http_status)
            return
        self.send_json({"ok": False, "error": "not found"}, status=404)

    def log_message(self, format, *args):
        sys.stderr.write("asset-dashboard: " + (format % args) + "\n")


def _launchctl_status(label):
    """查某用户级 service 实时状态，返回 (running, auto_disabled)。print 失败(已 unload)时用 print-disabled 兜底。"""
    domain = f"gui/{os.getuid()}"
    running = False
    auto_disabled = False
    try:
        proc = subprocess.run(["launchctl", "print", f"{domain}/{label}"], capture_output=True, text=True, timeout=6)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                ls = line.strip()
                if ls.startswith("state =") and "running" in ls:
                    running = True
                if ls.startswith("pid =") and not ls.rstrip().endswith("= 0"):
                    running = True
                if ls.startswith("disabled =") and "true" in ls:
                    auto_disabled = True
    except Exception:
        pass
    if not auto_disabled:
        try:
            proc = subprocess.run(["launchctl", "print-disabled", domain], capture_output=True, text=True, timeout=6)
            for line in (proc.stdout or "").splitlines():
                if label in line and ("(true)" in line or line.lower().rstrip().endswith("disabled")):
                    auto_disabled = True
        except Exception:
            pass
    return running, auto_disabled


def handle_launchctl(payload):
    """执行用户级 LaunchAgent 的 enable/disable/bootstrap/bootout。严格白名单（~/Library/LaunchAgents）+ 从 plist 读真实 Label，不信任前端。返回 (result, http_status)。"""
    plist = str(payload.get("plist") or "")
    action = str(payload.get("action") or "")
    if action not in {"enable", "disable", "bootstrap", "bootout"}:
        return {"ok": False, "error": "非法操作"}, 400
    home_agents = str(pathlib.Path.home() / "Library" / "LaunchAgents")
    if not plist or not plist.startswith(home_agents + "/") or not os.path.isfile(plist):
        return {"ok": False, "error": "plist 不在用户级目录(~/Library/LaunchAgents)或不存在"}, 400
    try:
        with open(plist, "rb") as fh:
            plist_data = plistlib.load(fh)
        real_label = str(plist_data.get("Label") or "").strip() if isinstance(plist_data, dict) else ""
    except Exception as exc:
        return {"ok": False, "error": f"读取 plist 失败: {exc}"}, 400
    # Label fallback：空占位 plist（如 Google Keystone stub）读不到，按 文件名stem → 前端label 兜底
    if not real_label:
        real_label = os.path.splitext(os.path.basename(plist))[0]
    if not real_label:
        cand = str(payload.get("label") or "").strip()
        if cand and "/" not in cand and " " not in cand:
            real_label = cand
    # label 用于 domain-target(gui/uid/<label>)，含 / 会破坏解析，拒绝
    if not real_label or "/" in real_label or "\x00" in real_label:
        return {"ok": False, "error": "无法确定 launchd Label（plist 为空且无可用文件名）"}, 400
    domain = f"gui/{os.getuid()}"
    if action == "bootstrap":
        cmd = ["launchctl", "bootstrap", domain, plist]
    elif action == "bootout":
        cmd = ["launchctl", "bootout", f"{domain}/{real_label}"]
    elif action == "enable":
        cmd = ["launchctl", "enable", f"{domain}/{real_label}"]
    else:
        cmd = ["launchctl", "disable", f"{domain}/{real_label}"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except Exception as exc:
        return {"ok": False, "error": f"执行失败: {exc}"}, 500
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return {"ok": False, "error": err or f"launchctl 退出码 {proc.returncode}"}, 500
    running, auto_disabled = _launchctl_status(real_label)
    action_zh = {"enable": "已启用开机自启", "disable": "已禁用开机自启", "bootstrap": "已启动", "bootout": "已停止"}.get(action, action)
    return {"ok": True, "action": action, "action_zh": action_zh, "label": real_label, "running": running, "auto_disabled": auto_disabled}, 200


def _is_kill_safe_pid(pid_str, cmd):
    """判断 pid 是否允许从 dashboard 终止。从严：必须命中白名单 + 非系统路径 + 命中用户进程特征。返回 (safe: bool, reason: str)。"""
    info = data.RUNTIME_WHITELIST.get(str(pid_str))
    if not info:
        return False, "pid 不在最近一次 runtime 报告白名单内（可能是系统进程、已退出，或前端伪造）"
    cmd = (cmd or info.get("cmd") or "").strip()
    if (info.get("cmd") or "").strip() and cmd and cmd != info.get("cmd"):
        return False, "cmd 与 runtime 报告不一致"
    cmd_resolved = cmd or info.get("cmd") or ""
    # 禁系统路径 / Apple 系统服务
    sys_prefixes = ("/usr/sbin/", "/usr/libexec/", "/sbin/", "/System/", "/usr/lib/")
    if any(cmd_resolved.startswith(p) or (" " + cmd_resolved).find(" " + p) != -1 for p in sys_prefixes):
        return False, "目标位于系统目录，拒绝终止"
    if "com.apple." in cmd_resolved:
        return False, "目标是 Apple 系统服务，拒绝终止"
    # 禁止动 PID 1 / kernel_task / 自身 dashboard
    try:
        pid_int = int(pid_str)
    except (TypeError, ValueError):
        return False, "pid 非法"
    if pid_int <= 1:
        return False, "拒绝终止系统核心进程"
    # 只允许「解释器跑用户进程」或「路径在 $HOME 下」或「runtime 已归类为用户态 agent/mcp/dev」
    home_str = str(paths.HOME)
    allowed_categories = {"mcp", "dev-server", "agent-daemon", "support"}
    in_home = home_str in cmd_resolved
    cat_ok = (info.get("category") or "") in allowed_categories
    # 解释器特征：node / bun / python / python3 / deno 跑的脚本，且命令里出现 mcp/dev/gateway/agent/watcher/serve
    interp_markers = ("node", "bun", "deno", "python", "python3")
    interp_kw = ("mcp", "dev", "gateway", "agent", "watcher", "serve", "hub", "daemon", "hermes", "context7")
    tokens = cmd_resolved.lower().split()
    interp_ok = any(t in tokens for t in interp_markers) and any(kw in cmd_resolved.lower() for kw in interp_kw)
    if not (in_home or cat_ok or interp_ok):
        return False, "目标不属于用户态 mcp/dev/agent 进程，拒绝终止"
    return True, "ok"


def handle_kill_process(payload):
    """终止单个 runtime 进程。安全模型：白名单 + 禁系统路径 + Host 127.0.0.1（由 server 绑定保证）。返回 (result, http_status)。"""
    pid = str(payload.get("pid") or "")
    mode = str(payload.get("mode") or "term")
    if mode not in {"term", "kill"}:
        return {"ok": False, "error": "非法 mode（仅允许 term/kill）"}, 400
    if not pid:
        return {"ok": False, "error": "缺少 pid"}, 400
    info = data.RUNTIME_WHITELIST.get(pid)
    cmd = (info or {}).get("cmd", "")
    safe, reason = _is_kill_safe_pid(pid, cmd)
    if not safe:
        sys.stderr.write(f"asset-dashboard: kill DENY pid={pid} reason={reason}\n")
        return {"ok": False, "error": reason, "pid": pid}, 403
    # 二次校验：进程还活着吗？取实时 comm 再核对一次路径
    try:
        check = subprocess.run(["ps", "-o", "comm=", "-p", pid], capture_output=True, text=True, timeout=4)
    except Exception as exc:
        return {"ok": False, "error": f"进程状态检查失败：{exc}"}, 500
    live_comm = (check.stdout or "").strip()
    if not live_comm:
        return {"ok": False, "error": "进程已不在（pid 可能已退出）", "pid": pid}, 404
    # 实时 comm 也走一次系统路径检查（防 pid 被复用为系统进程）
    if any(live_comm.startswith(p.rstrip("/")) for p in ("/usr/sbin/", "/usr/libexec/", "/sbin/", "/System/")):
        sys.stderr.write(f"asset-dashboard: kill DENY pid={pid} live_comm={live_comm} (system path)\n")
        return {"ok": False, "error": "实时核对发现目标是系统进程，拒绝终止"}, 403
    signum = "TERM" if mode == "term" else "KILL"
    try:
        proc = subprocess.run(["kill", "-" + signum, pid], capture_output=True, text=True, timeout=6)
    except Exception as exc:
        return {"ok": False, "error": f"发送信号失败：{exc}"}, 500
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return {"ok": False, "error": err or f"kill 退出码 {proc.returncode}", "pid": pid}, 500
    sys.stderr.write(f"asset-dashboard: kill OK pid={pid} mode={mode} cmd={cmd[:120]}\n")
    verb = "已发送 SIGTERM" if mode == "term" else "已发送 SIGKILL"
    return {"ok": True, "pid": pid, "mode": mode, "verb": verb, "cmd": cmd}, 200


def serve(host, port, open_browser=False):
    server = http.server.ThreadingHTTPServer((host, port), DashboardHandler)
    url = f"http://{host}:{port}/"
    html_module.write_dashboard(run_discovery=True, refresh_mcp=False, live=False)
    print(url)
    if open_browser:
        subprocess.run(["/usr/bin/open", url], check=False)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
