"""Tests for lib/agent_assets_dashboard_data.py pure functions."""

import os
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()
