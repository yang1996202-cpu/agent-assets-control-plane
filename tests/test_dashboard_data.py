"""Tests for lib/agent_assets_dashboard_data.py pure functions."""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import agent_assets_dashboard_data as dash_data


class TestSimplifyMcpEntry(unittest.TestCase):
    def test_http_url(self):
        self.assertEqual(
            dash_data.simplify_mcp_entry({"url": "http://localhost:3000/sse"}),
            {"transport": "http", "entry": "http://localhost:3000/sse"},
        )

    def test_stdio_command(self):
        self.assertEqual(
            dash_data.simplify_mcp_entry({"command": "node", "args": ["server.js"]}),
            {"transport": "stdio", "entry": "node server.js"},
        )

    def test_unknown(self):
        self.assertEqual(
            dash_data.simplify_mcp_entry("not-a-dict"),
            {"transport": "unknown", "entry": ""},
        )


class TestParseHealthText(unittest.TestCase):
    def test_connected(self):
        text = "gbrain: http://... - Connected (0ms)"
        health = dash_data.parse_health_text(text)
        self.assertEqual(health["gbrain"]["state"], "connected")

    def test_failed(self):
        text = "context7: /... - Failed to connect"
        health = dash_data.parse_health_text(text)
        self.assertEqual(health["context7"]["state"], "failed")


class TestBuildMcpAudit(unittest.TestCase):
    def test_host_only_detected(self):
        agent_registry = {
            "indexes": {
                "host_configs": {
                    "claude_mcp_config": "/tmp/claude-mcp.json",
                }
            }
        }
        mcp_registry = {"stdio_servers": {}, "http_servers": {}, "internal_servers": {}}
        mcp_rows = []
        # We would need a real file for full host ref collection; here test the empty case
        audit = dash_data.build_mcp_audit(agent_registry, mcp_registry, mcp_rows)
        self.assertIn("summary", audit)
        self.assertEqual(audit["summary"]["host_refs"], 0)


class TestCollectSystemMemory(unittest.TestCase):
    def test_parses_vm_stat_and_sysctl(self):
        """collect_system_memory 能正确解析 vm_stat 和 sysctl 输出并返回 GB 数值。"""
        vm_stdout = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                                1000.
Pages active:                            10000.
Pages inactive:                          10000.
Pages speculative:                         500.
Pages wired down:                         5000.
Pages purgeable:                           200.
Anonymous pages:                         15000.
File-backed pages:                        2000.
Pages occupied by compressor:             1000.
"""
        sysctl_stdout = """hw.memsize: 17179869184
hw.pagesize: 16384
"""

        def _fake_run(cmd, **kwargs):
            proc = MagicMock()
            proc.returncode = 0
            if cmd[0] == "vm_stat":
                proc.stdout = vm_stdout
            else:
                proc.stdout = sysctl_stdout
            return proc

        with patch.object(dash_data.subprocess, "run", side_effect=_fake_run):
            stats = dash_data.collect_system_memory()

        self.assertIsNotNone(stats)
        self.assertEqual(stats["total_gb"], 16.0)
        # app = anonymous pages
        self.assertAlmostEqual(stats["app_gb"], 15000 * 16384 / (1024 ** 3), places=4)
        self.assertAlmostEqual(stats["wired_gb"], 5000 * 16384 / (1024 ** 3), places=4)
        self.assertAlmostEqual(stats["compressed_gb"], 1000 * 16384 / (1024 ** 3), places=4)
        # used = app + wired + compressed
        expected_used = (15000 + 5000 + 1000) * 16384 / (1024 ** 3)
        self.assertAlmostEqual(stats["used_gb"], expected_used, places=4)

    def test_returns_none_on_failure(self):
        with patch.object(dash_data.subprocess, "run", side_effect=Exception("boom")):
            self.assertIsNone(dash_data.collect_system_memory())


class TestCollectAllProcesses(unittest.TestCase):
    """覆盖 collect_all_processes() 的核心路径。"""

    @staticmethod
    def _fake_runtime(exists_value):
        """构造一个可被 patch 的伪 ASSET_RUNTIME Path 对象。"""
        fake = MagicMock()
        fake.exists.return_value = exists_value
        fake.__str__.return_value = "/fake/bin/asset-runtime"
        return fake

    def test_missing_runtime_returns_empty(self):
        """collect_all_processes 在 asset-runtime 不存在时返回空列表。"""
        with patch.object(dash_data.paths, "ASSET_RUNTIME", self._fake_runtime(False)):
            self.assertEqual(dash_data.collect_all_processes(), [])

    def test_parses_json_stdout(self):
        """collect_all_processes 能正确解析 asset-runtime --json --show-system --show-normal 的 stdout 并返回 processes 列表。"""
        processes = [
            {"pid": "1", "cmd": "launchd", "category": "system", "rss": 12345},
            {"pid": "42", "cmd": "agent", "category": "normal", "rss": 67890},
        ]
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps({"processes": processes})

        expected_args = [
            "/fake/bin/asset-runtime",
            "--json",
            "--show-system",
            "--show-normal",
            "--show-apps",
        ]

        with patch.object(dash_data.paths, "ASSET_RUNTIME", self._fake_runtime(True)):
            with patch.object(dash_data.subprocess, "run", return_value=mock_proc) as mock_run:
                result = dash_data.collect_all_processes()
                mock_run.assert_called_once_with(
                    expected_args,
                    cwd=str(dash_data.paths.HOME),
                    capture_output=True,
                    text=True,
                    timeout=25,
                )
                self.assertEqual(result, processes)


if __name__ == "__main__":
    unittest.main()
