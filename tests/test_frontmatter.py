"""Tests for frontmatter_index.py -- indexing, searching, and merging."""

import pytest
from pathlib import Path

from obsidian_vault_mcp.frontmatter_index import FrontmatterIndex


@pytest.fixture
def index(vault_dir):
    """Create and start a frontmatter index against the test vault."""
    idx = FrontmatterIndex()
    idx.start()
    yield idx
    idx.stop()


def test_index_builds_on_startup(index, vault_dir):
    """Index has entries for all .md files (not .obsidian)."""
    assert index.file_count >= 2  # test-note.md, subfolder/nested-note.md
    # no-frontmatter.md may or may not be in index (no frontmatter to parse)


def test_search_exact_match(index, vault_dir):
    """Search for field=status, value=active, match_type=exact."""
    results = index.search_by_field("status", "active", "exact")
    assert len(results) >= 1
    paths = [r["path"] for r in results]
    assert "test-note.md" in paths


def test_search_contains(index, vault_dir):
    """Search for field=client, value=Test, match_type=contains."""
    results = index.search_by_field("client", "Test", "contains")
    assert len(results) >= 1
    paths = [r["path"] for r in results]
    found = any("nested-note.md" in p for p in paths)
    assert found


def test_search_exists(index, vault_dir):
    """Search for field=client, match_type=exists."""
    results = index.search_by_field("client", "", "exists")
    assert len(results) >= 1


def test_search_with_prefix(index, vault_dir):
    """Search limited to subfolder/."""
    results = index.search_by_field("status", "draft", "exact", path_prefix="subfolder/")
    assert len(results) >= 1
    for r in results:
        assert r["path"].startswith("subfolder/")


