"""Tests for lib/agent_assets_dashboard_render.py pure helper functions."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import agent_assets_dashboard_render as render


class TestBuildProcessLookup(unittest.TestCase):
    def test_string_and_int_pids(self):
        processes = [
            {"pid": "1", "cmd": "launchd", "cpu": 1.2, "rss": 12345},
            {"pid": 42, "cmd": "agent", "cpu": 5.5, "rss": 67890},
        ]
        lookup = render._build_process_lookup(processes)
        self.assertEqual(lookup["1"]["cmd"], "launchd")
        self.assertEqual(lookup["42"]["cmd"], "agent")

    def test_none_list_returns_empty(self):
        self.assertEqual(render._build_process_lookup(None), {})


class TestSignalResourceText(unittest.TestCase):
    def test_running_with_matched_process(self):
        lookup = render._build_process_lookup([
            {"pid": 516, "cpu": 12.3, "rss": 234 * 1024},
        ])
        row = {"running": True, "processes": [{"pid": 516}]}
        text = render._signal_resource_text(row, lookup)
        self.assertIn("CPU 12.3%", text)
        self.assertIn("内存 234.0 MB", text)

    def test_running_no_processes(self):
        lookup = render._build_process_lookup([{"pid": 1, "cpu": 0, "rss": 0}])
        row = {"running": True, "processes": []}
        self.assertEqual(render._signal_resource_text(row, lookup), "—")

    def test_not_running(self):
        lookup = render._build_process_lookup([{"pid": 1, "cpu": 5, "rss": 1024}])
        row = {"running": False, "processes": [{"pid": 1}]}
        self.assertEqual(render._signal_resource_text(row, lookup), "—")

    def test_multiple_processes_aggregate(self):
        lookup = render._build_process_lookup([
            {"pid": 10, "cpu": 3.0, "rss": 100 * 1024},
            {"pid": 11, "cpu": 2.0, "rss": 200 * 1024},
        ])
        row = {"running": True, "processes": [{"pid": 10}, {"pid": 11}]}
        text = render._signal_resource_text(row, lookup)
        self.assertIn("CPU 5.0%", text)
        self.assertIn("内存 300.0 MB", text)


class TestProcessDisplayName(unittest.TestCase):
    def test_app_bundle(self):
        self.assertEqual(
            render._process_display_name("/Applications/WeChat.app/Contents/MacOS/WeChat"),
            "WeChat.app",
        )

    def test_interpreter_script(self):
        self.assertEqual(
            render._process_display_name("/usr/local/bin/python3 /Users/x/app.py"),
            "python3 app.py",
        )

    def test_system_path(self):
        self.assertEqual(render._process_display_name("/usr/sbin/kernel_task"), "kernel_task")

    def test_empty(self):
        self.assertEqual(render._process_display_name(""), "未知进程")


class TestUsageBarHtml(unittest.TestCase):
    def test_contains_bar_and_value(self):
        html = render._usage_bar_html(50, 100, "50.0%", "cpu")
        self.assertIn('class="usage-cell"', html)
        self.assertIn('width:50.0%', html)
        self.assertIn("50.0%", html)

    def test_zero_max_falls_back(self):
        html = render._usage_bar_html(0, 0, "0.0%", "mem")
        self.assertIn('width:0.0%', html)


class TestRenderLinkedAssets(unittest.TestCase):
    def test_empty_returns_placeholder(self):
        self.assertIn("未关联", render._render_linked_assets([]))

    def test_single_shows_chip(self):
        html = render._render_linked_assets(["agent-assets-system:stable_entrypoints"])
        self.assertIn("agent-assets-system:stable_entrypoints", html)
        self.assertNotIn("+", html)

    def test_multiple_shows_first_and_count_badge(self):
        html = render._render_linked_assets([
            "agent-assets-system:stable_entrypoints",
            "agent-assets-dashboard:source_paths",
            "agent-assets-runtime:processes",
        ])
        self.assertIn("agent-assets-system:stable_entrypoints", html)
        self.assertIn("+2", html)

    def test_multiple_includes_full_list_in_title(self):
        html = render._render_linked_assets([
            "agent-assets-system:stable_entrypoints",
            "agent-assets-dashboard:source_paths",
        ])
        self.assertIn('title="', html)
        self.assertIn("agent-assets-dashboard:source_paths", html)


class TestAggregateSystemProcesses(unittest.TestCase):
    def test_merge_same_app_helpers(self):
        """同一应用的多 helper 进程应聚合为一行，CPU/内存做加总。"""
        processes = [
            {"pid": "1", "cmd": "/Applications/WeChat.app/Contents/MacOS/WeChat", "category": "app", "rss": 100 * 1024, "cpu": 5.0},
            {"pid": "2", "cmd": "/Applications/WeChat.app/Contents/MacOS/WeChat Helper", "category": "app", "rss": 50 * 1024, "cpu": 2.0},
            {"pid": "3", "cmd": "/Applications/Chrome.app/Contents/MacOS/Chrome Helper", "category": "app", "rss": 80 * 1024, "cpu": 3.0},
        ]
        groups = render._aggregate_system_processes(processes)
        self.assertEqual(len(groups), 2)
        names = {g["name"] for g in groups}
        self.assertEqual(names, {"WeChat.app", "Chrome.app"})
        wechat = next(g for g in groups if g["name"] == "WeChat.app")
        self.assertEqual(wechat["rss"], 150 * 1024)
        self.assertEqual(wechat["cpu"], 7.0)
        self.assertEqual(len(wechat["pids"]), 2)

    def test_category_takes_most_common(self):
        processes = [
            {"pid": "1", "cmd": "node mcp-server", "category": "mcp", "rss": 10, "cpu": 0.1},
            {"pid": "2", "cmd": "node mcp-server", "category": "mcp", "rss": 10, "cpu": 0.1},
            {"pid": "3", "cmd": "node mcp-server", "category": "unknown", "rss": 10, "cpu": 0.1},
        ]
        groups = render._aggregate_system_processes(processes)
        self.assertEqual(groups[0]["category"], "mcp")


class TestRenderSystemProcessesRows(unittest.TestCase):
    def test_shows_top_processors_and_aggregated_table(self):
        """系统进程页应同时展示高占用卡片和聚合后的表格。"""
        processes = [
            {"pid": "1", "cmd": "/Applications/WeChat.app/Contents/MacOS/WeChat", "category": "app", "rss": 500 * 1024, "cpu": 10.0},
            {"pid": "2", "cmd": "/Applications/WeChat.app/Contents/MacOS/WeChat Helper", "category": "app", "rss": 200 * 1024, "cpu": 3.0},
            {"pid": "3", "cmd": "/Applications/WeChat.app/Contents/MacOS/WeChat Helper (GPU)", "category": "app", "rss": 100 * 1024, "cpu": 1.0},
            {"pid": "4", "cmd": "/Applications/WeChat.app/Contents/MacOS/WeChat Helper (Renderer)", "category": "app", "rss": 50 * 1024, "cpu": 0.5},
            {"pid": "5", "cmd": "node vite", "category": "dev-server", "rss": 50 * 1024, "cpu": 1.0},
        ]
        html = render.render_system_processes_rows(processes)
        self.assertIn("高 CPU 占用", html)
        self.assertIn("高内存占用", html)
        self.assertIn("WeChat.app", html)
        self.assertIn("4 个进程", html)


class TestRenderRuntimeFilterBar(unittest.TestCase):
    def test_hides_empty_categories(self):
        """没有 agent-daemon 时不显示 Agent Daemon 按钮，避免用户点击后为空。"""
        data = {
            "processes": [
                {"pid": "1", "category": "mcp", "cmd": "bun gbrain"},
                {"pid": "2", "category": "support", "cmd": "python dashboard"},
                {"pid": "3", "category": "dev-server", "cmd": "node vite"},
            ]
        }
        html = render.render_runtime_filter_bar(data)
        self.assertIn("全部 (3)", html)
        self.assertIn("MCP (1)", html)
        self.assertIn("Dev Server (1)", html)
        self.assertIn("支撑 / 系统 (1)", html)
        self.assertNotIn("Agent Daemon", html)

    def test_support_and_system_combined(self):
        data = {
            "processes": [
                {"pid": "1", "category": "support", "cmd": "x"},
                {"pid": "2", "category": "system", "cmd": "y"},
            ]
        }
        html = render.render_runtime_filter_bar(data)
        self.assertIn("支撑 / 系统 (2)", html)


class TestRenderMacosSignalsRowsGrouping(unittest.TestCase):
    def test_same_title_rows_stay_adjacent_despite_linked_status(self):
        """同一产品（如 gbrain）无论是否关联都应相邻，避免被其他产品插开导致重复分组表头。"""
        rows = [
            {
                "label": "com.gbrain.memory-browser",
                "launch_role": "user-agent",
                "launch_plist": "/Users/x/Library/LaunchAgents/com.gbrain.memory-browser.plist",
                "running": True,
                "linked_assets": ["pkg:stable_entrypoints"],
            },
            {
                "label": "com.gbrain.serve-http",
                "launch_role": "user-agent",
                "launch_plist": "/Users/x/Library/LaunchAgents/com.gbrain.serve-http.plist",
                "running": False,
                "linked_assets": [],
            },
            {
                "label": "com.google.keystone.agent",
                "launch_role": "user-agent",
                "launch_plist": "/Users/x/Library/LaunchAgents/com.google.keystone.agent.plist",
                "running": False,
                "linked_assets": [],
            },
        ]
        # 复用 build_dashboard 里的预处理逻辑
        for r in rows:
            r["_signal_kind"] = "launchd·用户级"
            r["_control"] = "user-launchd"
            r["_human"] = render.humanize_signal(r)
            r["_safe"] = True
        html = render.render_macos_signals_rows(rows)
        # gbrain 记忆服务 应该只出现一次分组表头
        self.assertEqual(html.count(">gbrain 记忆服务<"), 1)
        # Google 自动更新 表头出现一次
        self.assertEqual(html.count(">Google 自动更新<"), 1)


class TestPidExists(unittest.TestCase):
    @patch("os.kill")
    def test_exists_when_permission_denied(self, mock_kill):
        """root 系统守护进程没权限发信号时，应认为进程存在，而不是已退出。"""
        mock_kill.side_effect = PermissionError(1, "Operation not permitted")
        self.assertTrue(render._pid_exists(123))

    @patch("os.kill")
    def test_not_exists_when_no_such_process(self, mock_kill):
        mock_kill.side_effect = ProcessLookupError(3, "No such process")
        self.assertFalse(render._pid_exists(123))

    @patch("os.kill")
    def test_exists_when_no_error(self, mock_kill):
        mock_kill.return_value = None
        self.assertTrue(render._pid_exists(123))


class TestStateBadge(unittest.TestCase):
    def test_custom_label_wins(self):
        """传入自定义 label 时不应被 state_labels 覆盖。"""
        html = render.state_badge("not-running", "已停止（进程已退出）")
        self.assertIn("已停止（进程已退出）", html)

    def test_fallback_to_state_lookup(self):
        html = render.state_badge("not-running")
        self.assertIn("未运行", html)


class TestLaunchctlDisabledSet(unittest.TestCase):
    """覆盖 _launchctl_disabled_set 对 print-disabled 输出的解析。"""

    def _mock_run(self, stdout):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = stdout
        proc.stderr = ""
        return proc

    def test_parses_dotted_label(self):
        stdout = 'disabled services = {\n\t"com.example.foo" => disabled\n}'
        with patch("subprocess.run", return_value=self._mock_run(stdout)):
            result = render._launchctl_disabled_set()
        self.assertIn("com.example.foo", result)

    def test_parses_chinese_label_without_dot(self):
        """中文 Label（如 闪电说）不含点，也要能被识别为已禁用。"""
        stdout = 'disabled services = {\n\t"闪电说" => disabled\n}'
        with patch("subprocess.run", return_value=self._mock_run(stdout)):
            result = render._launchctl_disabled_set()
        self.assertIn("闪电说", result)

    def test_ignores_braces_and_headers(self):
        stdout = 'disabled services = {\n}'
        with patch("subprocess.run", return_value=self._mock_run(stdout)):
            result = render._launchctl_disabled_set()
        self.assertEqual(result, set())


if __name__ == "__main__":
    unittest.main()
