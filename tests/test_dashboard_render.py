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
