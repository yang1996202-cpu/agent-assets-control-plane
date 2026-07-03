"""Tests for bin/agent-assets-macos-signals identifier and tag inference logic."""

import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import agent_assets_common as lib


def _load_bin_module(name, filename):
    path = os.path.join(ROOT, "bin", filename)
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader(name, path)
    module = loader.load_module()
    sys.modules[name] = module
    return module


macos = _load_bin_module("asset_macos_signals", "agent-assets-macos-signals")


class TestIdentifiers(unittest.TestCase):
    def test_normalize_identifier(self):
        self.assertEqual(lib.normalize_identifier("  2. Foo "), "Foo")
        self.assertEqual(lib.normalize_identifier(""), "")

    def test_item_key_priority(self):
        self.assertEqual(lib.item_key("(null)", "MyApp", "ignored"), "MyApp")
        self.assertEqual(lib.item_key("", "(null)", "Unknown Developer"), "unknown")


class TestInferTags(unittest.TestCase):
    def test_running_and_listening(self):
        item = {
            "label": "foo",
            "running": True,
            "listeners": [{"port": "8080"}],
            "tags": set(),
        }
        tags = set(macos.infer_tags(item))
        self.assertIn("running", tags)
        self.assertIn("listening", tags)

    def test_residual_candidate(self):
        item = {
            "label": "foo",
            "btm_enabled": True,
            "running": False,
            "tags": set(),
        }
        tags = set(macos.infer_tags(item))
        self.assertIn("residual-candidate", tags)

    def test_remote_control(self):
        item = {"label": "todesk helper", "tags": set()}
        tags = set(macos.infer_tags(item))
        self.assertIn("remote-control", tags)


class TestActionHint(unittest.TestCase):
    def test_running_listening(self):
        item = {"tags": ["running", "listening"]}
        self.assertIn("verify owner", macos.action_hint(item))

    def test_residual(self):
        item = {"tags": ["residual-candidate"]}
        self.assertIn("Launch/login trace", macos.action_hint(item))


if __name__ == "__main__":
    unittest.main()
