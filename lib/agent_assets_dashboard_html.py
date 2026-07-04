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
    main { padding: 28px 32px 60px; min-width: 0; overflow-x: auto; }
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
    .alert-banner {
      background: #fff7ed;
      border: 1px solid #fdba74;
      border-radius: 10px;
      padding: 12px 16px;
      margin-bottom: 16px;
      color: #9a3412;
      font-size: 14px;
    }
    .toast {
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 9999;
      max-width: 360px;
      padding: 12px 16px;
      border-radius: 10px;
      font-size: 14px;
      color: #1f2328;
      background: #fff;
      border: 1px solid var(--line);
      box-shadow: 0 4px 20px rgba(0,0,0,0.12);
      opacity: 0;
      transform: translateY(-10px);
      transition: opacity 0.2s, transform 0.2s;
      pointer-events: none;
    }
    .toast.show { opacity: 1; transform: translateY(0); }
    .toast-ok { background: #f0fdf4; border-color: #86efac; color: #14532d; }
    .toast-err { background: #fef2f2; border-color: #fecaca; color: #7f1d1d; }
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
    .action-log-table { table-layout: fixed; }
    .action-log-table .col-time { width: 16%; white-space: nowrap; }
    .action-log-table .col-action { width: 12%; }
    .action-log-table .col-target { width: 20%; word-break: break-word; }
    .action-log-table .col-mode { width: 12%; }
    .action-log-table .col-result { width: 25%; }
    .action-log-table .col-undo { width: 15%; }
    .log-status {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
    }
    .log-status.ok { background: #e1f5e8; color: var(--green); }
    .log-status.err { background: #fde8e6; color: var(--red); }
    .log-detail {
      margin-top: 6px;
      font-size: 13px;
    }
    .log-detail summary {
      color: var(--blue);
      cursor: pointer;
      user-select: none;
    }
    .log-detail pre {
      margin: 6px 0 0;
      padding: 8px;
      background: #f6f6f3;
      border-radius: 6px;
      white-space: pre-wrap;
      word-break: break-word;
      color: var(--text);
      font-size: 12px;
    }
    .section { display: none; min-width: 0; overflow-x: auto; }
    .section.active { display: block; }
    .signal-table { width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 16px; table-layout: fixed; }
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
      vertical-align: middle;
    }
    .signal-table th { color: var(--muted); font-weight: 500; font-size: 13px; }
    .signal-table .subtle { color: var(--muted); font-size: 13px; }
    .signal-table .muted { color: var(--muted); }
    .signal-table .ctrl-icon { margin-right: 6px; }
    .signal-table .col-name { width: 24%; }
    .signal-table .col-type { width: 10%; }
    .signal-table .col-state { width: 9%; }
    .signal-table .col-resource { width: 14%; font-size: 13px; white-space: nowrap; }
    .signal-table .col-ports { width: 11%; white-space: nowrap; }
    .signal-table .col-linked { width: 12%; white-space: nowrap; }
    .signal-table .action-cell { width: 20%; white-space: nowrap; }
    .signal-table .col-linked .chip {
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      display: inline-block;
      vertical-align: middle;
      white-space: nowrap;
    }
    .signal-table .linked-more {
      display: inline-block;
      padding: 1px 5px;
      border-radius: 999px;
      background: var(--soft);
      font-size: 11px;
      color: var(--muted);
      vertical-align: middle;
      margin-left: 4px;
      white-space: nowrap;
    }
    .signal-table td:first-child { word-break: break-word; }
    .signal-table td:first-child > div { margin-bottom: 2px; }
    .signal-table td:first-child .plist-path { font-family: ui-monospace, monospace; font-size: 12px; }
    .signal-table .signal-group-header td {
      background: #f9f9f7;
      padding: 8px;
      font-weight: 600;
      color: var(--text);
      border-bottom: 1px solid var(--soft);
    }
    .signal-table .signal-group-header + tr td { padding-top: 8px; }
    .signal-table .group-subname { font-family: ui-monospace, monospace; font-size: 12px; }
    .signal-table th.sortable {
      cursor: pointer; user-select: none;
    }
    .signal-table th.sortable::after {
      content: "↕"; color: var(--muted); font-size: 11px; margin-left: 4px;
    }
    .signal-table th.sortable.asc::after { content: "↑"; }
    .signal-table th.sortable.desc::after { content: "↓"; }
    .signal-table th.sortable.asc,
    .signal-table th.sortable.desc { color: var(--text); }
    .action-stack { display: inline-flex; flex-direction: column; gap: 3px; align-items: flex-start; }
    .action-stack .table-action { white-space: nowrap; }
    .auto-state {
      display: inline-block;
      padding: 1px 5px;
      border-radius: 4px;
      font-size: 11px;
      white-space: nowrap;
      line-height: 1.2;
    }
    .auto-state.on { background: #dcfce7; color: #166534; }
    .auto-state.off { background: #fee2e2; color: #b42318; }
    .cli-group {
      margin-bottom: 16px;
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 10px;
      overflow: hidden;
    }
    .cli-group summary {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 14px;
      font-size: 15px;
      font-weight: 650;
      cursor: pointer;
      list-style: none;
      user-select: none;
    }
    .cli-group summary::-webkit-details-marker { display: none; }
    .cli-group table { border-top: 1px solid var(--line); }
    .runtime-group {
      margin-bottom: 16px;
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 10px;
      overflow: hidden;
    }
    .runtime-group summary {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 15px;
      font-weight: 650;
      padding: 12px 14px;
      cursor: pointer;
      list-style: none;
      user-select: none;
    }
    .runtime-group summary::-webkit-details-marker { display: none; }
    .runtime-group-title .muted { color: var(--muted); font-weight: normal; }
    .runtime-group-title .subtle { color: var(--muted); font-weight: normal; font-size: 13px; margin-left: 4px; }
    .runtime-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
      table-layout: fixed;
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
    .runtime-table .col-pid { width: 12%; }
    .runtime-table .col-type { width: 7%; }
    .runtime-table .col-ports { width: 13%; }
    .runtime-table .col-rss { width: 9%; }
    .runtime-table .col-cmd { width: 42%; }
    .runtime-table .col-action { width: 17%; }
    .runtime-table td.col-pid { white-space: nowrap; }
    .runtime-table td.col-type { white-space: nowrap; }
    .runtime-table td.col-rss { white-space: nowrap; text-align: right; }
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
    .tag.app { background: #fef3c7; color: #92400e; }
    .tag.other { background: #f0f1ed; color: var(--muted); }
    .ports-bar { display: flex; gap: 8px; flex-wrap: wrap; }
    .port {
      padding: 6px 12px;
      border-radius: 8px;
      background: var(--soft);
      font-size: 13px;
      font-family: ui-monospace, monospace;
    }
    .processes-panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 10px;
      overflow: hidden;
      margin-bottom: 16px;
    }
    .memory-summary {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 16px;
    }
    .memory-summary-head {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 14px;
    }
    .memory-summary-head h4 {
      margin: 0 0 4px;
      font-size: 15px;
      font-weight: 650;
    }
    .memory-total {
      font-size: 20px;
      font-weight: 700;
    }
    .memory-availability {
      font-size: 14px;
      color: var(--green);
      font-weight: 600;
    }
    .memory-bars {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px 24px;
      margin-bottom: 12px;
    }
    .mem-bar-row {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 13px;
    }
    .mem-bar-label {
      flex: 0 0 5.5em;
      color: var(--muted);
    }
    .mem-bar-track {
      flex: 1;
      height: 8px;
      background: var(--soft);
      border-radius: 4px;
      overflow: hidden;
    }
    .mem-bar-fill {
      height: 100%;
      border-radius: 4px;
    }
    .mem-bar-fill.app { background: #60a5fa; }
    .mem-bar-fill.wired { background: #a78bfa; }
    .mem-bar-fill.compressed { background: #f87171; }
    .mem-bar-fill.cached { background: #fbbf24; }
    .mem-bar-fill.uncovered { background: #9ca3af; }
    .mem-bar-fill.free { background: #86efac; }
    .mem-bar-value {
      flex: 0 0 4.5em;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .memory-hint {
      font-size: 12px;
      line-height: 1.5;
      margin: 0;
    }
    .top-processors {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 16px;
    }
    .top-processors h4 {
      margin: 0 0 12px;
      font-size: 14px;
      font-weight: 650;
      color: var(--text);
    }
    .top-proc-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }
    .top-proc-col {
      min-width: 0;
    }
    .top-proc-item {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 10px;
    }
    .top-proc-name {
      flex: 0 0 38%;
      font-size: 13px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--text);
    }
    .top-proc-item .usage-cell {
      flex: 1;
      min-width: 0;
    }
    .system-processes-table { width: 100%; border-collapse: collapse; font-size: 14px; }
    .system-processes-table th {
      text-align: left; padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      background: #fbfbf8;
      color: var(--muted); font-weight: 500; font-size: 13px;
    }
    .system-processes-table td {
      padding: 10px 12px; border-bottom: 1px solid var(--soft); vertical-align: middle;
    }
    .system-processes-table tr:last-child td { border-bottom: 0; }
    .system-processes-table tr:hover td { background: #f9f9f7; }
    .system-processes-table .col-name { width: 44%; }
    .system-processes-table .col-cpu { width: 16%; }
    .system-processes-table .col-rss { width: 16%; }
    .system-processes-table .col-type { width: 10%; }
    .system-processes-table .col-action { width: 14%; }
    .system-processes-table .col-name strong {
      display: block; font-weight: 650; font-size: 14.5px;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%;
    }
    .system-processes-table .pid-hint {
      display: block; font-size: 12px; color: var(--muted); margin-top: 2px;
      font-variant-numeric: tabular-nums;
    }
    .system-processes-table th.sortable {
      cursor: pointer; user-select: none;
    }
    .system-processes-table th.sortable::after {
      content: "↕"; color: var(--muted); font-size: 11px; margin-left: 4px;
    }
    .system-processes-table th.sortable.asc::after { content: "↑"; }
    .system-processes-table th.sortable.desc::after { content: "↓"; }
    .system-processes-table th.sortable.asc,
    .system-processes-table th.sortable.desc {
      color: var(--text); font-weight: 650; background: #eceee8;
    }
    .usage-cell {
      display: flex; align-items: center; gap: 8px;
      min-width: 80px;
    }
    .usage-bar {
      flex: 1;
      height: 6px;
      background: var(--soft);
      border-radius: 3px;
      overflow: hidden;
      min-width: 40px;
    }
    .usage-bar-fill {
      height: 100%;
      border-radius: 3px;
      transition: width 0.2s;
    }
    .usage-bar.cpu .usage-bar-fill { background: #93c5fd; }
    .usage-bar.mem .usage-bar-fill { background: #86efac; }
    .usage-value {
      font-size: 12px; color: var(--muted);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
      min-width: 3.5em; text-align: right;
    }
    .muted { color: var(--muted); }
    .refresh-status { color: var(--muted); font-size: 13px; margin-left: 10px; }
    .hidden { display: none; }
    .toggle { color: var(--blue); cursor: pointer; font-size: 13px; margin-left: auto; }
"""


JS = """    (function() {
      // 强制绕过浏览器缓存重新加载页面；location.reload() 在某些浏览器/场景下仍会读缓存。
      function hardReload() {
        var base = location.href.split('?')[0];
        var hash = location.hash || '';
        location.href = base + '?_t=' + Date.now() + hash;
      }
      function showToast(message, type) {
        const toast = document.createElement('div');
        toast.className = 'toast ' + (type ? 'toast-' + type : '');
        toast.textContent = message;
        document.body.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('show'));
        setTimeout(() => {
          toast.classList.remove('show');
          setTimeout(() => toast.remove(), 200);
        }, 3000);
      }
      const tabs = document.querySelectorAll('.nav button[data-tab]');
      const sections = document.querySelectorAll('.section');
      function switchTab(tabName, updateHash) {
        const targetBtn = Array.from(tabs).find(b => b.dataset.tab === tabName);
        const targetSection = document.querySelector('section[data-section="' + tabName + '"]');
        if (!targetBtn || !targetSection) return;
        tabs.forEach(b => b.classList.remove('active'));
        sections.forEach(s => s.classList.remove('active'));
        targetBtn.classList.add('active');
        targetSection.classList.add('active');
        if (updateHash !== false) {
          history.replaceState(null, '', '#tab=' + tabName);
        }
      }
      tabs.forEach(btn => {
        btn.addEventListener('click', () => {
          switchTab(btn.dataset.tab);
        });
      });
      // 页面加载时根据 URL hash 恢复 tab
      (function() {
        const m = location.hash.match(/^#tab=([a-z-]+)$/);
        if (m && m[1]) {
          switchTab(m[1], false);
        }
      })();

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
            else if (filter === 'mcp') { visible = tags.includes('mcp'); }
            else if (filter === 'agent-daemon') { visible = tags.includes('agent-daemon'); }
            else if (filter === 'dev-server') { visible = tags.includes('dev-server') || tags.includes('zombie'); }
            else if (filter === 'support-system') { visible = tags.includes('support') || tags.includes('system'); }
            else if (filter === 'other') { visible = tags.includes('unknown'); }
            row.style.display = visible ? '' : 'none';
          });
          // 隐藏无可见行的分组
          document.querySelectorAll('.runtime-group').forEach(g => {
            const visibleRows = g.querySelectorAll('.searchable:not([style*="display: none"])');
            g.style.display = visibleRows.length ? '' : 'none';
          });
        });
      });

      // CLI filter buttons
      document.querySelectorAll('.cli-filter-bar .filter').forEach(btn => {
        btn.addEventListener('click', () => {
          document.querySelectorAll('.cli-filter-bar .filter').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          const filter = btn.dataset.filter;
          document.querySelectorAll('.cli-table .searchable[data-section="cli"]').forEach(row => {
            const tags = (row.dataset.filterTags || '').split(/\\s+/);
            const visible = !filter || tags.includes(filter);
            row.style.display = visible ? '' : 'none';
          });
        });
      });

      // Signals filter buttons
      document.querySelectorAll('.signals-filter-bar .filter').forEach(btn => {
        btn.addEventListener('click', () => {
          document.querySelectorAll('.signals-filter-bar .filter').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          applySignalsFilter();
        });
      });

      // System processes filter buttons
      function applySystemProcessesFilter(filter) {
        document.querySelectorAll('.system-processes-table .searchable[data-section="system-processes"]').forEach(el => {
          const tags = (el.dataset.filterTags || '').split(/\\s+/);
          const visible = !filter || filter === 'user' ? tags.includes('user') : tags.includes(filter);
          el.style.display = visible ? '' : 'none';
        });
      }
      document.querySelectorAll('.system-processes-filter-bar .filter').forEach(btn => {
        btn.addEventListener('click', () => {
          document.querySelectorAll('.system-processes-filter-bar .filter').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          applySystemProcessesFilter(btn.dataset.filter);
        });
      });
      // 页面加载时应用默认筛选（通常是「用户进程」）
      (function() {
        const activeBtn = document.querySelector('.system-processes-filter-bar .filter.active');
        if (activeBtn) applySystemProcessesFilter(activeBtn.dataset.filter);
      })();

      // System processes table sorting
      document.querySelectorAll('.system-processes-table th.sortable').forEach(th => {
        th.addEventListener('click', () => {
          const table = th.closest('table');
          const tbody = table.querySelector('tbody');
          const rows = Array.from(tbody.querySelectorAll('tr'));
          const sortKey = th.dataset.sort;
          const currentDir = th.classList.contains('asc') ? 'asc' : (th.classList.contains('desc') ? 'desc' : '');
          const nextDir = currentDir === 'asc' ? 'desc' : 'asc';
          table.querySelectorAll('th.sortable').forEach(h => h.classList.remove('asc', 'desc'));
          th.classList.add(nextDir);

          const getValue = (row) => {
            if (sortKey === 'name') {
              const cell = row.querySelector('.col-name strong');
              return (cell ? cell.textContent : '').toLowerCase();
            }
            const cell = row.querySelector(`.col-${sortKey}`);
            if (!cell) return 0;
            const val = parseFloat(cell.dataset.sortValue);
            return isNaN(val) ? 0 : val;
          };

          rows.sort((a, b) => {
            let va = getValue(a), vb = getValue(b);
            if (va < vb) return nextDir === 'asc' ? -1 : 1;
            if (va > vb) return nextDir === 'asc' ? 1 : -1;
            return 0;
          });

          rows.forEach(row => tbody.appendChild(row));
        });
      });

      function applySignalsFilter() {
        const controlFilter = (document.querySelector('.signals-filter-bar .filter.active') || {}).dataset.filter || '';
        document.querySelectorAll('.signal-table').forEach(table => {
          const control = table.dataset.control || '';
          const controlMatch = !controlFilter || control === controlFilter;
          let hasVisibleRow = false;
          table.querySelectorAll('.searchable[data-section="signals"]').forEach(row => {
            const visible = controlMatch;
            row.style.display = visible ? '' : 'none';
            if (visible) hasVisibleRow = true;
          });
          table.style.display = controlMatch && hasVisibleRow ? '' : 'none';
        });
      }

      // Signal table sorting (name / type / state / resource)
      document.querySelectorAll('.signal-table th.sortable').forEach(th => {
        th.addEventListener('click', () => {
          const table = th.closest('table');
          const tbody = table.querySelector('tbody');
          const rows = Array.from(tbody.querySelectorAll('tr'));
          const sortKey = th.dataset.sort;
          const currentDir = th.classList.contains('asc') ? 'asc' : (th.classList.contains('desc') ? 'desc' : '');
          const nextDir = currentDir === 'asc' ? 'desc' : 'asc';
          table.querySelectorAll('th.sortable').forEach(h => h.classList.remove('asc', 'desc'));
          th.classList.add(nextDir);

          const getValue = (row) => {
            if (row.classList.contains('signal-group-header')) return '';
            if (sortKey === 'name') {
              const cell = row.querySelector('.col-name strong, .col-name .group-subname');
              return (cell ? cell.textContent : '').toLowerCase();
            }
            if (sortKey === 'type') {
              const cell = row.querySelector('.col-type');
              return (cell ? cell.textContent : '').toLowerCase();
            }
            const cell = row.querySelector(`.col-${sortKey}`);
            if (!cell) return 0;
            const val = parseFloat(cell.dataset.sortValue);
            return isNaN(val) ? 0 : val;
          };

          rows.sort((a, b) => {
            let va = getValue(a), vb = getValue(b);
            if (va < vb) return nextDir === 'asc' ? -1 : 1;
            if (va > vb) return nextDir === 'asc' ? 1 : -1;
            return 0;
          });

          rows.forEach(row => tbody.appendChild(row));
        });
      });

      // Generic filter-chip buttons (CLI, assets, projects, etc.)
      document.querySelectorAll('.filter-chip').forEach(btn => {
        btn.addEventListener('click', () => {
          const section = btn.dataset.filterSection;
          const filter = btn.dataset.filter;
          const container = btn.closest('.card') || document.querySelector('section[data-section="' + section + '"]');
          if (!container) return;
          container.querySelectorAll('.filter-chip[data-filter-section="' + section + '"]').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          container.querySelectorAll('.searchable[data-section="' + section + '"]').forEach(row => {
            const tags = (row.dataset.filterTags || '').split(/\\s+/);
            const visible = !filter || tags.includes(filter);
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
              hardReload();
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

      // Refresh all data sources
      const refreshAllBtn = document.getElementById('refresh-all');
      if (refreshAllBtn) {
        refreshAllBtn.addEventListener('click', async () => {
          refreshAllBtn.disabled = true;
          refreshStatus.textContent = '全量刷新中（可能需几十秒）...';
          try {
            const res = await fetch('/api/refresh-all', {method: 'POST'});
            const data = await res.json();
            if (data.ok) {
              hardReload();
            } else {
              refreshStatus.textContent = data.error || '刷新失败';
            }
          } catch (e) {
            refreshStatus.textContent = '网络错误';
          } finally {
            refreshAllBtn.disabled = false;
          }
        });
      }

      // Refresh signals
      const sigRefresh = document.getElementById('refresh-signals');
      const sigStatus = document.getElementById('signals-status');
      if (sigRefresh) {
        sigRefresh.addEventListener('click', () => {
          sigStatus.textContent = '刷新中...';
          hardReload();
        });
      }

      // Kill process
      document.querySelectorAll('.js-kill-process').forEach(btn => {
        btn.addEventListener('click', async () => {
          const pid = btn.dataset.pid;
          const mode = btn.dataset.mode;
          const cmd = btn.dataset.cmd || '';
          if (!pid) return;
          let confirmMsg = '确认终止 PID ' + pid + '？';
          if (pid.startsWith('[')) {
            try {
              const pids = JSON.parse(pid);
              confirmMsg = '确认终止「' + cmd + '」下的 ' + pids.length + ' 个进程？';
            } catch (e) {
              confirmMsg = '确认终止该进程组？';
            }
          }
          if (!confirm(confirmMsg)) return;
          btn.disabled = true;
          try {
            const res = await fetch('/api/kill-process', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({pid: pid, mode: mode})
            });
            const data = await res.json();
            if (data.ok) {
              showToast(data.verb || '操作成功', 'ok');
            } else {
              showToast(data.error || '操作失败', 'err');
            }
            hardReload();
          } catch (e) {
            showToast('请求失败', 'err');
          }
        });
      });

      // Poll /api/status until the backend signals refresh has completed.
      function waitForSignalsRefresh(startedAt, maxWaitMs, intervalMs) {
        maxWaitMs = maxWaitMs || 12000;
        intervalMs = intervalMs || 800;
        return new Promise(function(resolve) {
          var deadline = Date.now() + maxWaitMs;
          function check() {
            fetch('/api/status')
              .then(function(res) { return res.json(); })
              .then(function(status) {
                var ts = status.last_signals_refresh_at;
                if (ts && new Date(ts).getTime() > startedAt) {
                  resolve({ok: true, refreshed: true});
                  return;
                }
                if (Date.now() >= deadline) {
                  resolve({ok: true, refreshed: false, timeout: true});
                  return;
                }
                setTimeout(check, intervalMs);
              })
              .catch(function() {
                if (Date.now() >= deadline) {
                  resolve({ok: true, refreshed: false, timeout: true});
                  return;
                }
                setTimeout(check, intervalMs);
              });
          }
          check();
        });
      }

      async function handleLaunchctl(btn, payload) {
        var action = btn.dataset.action;
        var plist = btn.dataset.plist;
        var label = btn.dataset.label;
        if (!action || (!plist && !label)) {
          showToast('缺少服务标识，无法操作', 'err');
          return;
        }
        btn.disabled = true;
        showToast('操作中...', '');
        var opStarted = Date.now();
        try {
          const res = await fetch('/api/launchctl', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
          });
          const data = await res.json();
          if (data.ok) {
            var msg = data.action_zh || '操作成功';
            if (data.keep_alive) {
              msg += '（KeepAlive 服务停止后可能自动重启）';
            }
            showToast('操作成功，正在刷新状态...', 'ok');
            await waitForSignalsRefresh(opStarted);
            hardReload();
          } else {
            showToast(data.error || '操作失败', 'err');
            btn.disabled = false;
          }
        } catch (e) {
          showToast('请求失败', 'err');
          btn.disabled = false;
        }
      }

      // Launchctl control
      document.querySelectorAll('.js-launchctl').forEach(btn => {
        btn.addEventListener('click', () => {
          handleLaunchctl(btn, {
            plist: btn.dataset.plist,
            label: btn.dataset.label,
            action: btn.dataset.action
          });
        });
      });

      // Undo launchctl from action log
      document.querySelectorAll('.js-launchctl-undo').forEach(btn => {
        btn.addEventListener('click', async () => {
          const plist = btn.dataset.plist;
          const action = btn.dataset.action;
          if (!plist || !action) return;
          if (!confirm('确认撤销这条 launchctl 操作？')) return;
          await handleLaunchctl(btn, {plist: plist, action: action});
        });
      });

      // Clear action log
      document.querySelectorAll('.js-clear-action-log').forEach(btn => {
        btn.addEventListener('click', async () => {
          if (!confirm('确定要清空所有操作记录吗？此操作不可恢复。')) return;
          btn.disabled = true;
          try {
            const res = await fetch('/api/clear-action-log', {method: 'POST'});
            const data = await res.json();
            if (data.ok) {
              showToast('操作记录已清空', 'ok');
            } else {
              showToast(data.error || '清空失败', 'err');
            }
            hardReload();
          } catch (e) {
            showToast('请求失败', 'err');
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
    all_processes=None,
    system_memory=None,
):
    generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    runtime_updated = render._runtime_updated_at(runtime_data)
    live_attr = "true" if live else "false"
    runtime_section = render.render_runtime_rows(runtime_data) if runtime_data else '<p class="muted">运行态数据未加载。</p>'
    signals_refresh_error = (signals_meta or {}).get("_refresh_error", "")
    signals_error_banner = f'<div class="alert-banner">⚠️ 系统信号刷新失败：{lib.h(signals_refresh_error)}</div>' if signals_refresh_error else ""
    signals_section = signals_error_banner + (render.render_macos_signals_rows(signals_rows, process_list=all_processes) if signals_rows else '<p class="muted">系统信号未加载。</p>')
    cli_section = render.render_cli_section(entrypoints)
    action_log_section = render.render_action_log()
    system_processes_section = render.render_system_processes_rows(all_processes, mem_stats=system_memory) if all_processes is not None else '<p class="muted">系统进程数据未加载。</p>'
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate, max-age=0">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
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
        <button data-tab="system-processes">系统进程</button>
        <button data-tab="cli">CLI 工具</button>
        <button data-tab="log">操作记录</button>
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
            <button class="btn" id="refresh-all" title="重新采集 runtime、系统信号、发现候选、项目索引">刷新全部</button>
            <button class="btn primary" id="refresh-runtime">刷新运行态</button>
          </div>
        </div>
        {render.render_runtime_filter_bar(runtime_data)}
        {render.render_alert_cards(runtime_data)}
        {runtime_section}
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

      <section class="section" data-section="system-processes">
        <div class="topbar">
          <div>
            <h1>系统进程</h1>
            <div class="sub">本机所有运行中进程 · 按内存占用排序</div>
          </div>
        </div>
        {system_processes_section}
      </section>

      <section class="section" data-section="cli">
        <div class="topbar">
          <div>
            <h1>CLI 工具</h1>
            <div class="sub">本机已登记或可执行的命令行入口</div>
          </div>
        </div>
        {cli_section}
      </section>

      <section class="section" data-section="log">
        <div class="topbar">
          <div>
            <h1>操作记录</h1>
            <div class="sub">你在本面板上执行的终止进程、启动 / 停止 LaunchAgent 等操作</div>
          </div>
        </div>
        {action_log_section}
      </section>

      <section class="section" data-section="settings">
        <div class="topbar">
          <div>
            <h1>设置</h1>
            <div class="sub">配置路径与刷新说明</div>
          </div>
        </div>
        <div class="card">
          <div class="card-title">数据刷新说明</div>
          <ul class="muted">
            <li>本页面是<strong>快照</strong>，不是实时监控。</li>
            <li>「刷新运行态」只重新采集当前在跑的进程。</li>
            <li>「刷新全部」会重新跑 discovery、projects、runtime、macos-signals，并更新静态 HTML。</li>
            <li>你在外面新装了工具 / 改了 launchd，需要点「刷新全部」才能看到最新状态。</li>
            <li>「操作记录」记录你在本面板上执行的终止进程和 LaunchAgent 开关操作。</li>
          </ul>
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


def build_dashboard(run_discovery=True, refresh_mcp=True, run_projects=True, run_signals=False, run_signals_skip_btm=False, live=False, discovery_mode="daily"):
    agent_registry = lib.load_json(paths.REGISTRY)
    mcp_registry = lib.load_json(paths.MCP_REGISTRY)
    discovery_raw = data.refresh_discovery(mode=discovery_mode) if run_discovery else ""
    project_raw = data.refresh_projects() if run_projects else ""
    signals_refresh_error = data.refresh_signals(skip_btm=run_signals_skip_btm) if run_signals else ""
    discovered_rows, discovered_at, discovered_meta = data.collect_discovered()
    project_rows, project_at, project_meta = data.collect_projects()
    signals_raw = lib.load_json(paths.MACOS_SIGNALS) if paths.MACOS_SIGNALS.exists() else {}
    signals_rows = signals_raw.get("items", []) if isinstance(signals_raw, dict) else []
    signals_meta = dict(signals_raw.get("summary", {}) if isinstance(signals_raw, dict) else {})
    if signals_refresh_error:
        signals_meta["_refresh_error"] = signals_refresh_error
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
    all_processes = data.collect_all_processes()
    system_memory = data.collect_system_memory()
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
        all_processes=all_processes,
        system_memory=system_memory,
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
    dashboard_state = lib.load_json(paths.DASHBOARD_STATE)
    last_signals_refresh_at = dashboard_state.get("last_signals_refresh_at", "")
    # 首次生成时初始化时间戳，让前端轮询有基准可比
    if not last_signals_refresh_at:
        last_signals_refresh_at = lib.now_iso()
        dashboard_state["last_signals_refresh_at"] = last_signals_refresh_at
        paths.DASHBOARD_STATE.parent.mkdir(parents=True, exist_ok=True)
        lib.write_json(paths.DASHBOARD_STATE, dashboard_state)
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
        "last_signals_refresh_at": last_signals_refresh_at,
    }
    return html_text, summary


def write_dashboard(run_discovery=True, refresh_mcp=True, run_projects=True, run_signals=False, run_signals_skip_btm=False, live=False):
    html_text, summary = build_dashboard(run_discovery=run_discovery, refresh_mcp=refresh_mcp, run_projects=run_projects, run_signals=run_signals, run_signals_skip_btm=run_signals_skip_btm, live=live)
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
