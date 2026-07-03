"""Tests for bin/agent-assets-runtime classification and fingerprint logic."""

import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))


def _load_bin_module(name, filename):
    """把 bin/ 下的脚本按模块名加载（文件名可含连字符、无 .py 后缀）。"""
    path = os.path.join(ROOT, "bin", filename)
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader(name, path)
    module = loader.load_module()
    sys.modules[name] = module
    return module


runtime = _load_bin_module("asset_runtime", "agent-assets-runtime")


class TestClassify(unittest.TestCase):
    def test_system_daemon(self):
        self.assertEqual(runtime.classify("/usr/libexec/something"), "system")

    def test_mcp_known_service(self):
        self.assertEqual(runtime.classify("bun run gbrain serve --http"), "mcp")

    def test_dev_server(self):
        self.assertEqual(runtime.classify("node vite --host"), "dev-server")

    def test_mcp_wrapper(self):
        self.assertEqual(runtime.classify("npx context7-mcp"), "mcp")

    def test_agent_daemon(self):
        self.assertEqual(runtime.classify("python hermes-agent --daemon"), "agent-daemon")

    def test_known_service_wins_over_dev_server(self):
        # gbrain contains "serve" and listens on port but should be classified as mcp
        self.assertEqual(runtime.classify("bun gbrain serve --http"), "mcp")


class TestFingerprint(unittest.TestCase):
    def test_strips_paths(self):
        fp1 = runtime.fingerprint("/usr/local/bin/node /Users/x/app.js")
        self.assertNotIn("/Users/x", fp1)

    def test_collapses_hashes(self):
        fp = runtime.fingerprint("node abc12345 xyz")
        self.assertNotIn("abc12345", fp)

    def test_same_fingerprint_for_cache_variants(self):
        a = runtime.fingerprint("node /Users/x/.npm/_npx/abc/pkg")
        b = runtime.fingerprint("node /Users/x/.npm/_npx/def/pkg")
        self.assertEqual(a, b)


class TestBuildRows(unittest.TestCase):
    def test_dev_server_with_port_is_zombie(self):
        procs = [{"pid": "1", "ppid": "0", "cmd": "node vite", "category": "dev-server", "fp": "vite"}]
        listeners = {"1": {"*:3000"}}
        rows = runtime.build_rows(procs, listeners, set())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["severity"], "zombie")

    def test_leak_flagged(self):
        procs = [
            {"pid": "1", "ppid": "0", "cmd": "bun gbrain", "category": "mcp", "fp": "gbrain"},
            {"pid": "2", "ppid": "0", "cmd": "bun gbrain", "category": "mcp", "fp": "gbrain"},
            {"pid": "3", "ppid": "0", "cmd": "bun gbrain", "category": "mcp", "fp": "gbrain"},
        ]
        listeners = {}
        leak_fps = {"gbrain"}
        rows = runtime.build_rows(procs, listeners, leak_fps)
        self.assertTrue(all(r["severity"] == "leak" for r in rows))


if __name__ == "__main__":
    unittest.main()
