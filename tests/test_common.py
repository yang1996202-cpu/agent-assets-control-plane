"""Tests for lib/agent_assets_common.py."""

import os
import pathlib
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import agent_assets_common as lib


class TestListify(unittest.TestCase):
    def test_listify_none(self):
        self.assertEqual(lib.listify(None), [])

    def test_listify_empty(self):
        self.assertEqual(lib.listify([]), [])

    def test_listify_string(self):
        self.assertEqual(lib.listify("x"), ["x"])

    def test_listify_list(self):
        self.assertEqual(lib.listify(["a", None, "b"]), ["a", "b"])


class TestAppendUnique(unittest.TestCase):
    def test_append_unique_filters_none(self):
        target = {}
        lib.append_unique(target, "k", ["a", None, "a", "b"])
        self.assertEqual(target["k"], ["a", "b"])

    def test_append_unique_scalar(self):
        target = {"k": ["a"]}
        lib.append_unique(target, "k", "b")
        self.assertEqual(target["k"], ["a", "b"])


class TestPathHelpers(unittest.TestCase):
    def test_safe_resolve_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp)
            self.assertEqual(lib.safe_resolve(tmp), p.resolve())

    def test_is_under(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = pathlib.Path(tmp) / "parent"
            child = parent / "child"
            parent.mkdir()
            child.mkdir()
            self.assertTrue(lib.is_under(child, parent))
            self.assertFalse(lib.is_under(parent, child))

    def test_url_to_path(self):
        self.assertEqual(lib.url_to_path("file:///tmp/foo%20bar"), "/tmp/foo bar")
        self.assertEqual(lib.url_to_path("https://example.com"), "")


class TestIdentifierHelpers(unittest.TestCase):
    def test_normalize_identifier(self):
        self.assertEqual(lib.normalize_identifier("  1. Foo Bar "), "Foo Bar")
        self.assertEqual(lib.normalize_identifier(""), "")

    def test_item_key(self):
        self.assertEqual(lib.item_key("(null)", "name", ""), "name")
        self.assertEqual(lib.item_key(None, "(null)"), "unknown")


class TestHtmlChip(unittest.TestCase):
    def test_path_state_ref(self):
        self.assertEqual(lib.path_state("not-a-path"), "ref")

    def test_path_state_missing(self):
        self.assertEqual(lib.path_state("/nonexistent/path"), "missing")

    def test_chip_contains_state_badge(self):
        html = lib.chip("/nonexistent/path")
        self.assertIn("missing", html)


if __name__ == "__main__":
    unittest.main()
