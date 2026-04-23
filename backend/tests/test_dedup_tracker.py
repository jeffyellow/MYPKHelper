"""Tests for DedupTracker."""

import time
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dedup_tracker import DedupTracker


class TestDedupTracker:
    def test_first_entry_not_duplicate(self):
        t = DedupTracker(window_ms=3000)
        assert t.is_duplicate("A", 100) is False

    def test_duplicate_within_window(self):
        t = DedupTracker(window_ms=3000)
        t.record("A", 100)
        assert t.is_duplicate("A", 100) is True

    def test_different_value_not_duplicate(self):
        t = DedupTracker(window_ms=3000)
        t.record("A", 100)
        assert t.is_duplicate("A", 200) is False

    def test_different_unit_not_duplicate(self):
        t = DedupTracker(window_ms=3000)
        t.record("A", 100)
        assert t.is_duplicate("B", 100) is False

    def test_expired_entry_not_duplicate(self):
        t = DedupTracker(window_ms=100)
        t.record("A", 100)
        time.sleep(0.15)
        assert t.is_duplicate("A", 100) is False

    def test_clear(self):
        t = DedupTracker(window_ms=3000)
        t.record("A", 100)
        t.clear()
        assert t.is_duplicate("A", 100) is False
