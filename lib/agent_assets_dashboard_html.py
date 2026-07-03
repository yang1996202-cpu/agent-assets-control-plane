"""Agent Assets Dashboard — 页面骨架、CSS、JS 与 HTML 组装。

背景：dashboard 最终输出是一个完整的 HTML 文件，包含内联样式、脚本和多个数据板块。
设计意图：把页面模板字符串与「聚合数据 → 生成完整 HTML」的组装逻辑集中于此，
上层 API/入口脚本只需调用 build_dashboard / write_dashboard。
关键约束：
- CSS / JS 作为独立字符串维护，便于阅读和局部调整。
- build_dashboard 负责调用 data 模块收集所有数据，再调用 build_html 拼接页面。
"""

import datetime as dt
import json

import agent_assets_common as lib
import agent_assets_dashboard_data as data
import agent_assets_dashboard_paths as paths
import agent_assets_dashboard_render as render


CSS = """    :root {
      color-scheme: light;
      --bg: #f7f7f4;
      --panel: #ffffff;
      --line: #deded8;
      --text: #1f2328;
      --muted: #6b6f76;
      --soft: #f0f1ed;
      --blue: #2458d3;
      --green: #137333;
      --red: #b42318;
      --amber: #f59e0b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    .shell {
      display: grid;
      grid-template-columns: 200px minmax(0, 1fr);
      min-height: 100vh;
    }
    aside {
      background: #fbfbf8;
      border-right: 1px solid var(--line);
      padding: 20px 14px;
      position: sticky;
      top: 0;
      height: 100vh;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 28px;
      font-weight: 700;
      font-size: 15px;
    }
    .brand-mark {
      width: 32px; height: 32px; border-radius: 8px;
      background: #20242a; color: #fff;
      display: grid; place-items: center;
    }
    .nav button {
      width: 100%;
      border: 0;
      background: transparent;
      padding: 10px 12px;
      border-radius: 8px;
      text-align: left;
      color: var(--text);
      font: inherit;
      cursor: pointer;
      margin-bottom: 4px;
      font-size: 14px;
    }
    .nav button.active { background: #eceee8; font-weight: 650; }
    main { padding: 28px 32px 60px; min-width: 0; }
    h1 { margin: 0 0 6px; font-size: 28px; }
    .sub { color: var(--muted); font-size: 14px; }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
    }
    .btn {
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 8px;
      padding: 8px 16px;
      font: inherit;
      font-size: 14px;
      cursor: pointer;
    }
    .btn.primary { background: var(--blue); color: #fff; border-color: var(--blue); }
    .btn:disabled { opacity: 0.6; cursor: not-allowed; }
    .filter-bar { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
    .filter {
      padding: 6px 14px;
      border-radius: 999px;
      background: #fff;
      border: 1px solid var(--line);
      font-size: 13px;
      cursor: pointer;
    }
    .filter.active { background: #20242a; color: #fff; border-color: #20242a; }
    .card {
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 16px;
    }
    .card-title {
      font-weight: 650;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .alert-card { background: #fffbeb; border-color: #fcd34d; }
    .alert-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .alert-item {
      padding: 14px;
      border-radius: 8px;
      background: #fff;
      border: 1px solid #fcd34d;
      min-height: 80px;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }
    .alert-item.ok { background: #f0fdf4; border-color: #86efac; }
    .alert-item b { display: block; font-size: 26px; }
    .alert-item span { color: var(--muted); font-size: 13px; }
    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }
    .data-table th {
      text-align: left;
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      font-weight: 500;
      font-size: 13px;
    }
    .data-table td {
      padding: 12px 8px;
      border-bottom: 1px solid var(--soft);
      vertical-align: top;
    }
    .data-table tr:hover td { background: #f9f9f7; }
    .section { display: none; min-width: 0; }
    .section.active { display: block; }
    .signal-table { width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 16px; }
    .signal-table caption {
      text-align: left;
      font-weight: 650;
      padding: 10px 0;
      font-size: 15px;
    }
    .signal-table th, .signal-table td {
      text-align: left;
      padding: 10px 8px;
      border-bottom: 1px solid var(--soft);
      vertical-align: top;
    }
    .signal-table th { color: var(--muted); font-weight: 500; font-size: 13px; }
    .signal-table .subtle { color: var(--muted); font-size: 13px; }
    .signal-table .muted { color: var(--muted); }
    .signal-table .ctrl-icon { margin-right: 6px; }
    .runtime-group { margin-bottom: 24px; }
    .runtime-group-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 15px;
      font-weight: 650;
      margin-bottom: 8px;
    }
    .runtime-group-title .muted { color: var(--muted); font-weight: normal; }
    .runtime-group-title .subtle { color: var(--muted); font-weight: normal; font-size: 13px; margin-left: 4px; }
    .runtime-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
      table-layout: fixed;
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .runtime-table th, .runtime-table td {
      padding: 10px 12px;
      border-bottom: 1px solid var(--soft);
      vertical-align: middle;
      text-align: left;
    }
    .runtime-table th {
      background: #fbfbf8;
      color: var(--muted);
      font-weight: 500;
      font-size: 13px;
    }
    .runtime-table tr:last-child td { border-bottom: 0; }
    .runtime-table tr:hover td { background: #f9f9f7; }
    .runtime-table .col-pid { width: 13%; }
    .runtime-table .col-type { width: 7%; }
    .runtime-table .col-ports { width: 14%; }
    .runtime-table .col-cmd { width: 46%; }
    .runtime-table .col-action { width: 20%; }
    .runtime-table td.col-pid { white-space: nowrap; }
    .runtime-table td.col-type { white-space: nowrap; }
    .runtime-table td.col-ports {
      font-family: ui-monospace, monospace;
      font-size: 13px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .runtime-table td.col-cmd code {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 100%;
    }
    .runtime-table td.col-cmd .cwd-chip {
      display: inline-block;
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      vertical-align: middle;
      margin-top: 6px;
    }
    .runtime-table td.col-cmd .cwd-chip b { display: none; }
    .table-action {
      padding: 4px 8px;
      border-radius: 6px;
      border: 1px solid var(--line);
      background: #fff;
      font-size: 12px;
      cursor: pointer;
      margin-right: 4px;
      white-space: nowrap;
    }
    .table-action.danger { border-color: #fca5a5; color: #b42318; }
    .action-cell { white-space: nowrap; }
    .chip {
      display: inline-flex;
      align-items: baseline;
      gap: 6px;
      padding: 4px 10px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--soft);
      text-decoration: none;
      color: inherit;
      font-size: 12px;
      font-family: ui-monospace, monospace;
    }
    .chip b { font-size: 10px; color: var(--muted); font-weight: normal; }
    .cwd-chip { background: #eff6ff; border-color: #bfdbfe; color: #1e40af; margin-left: 6px; }
    .state {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 12px;
    }
    .state-exec { background: #dcfce7; color: #166534; }
    .state-missing { background: #fee2e2; color: #b42318; }
    .state-broken-link { background: #fee2e2; color: #b42318; }
    .state-file, .state-dir { background: #f0f1ed; color: var(--muted); }
    .tag {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 500;
      background: #f0f1ed;
      color: var(--muted);
    }
    .tag.mcp { background: #dcfce7; color: #166534; }
    .tag.agent { background: #f3e8ff; color: #6b21a8; }
    .tag.dev { background: #ffedd5; color: #9a3412; }
    .tag.support { background: #e0f2fe; color: #075985; }
    .tag.system { background: #f3f4f6; color: #374151; }
    .tag.other { background: #f0f1ed; color: var(--muted); }
    .ports-bar { display: flex; gap: 8px; flex-wrap: wrap; }
    .port {
      padding: 6px 12px;
      border-radius: 8px;
      background: var(--soft);
      font-size: 13px;
      font-family: ui-monospace, monospace;
    }
    .muted { color: var(--muted); }
    .refresh-status { color: var(--muted); font-size: 13px; margin-left: 10px; }
    .hidden { display: none; }
    .toggle { color: var(--blue); cursor: pointer; font-size: 13px; margin-left: auto; }
"""


JS = """    (function() {
      const tabs = document.querySelectorAll('.nav button[data-tab]');
      const sections = document.querySelectorAll('.section');
      tabs.forEach(btn => {
        btn.addEventListener('click', () => {
          tabs.forEach(b => b.classList.remove('active'));
          sections.forEach(s => s.classList.remove('active'));
          btn.classList.add('active');
          document.querySelector('section[data-section="' + btn.dataset.tab + '"]').classList.add('active');
        });
      });

      // Runtime filter buttons
      document.querySelectorAll('.runtime-filter-bar .filter').forEach(btn => {
        btn.addEventListener('click', () => {
          document.querySelectorAll('.runtime-filter-bar .filter').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          const filter = btn.dataset.filter;
          document.querySelectorAll('[data-section="runtime"] .searchable').forEach(row => {
            const tags = (row.dataset.filterTags || '').split(/\\s+/);
            let visible = false;
            if (!filter) { visible = true; }
            else if (filter === 'agent-mcp') { visible = tags.includes('mcp') || tags.includes('agent-daemon'); }
            else if (filter === 'dev-server') { visible = tags.includes('dev-server') || tags.includes('zombie'); }
            else if (filter === 'other') { visible = tags.includes('support') || tags.includes('unknown') || tags.includes('system'); }
            row.style.display = visible ? '' : 'none';
          });
        });
      });

      // Refresh runtime
      const refreshBtn = document.getElementById('refresh-runtime');
      const refreshStatus = document.getElementById('refresh-status');
      const updatedSpan = document.getElementById('runtime-updated');
      if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
          refreshBtn.disabled = true;
          refreshStatus.textContent = '刷新中...';
          try {
            const res = await fetch('/api/scan', {method: 'POST'});
            const data = await res.json();
            if (data.ok) {
              window.location.reload();
            } else {
              refreshStatus.textContent = data.error || '刷新失败';
            }
          } catch (e) {
            refreshStatus.textContent = '网络错误';
          } finally {
            refreshBtn.disabled = false;
          }
        });
      }

      // Refresh signals
      const sigRefresh = document.getElementById('refresh-signals');
      const sigStatus = document.getElementById('signals-status');
      if (sigRefresh) {
        sigRefresh.addEventListener('click', () => {
          sigStatus.textContent = '刷新中...';
          window.location.reload();
        });
      }

      // Kill process
      document.querySelectorAll('.js-kill-process').forEach(btn => {
        btn.addEventListener('click', async () => {
          const pid = btn.dataset.pid;
          const mode = btn.dataset.mode;
          if (!pid) return;
          if (!confirm('确认终止 PID ' + pid + '？')) return;
          btn.disabled = true;
          try {
            const res = await fetch('/api/kill-process', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({pid: pid, mode: mode})
            });
            const data = await res.json();
            alert(data.result || data.error || '未知结果');
            window.location.reload();
          } catch (e) {
            alert('请求失败');
          }
        });
      });

      // Launchctl control
      document.querySelectorAll('.js-launchctl').forEach(btn => {
        btn.addEventListener('click', async () => {
          const label = btn.dataset.label;
          const domain = btn.dataset.domain;
          const action = btn.dataset.action;
          if (!label || !action) return;
          btn.disabled = true;
          try {
            const res = await fetch('/api/launchctl', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({label: label, domain: domain, action: action})
            });
            const data = await res.json();
            alert(data.result || data.error || '未知结果');
            window.location.reload();
          } catch (e) {
            alert('请求失败');
          }
        });
      });
    })();
"""


def build_html(
    agent_registry,
    mcp_registry,
    mcp_rows,
    entrypoints,
    health_raw,
    discovered_rows,
    discovered_at,
    discovery_raw,
    mcp_audit,
    project_rows,
    project_at,
    project_meta,
    project_raw="",
    discovered_meta=None,
    signals_rows=None,
    signals_meta=None,
    live=False,
    runtime_data=None,
):
    generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    runtime_updated = render._runtime_updated_at(runtime_data)
    live_attr = "true" if live else "false"
    runtime_section = render.render_runtime_rows(runtime_data) if runtime_data else '<p class="muted">运行态数据未加载。</p>'
    signals_section = render.render_macos_signals_rows(signals_rows) if signals_rows else '<p class="muted">系统信号未加载。</p>'
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>本机运行态</title>
  <style>
{CSS}  </style>
</head>
<body data-live="{lib.h(live_attr)}">
  <div class="shell">
    <aside>
      <div class="brand">
        <div class="brand-mark">RT</div>
        <div>运行态</div>
      </div>
      <nav class="nav">
        <button class="active" data-tab="runtime">运行态</button>
        <button data-tab="signals">系统信号</button>
        <button data-tab="settings">设置</button>
      </nav>
    </aside>
    <main>
      <section class="section active" data-section="runtime">
        <div class="topbar">
          <div>
            <h1>本机运行态</h1>
            <div class="sub">只看现在有什么在跑 · 上次刷新 <span id="runtime-updated">{lib.h(runtime_updated)}</span></div>
          </div>
          <div style="display:flex;align-items:center;gap:10px;">
            <span id="refresh-status" class="refresh-status"></span>
            <button class="btn primary" id="refresh-runtime">刷新</button>
          </div>
        </div>
        {render.render_runtime_filter_bar()}
        {render.render_alert_cards(runtime_data)}
        {runtime_section}
        {render.render_cli_entrypoints(entrypoints)}
      </section>

      <section class="section" data-section="signals">
        <div class="topbar">
          <div>
            <h1>系统信号</h1>
            <div class="sub">launchd / 开机自启 / 登录项 / 后台服务</div>
          </div>
          <div style="display:flex;align-items:center;gap:10px;">
            <span id="signals-status" class="refresh-status"></span>
            <button class="btn primary" id="refresh-signals">刷新</button>
          </div>
        </div>
        {signals_section}
      </section>

      <section class="section" data-section="settings">
        <div class="topbar">
          <div>
            <h1>设置</h1>
            <div class="sub">配置路径与工具信息</div>
          </div>
        </div>
        <div class="card">
          <div class="card-title">配置路径</div>
          <table class="data-table">
            <tbody>
              <tr><td>registry</td><td>{lib.chip(str(paths.REGISTRY))}</td></tr>
              <tr><td>MCP registry</td><td>{lib.chip(str(paths.MCP_REGISTRY))}</td></tr>
              <tr><td>stable bin</td><td>{lib.chip(str(paths.STABLE_BIN_DIR))}</td></tr>
              <tr><td>projects</td><td>{lib.chip(str(paths.PROJECTS_DIR))}</td></tr>
            </tbody>
          </table>
        </div>
        <div class="card">
          <div class="card-title">关于</div>
          <p class="muted">Agent Assets Control Plane · 本机运行态观测台</p>
          <p class="muted">生成时间：{lib.h(generated)}</p>
        </div>
      </section>
    </main>
  </div>
  <script>
{JS}  </script>
</body>
</html>
"""


def build_dashboard(run_discovery=True, refresh_mcp=True, run_projects=True, live=False, discovery_mode="daily"):
    agent_registry = lib.load_json(paths.REGISTRY)
    mcp_registry = lib.load_json(paths.MCP_REGISTRY)
    discovery_raw = data.refresh_discovery(mode=discovery_mode) if run_discovery else ""
    project_raw = data.refresh_projects() if run_projects else ""
    discovered_rows, discovered_at, discovered_meta = data.collect_discovered()
    project_rows, project_at, project_meta = data.collect_projects()
    signals_raw = lib.load_json(paths.MACOS_SIGNALS) if paths.MACOS_SIGNALS.exists() else {}
    signals_rows = signals_raw.get("items", []) if isinstance(signals_raw, dict) else []
    signals_meta = dict(signals_raw.get("summary", {}) if isinstance(signals_raw, dict) else {})
    _raw = signals_raw.get("raw", {}) if isinstance(signals_raw, dict) else {}
    signals_meta["login_items"] = _raw.get("login_items", []) if isinstance(_raw, dict) else []
    _sext = _raw.get("system_extensions") if isinstance(_raw, dict) else None
    signals_meta["system_extensions"] = (_sext or {}).get("extensions", []) if isinstance(_sext, dict) else []
    for _row in signals_rows:
        role = _row.get("launch_role")
        plist = _row.get("launch_plist") or ""
        if plist:
            _row["_signal_kind"] = {"user-agent": "launchd·用户级", "system-daemon": "launchd·系统级", "global-agent": "launchd·全局级"}.get(role, "launchd")
            _row["_control"] = "user-launchd" if role == "user-agent" else "system-launchd"
        elif _row.get("listeners"):
            _row["_signal_kind"] = "监听端口"
            _row["_control"] = "app-running"
        elif _row.get("running"):
            _row["_signal_kind"] = "后台进程"
            _row["_control"] = "app-running"
        else:
            _row["_signal_kind"] = "登录项/已停"
            _row["_control"] = "login-item"
        _row["_human"] = render.humanize_signal(_row)
        _row["_safe"] = render.is_safe_to_control(_row)
    runtime_data = data.collect_runtime()
    if refresh_mcp:
        health, health_raw = data.parse_claude_mcp_health()
    else:
        health, health_raw = data.cached_mcp_health("MCP health cache. Click one-key scan to refresh.")
    mcp_rows = data.collect_mcp(mcp_registry, health)
    mcp_audit = data.build_mcp_audit(agent_registry, mcp_registry, mcp_rows)
    entrypoints = data.collect_entrypoints(agent_registry)
    html_text = build_html(
        agent_registry,
        mcp_registry,
        mcp_rows,
        entrypoints,
        health_raw,
        discovered_rows,
        discovered_at,
        discovery_raw,
        mcp_audit,
        project_rows,
        project_at,
        project_meta,
        project_raw,
        discovered_meta,
        signals_rows,
        signals_meta,
        live=live,
        runtime_data=runtime_data,
    )
    project_summary = project_meta.get("summary", {})
    assets = agent_registry.get("assets", {})
    agent_app_count = 0
    agent_host_count = 0
    agent_subject_count = 0
    for asset in assets.values():
        categories = set(lib.listify(asset.get("category")))
        is_agent_app = "agent-app" in categories
        is_agent_host = "agent-host" in categories
        if is_agent_app:
            agent_app_count += 1
        if is_agent_host:
            agent_host_count += 1
        if is_agent_app or is_agent_host:
            agent_subject_count += 1
    needs_review = sum(1 for row in discovered_rows if not row.get("registered") and row.get("review_status", "new") == "new")
    summary = {
        "assets": len(assets),
        "agent_subjects": agent_subject_count,
        "agent_apps": agent_app_count,
        "agent_hosts": agent_host_count,
        "decision_count": needs_review,
        "projects": project_summary.get("total", len(project_rows)),
        "project_canonical": project_summary.get("canonical", 0),
        "project_legacy": project_summary.get("legacy", 0),
        "project_download_candidate": project_summary.get("download_candidate", 0),
        "project_host_managed": project_summary.get("host_managed", 0),
        "project_linked": project_summary.get("linked", 0),
        "project_unlinked": sum(1 for row in project_rows if not row.get("linked_assets")),
        "projects_updated_at": project_at,
        "mcp_total": len(mcp_rows),
        "mcp_connected": sum(1 for row in mcp_rows if row["state"] == "connected"),
        "entrypoints": len(entrypoints),
        "valid_entrypoints": sum(1 for row in entrypoints if row["state"] in {"exec", "file", "dir"}),
        "candidates": len(discovered_rows),
        "unregistered": sum(1 for row in discovered_rows if not row.get("registered")),
        "needs_review": needs_review,
        "deferred": sum(1 for row in discovered_rows if not row.get("registered") and row.get("review_status") == "defer"),
        "ignored": sum(1 for row in discovered_rows if not row.get("registered") and row.get("review_status") == "ignore"),
        "discovered_at": discovered_at,
        "scan_mode": discovered_meta.get("scan_mode", "daily"),
        "mcp_host_only": mcp_audit["summary"]["host_only"],
        "mcp_registry_only": mcp_audit["summary"]["registry_only"],
    }
    return html_text, summary


def write_dashboard(run_discovery=True, refresh_mcp=True, run_projects=True, live=False):
    html_text, summary = build_dashboard(run_discovery=run_discovery, refresh_mcp=refresh_mcp, run_projects=run_projects, live=live)
    paths.OUT.parent.mkdir(parents=True, exist_ok=True)
    paths.OUT.write_text(html_text, encoding="utf-8")
    return summary


def run_crosscheck():
    summary = write_dashboard(run_discovery=False, refresh_mcp=False, run_projects=False, live=False)
    return {
        "ok": True,
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "assets": summary.get("assets", 0),
        "projects": summary.get("projects", 0),
        "project_unlinked": summary.get("project_unlinked", 0),
        "mcp_delta": summary.get("mcp_host_only", 0) + summary.get("mcp_registry_only", 0),
        "mcp_host_only": summary.get("mcp_host_only", 0),
        "mcp_registry_only": summary.get("mcp_registry_only", 0),
        "needs_review": summary.get("needs_review", 0),
    }


def run_scan(include_versions=False, mode="daily"):
    discovery_raw = data.refresh_discovery(include_versions=include_versions, mode=mode)
    discovered_rows, discovered_at, discovered_meta = data.collect_discovered()
    mcp_registry = lib.load_json(paths.MCP_REGISTRY)
    health, health_raw = data.parse_claude_mcp_health()
    mcp_rows = data.collect_mcp(mcp_registry, health)
    write_dashboard(run_discovery=False, refresh_mcp=False, run_projects=False, live=False)
    return {
        "ok": True,
        "updated_at": discovered_at,
        "scan_mode": discovered_meta.get("scan_mode", mode),
        "candidates": len(discovered_rows),
        "unregistered": sum(1 for row in discovered_rows if not row.get("registered")),
        "needs_review": sum(1 for row in discovered_rows if not row.get("registered") and row.get("review_status", "new") == "new"),
        "deferred": sum(1 for row in discovered_rows if not row.get("registered") and row.get("review_status") == "defer"),
        "ignored": sum(1 for row in discovered_rows if not row.get("registered") and row.get("review_status") == "ignore"),
        "mcp_total": len(mcp_rows),
        "mcp_connected": sum(1 for row in mcp_rows if row["state"] == "connected"),
        "discovery_output": discovery_raw,
        "mcp_output": health_raw,
    }


def run_project_scan():
    project_raw = data.refresh_projects()
    project_rows, project_at, project_meta = data.collect_projects()
    write_dashboard(run_discovery=False, refresh_mcp=False, run_projects=False, live=False)
    summary = project_meta.get("summary", {})
    return {
        "ok": True,
        "updated_at": project_at,
        "projects": summary.get("total", len(project_rows)),
        "canonical": summary.get("canonical", 0),
        "legacy": summary.get("legacy", 0),
        "download_candidate": summary.get("download_candidate", 0),
        "host_managed": summary.get("host_managed", 0),
        "linked": summary.get("linked", 0),
        "output": project_raw,
    }


def run_reconcile(mode="daily"):
    if mode not in {"daily", "deep"}:
        mode = "daily"
    discovery_raw = data.refresh_discovery(mode=mode)
    project_raw = data.refresh_projects()
    health, health_raw = data.parse_claude_mcp_health()
    discovered_rows, discovered_at, discovered_meta = data.collect_discovered()
    project_rows, project_at, project_meta = data.collect_projects()
    mcp_registry = lib.load_json(paths.MCP_REGISTRY)
    mcp_rows = data.collect_mcp(mcp_registry, health)
    write_dashboard(run_discovery=False, refresh_mcp=False, run_projects=False, live=False)
    return {
        "ok": True,
        "scan_mode": discovered_meta.get("scan_mode", mode),
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "candidates": len(discovered_rows),
        "unregistered": sum(1 for row in discovered_rows if not row.get("registered")),
        "projects": project_meta.get("summary", {}).get("total", len(project_rows)),
        "projects_updated_at": project_at,
        "mcp_total": len(mcp_rows),
        "mcp_connected": sum(1 for row in mcp_rows if row["state"] == "connected"),
        "discovered_at": discovered_at,
        "discovery_output": discovery_raw,
        "project_output": project_raw,
        "mcp_output": health_raw,
    }
