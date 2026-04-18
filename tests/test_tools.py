"""Integration tests for tool functions."""

import json

import pytest

from obsidian_vault_mcp.tools.read import vault_read, vault_batch_read
from obsidian_vault_mcp.tools.write import vault_write, vault_batch_frontmatter_update
from obsidian_vault_mcp.tools.search import vault_search
from obsidian_vault_mcp.tools.manage import vault_list, vault_delete


def test_vault_read_returns_frontmatter(vault_dir):
    """vault_read returns parsed frontmatter."""
    result = json.loads(vault_read("test-note.md"))
    assert "error" not in result
    assert result["frontmatter"]["status"] == "active"
    assert result["frontmatter"]["type"] == "note"
    assert "test note" in result["content"]


def test_vault_write_creates_file(vault_dir):
    """vault_write creates a new file."""
    result = json.loads(vault_write("tools-test.md", "---\ntitle: Test\n---\n\nContent."))
    assert result["created"] is True
    assert result["size"] > 0
    assert (vault_dir / "tools-test.md").exists()


def test_vault_write_merge_frontmatter(vault_dir):
    """vault_write with merge_frontmatter preserves existing fields."""
    result = json.loads(vault_write(
        "test-note.md",
        "---\npriority: high\n---\n\nUpdated body.",
        merge_frontmatter=True,
    ))
    assert "error" not in result

    read_result = json.loads(vault_read("test-note.md"))
    assert read_result["frontmatter"]["status"] == "active"  # preserved
    assert read_result["frontmatter"]["priority"] == "high"  # new


def test_vault_search_finds_text(vault_dir):
    """vault_search finds text in files."""
    result = json.loads(vault_search("test note"))
    assert result["total_matches"] >= 1
    assert result["results"][0]["path"] == "test-note.md"


def test_vault_search_serializes_frontmatter_dates(vault_dir):
    """vault_search must JSON-serialize datetime/date values parsed from YAML frontmatter."""
    (vault_dir / "dated-note.md").write_text(
        "---\ncreated: 2025-01-15\nreviewed: 2025-06-01 10:30:00\n"
        "milestones:\n  - date: 2025-03-01\n    label: kickoff\n"
        "---\n\ndated content body.\n"
    )

    raw = vault_search("dated content")
    result = json.loads(raw)
    assert "error" not in result
    assert result["total_matches"] >= 1

    match = next(r for r in result["results"] if r["path"] == "dated-note.md")
    fm = match["frontmatter_excerpt"]
    assert isinstance(fm["created"], str)
    assert fm["created"].startswith("2025-01-15")


def test_vault_read_serializes_frontmatter_dates(vault_dir):
    """vault_read must JSON-serialize datetime/date values parsed from YAML frontmatter."""
    (vault_dir / "dated-read.md").write_text(
        "---\ndue: 2025-12-31\n---\n\nbody.\n"
    )

    result = json.loads(vault_read("dated-read.md"))
    assert "error" not in result
    assert isinstance(result["frontmatter"]["due"], str)
    assert result["frontmatter"]["due"].startswith("2025-12-31")


def test_vault_batch_read_handles_missing(vault_dir):
    """vault_batch_read returns errors for missing files without failing."""
    result = json.loads(vault_batch_read(
        ["test-note.md", "nonexistent.md"],
        include_content=True,
    ))
    assert result["found"] == 1
    assert result["missing"] == 1
    assert "error" in result["files"][1]


def test_vault_list_returns_items(vault_dir):
    """vault_list returns directory contents."""
    result = json.loads(vault_list(""))
    assert result["total"] >= 2
    names = [item["name"] for item in result["items"]]
    assert "test-note.md" in names
    assert ".obsidian" not in names


def test_vault_delete_requires_confirm(vault_dir):
    """vault_delete without confirm=true returns error."""
    vault_write("delete-me.md", "temp content")
    result = json.loads(vault_delete("delete-me.md", confirm=False))
    assert "error" in result
    assert (vault_dir / "delete-me.md").exists()  # still there
