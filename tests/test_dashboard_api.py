"""Tests for lib/agent_assets_dashboard_api.py helper functions and handlers."""

import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import agent_assets_dashboard_api as api
import agent_assets_dashboard_paths as paths


class TestDashboardStateHelpers(unittest.TestCase):
    """覆盖 dashboard-state.json 与 macos-signals.json 错误标记的读写辅助函数。"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.state_path = pathlib.Path(self.tmpdir.name) / "dashboard-state.json"
        self.signals_path = pathlib.Path(self.tmpdir.name) / "macos-signals.json"
        patcher_state = patch.object(paths, "DASHBOARD_STATE", self.state_path)
        patcher_signals = patch.object(paths, "MACOS_SIGNALS", self.signals_path)
        self.addCleanup(patcher_state.stop)
        self.addCleanup(patcher_signals.stop)
        patcher_state.start()
        patcher_signals.start()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_touch_last_signals_refresh_at(self):
        """_touch_last_signals_refresh_at 应写入 ISO 格式时间戳。"""
        api._touch_last_signals_refresh_at()
        state = api.lib.load_json(self.state_path)
        self.assertIn("last_signals_refresh_at", state)
        self.assertTrue(state["last_signals_refresh_at"].endswith("Z"))

    def test_record_signals_refresh_error(self):
        """_record_signals_refresh_error 应把错误写入 macos-signals.json summary。"""
        api._record_signals_refresh_error("something went wrong")
        raw = api.lib.load_json(self.signals_path)
        self.assertEqual(raw["summary"]["_refresh_error"], "something went wrong")

    def test_clear_signals_refresh_error(self):
        """_clear_signals_refresh_error 应移除已有的 _refresh_error 标记。"""
        api._record_signals_refresh_error("old error")
        api._clear_signals_refresh_error()
        raw = api.lib.load_json(self.signals_path)
        self.assertNotIn("_refresh_error", raw.get("summary", {}))

    def test_clear_signals_refresh_error_when_missing(self):
        """_clear_signals_refresh_error 在文件不存在时不应抛异常。"""
        try:
            api._clear_signals_refresh_error()
        except Exception as exc:
            self.fail(f"_clear_signals_refresh_error raised {exc}")


class TestHandleLaunchctlActionZh(unittest.TestCase):
    """覆盖 handle_launchctl 用真实状态修正 action_zh 的逻辑。"""

    def setUp(self):
        self.home_agents = str(pathlib.Path.home() / "Library" / "LaunchAgents")
        self.plist = os.path.join(self.home_agents, "com.example.test.plist")

    def _make_plist_data(self, label="com.example.test", keep_alive=False):
        return {"Label": label, "KeepAlive": keep_alive}

    def _cmd_proc(self, rc=0, stderr=""):
        proc = MagicMock()
        proc.returncode = rc
        proc.stderr = stderr
        proc.stdout = ""
        return proc

    def _print_proc(self, running=False, disabled=False):
        proc = MagicMock()
        proc.returncode = 0
        lines = []
        lines.append("state = running" if running else "state = not running")
        lines.append("pid = 123" if running else "pid = 0")
        lines.append(f"disabled = {'true' if disabled else 'false'}")
        proc.stdout = "\n".join(lines)
        proc.stderr = ""
        return proc

    def _print_disabled_proc(self, contains=False):
        proc = MagicMock()
        proc.returncode = 0
        if contains:
            proc.stdout = "com.example.test\t=> disabled\n"
        else:
            proc.stdout = "some.other.service\t=> disabled\n"
        proc.stderr = ""
        return proc

    def _run_handle(self, action, running, disabled, keep_alive=False):
        """在统一 mock 环境下调用 handle_launchctl。"""
        plist_data = self._make_plist_data("com.example.test", keep_alive=keep_alive)
        procs = [
            self._cmd_proc(0),
            self._print_proc(running=running, disabled=disabled),
            self._print_disabled_proc(contains=disabled),
        ]
        with patch("agent_assets_dashboard_api.plistlib.load", return_value=plist_data):
            with patch("builtins.open", MagicMock()):
                with patch("agent_assets_dashboard_api.os.path.isfile", return_value=True):
                    with patch("agent_assets_dashboard_api.subprocess.run", side_effect=procs) as mock_run:
                        result, status = api.handle_launchctl({"plist": self.plist, "action": action})
                        return result, status, mock_run

    def test_bootout_success_stopped(self):
        result, status, _ = self._run_handle("bootout", running=False, disabled=False)
        self.assertEqual(status, 200)
        self.assertEqual(result["action_zh"], "已停止")
        self.assertFalse(result["running"])

    def test_bootout_keep_alive_restarted(self):
        result, status, _ = self._run_handle("bootout", running=True, disabled=False, keep_alive=True)
        self.assertEqual(status, 200)
        self.assertIn("KeepAlive", result["action_zh"])
        self.assertTrue(result["running"])

    def test_bootstrap_not_running(self):
        result, status, _ = self._run_handle("bootstrap", running=False, disabled=False)
        self.assertEqual(status, 200)
        self.assertIn("尚未运行", result["action_zh"])
        self.assertFalse(result["running"])

    def test_disable_confirmed(self):
        result, status, _ = self._run_handle("disable", running=False, disabled=True)
        self.assertEqual(status, 200)
        self.assertEqual(result["action_zh"], "已禁用开机自启")
        self.assertTrue(result["auto_disabled"])

    def test_disable_uncertain(self):
        result, status, _ = self._run_handle("disable", running=False, disabled=False)
        self.assertEqual(status, 200)
        self.assertIn("待刷新确认", result["action_zh"])
        self.assertFalse(result["auto_disabled"])


if __name__ == "__main__":
    unittest.main()
