"""Write tools for the Obsidian vault MCP server."""

import json
import logging

from .. import frontmatter_io
from ..hooks import fire_post_write
from ..vault import resolve_vault_path, read_file, write_file_atomic

logger = logging.getLogger(__name__)


def vault_write(path: str, content: str, create_dirs: bool = True, merge_frontmatter: bool = False) -> str:
    """Write a file to the vault, optionally merging frontmatter with existing content."""
    try:
        resolve_vault_path(path)

        if merge_frontmatter:
            try:
                existing_content, _ = read_file(path)
                existing_meta, _ = frontmatter_io.loads(existing_content)
                new_meta, new_body = frontmatter_io.loads(content)

                # Mutate existing in place: untouched keys keep their original
                # formatting (quote style, comments); new keys are appended.
                for key, value in new_meta.items():
                    existing_meta[key] = value

                content = frontmatter_io.dumps(existing_meta, new_body)
            except FileNotFoundError:
                pass
            except Exception as e:
                logger.warning(f"Frontmatter merge failed for {path}, writing as-is: {e}")

        is_new, size = write_file_atomic(path, content, create_dirs=create_dirs)

        operation = "created" if is_new else "updated"
        fire_post_write(operation, [path])

        return json.dumps({"path": path, "created": is_new, "size": size})
    except ValueError as e:
        return json.dumps({"error": str(e), "path": path})
    except Exception as e:
        logger.error(f"vault_write error for {path}: {e}")
        return json.dumps({"error": str(e), "path": path})


def vault_batch_frontmatter_update(updates: list[dict]) -> str:
    """Update frontmatter fields on multiple files without changing body content."""
    results = []
    updated_paths: list[str] = []

    for update in updates:
        file_path = update.get("path", "")
        fields = update.get("fields", {})

        try:
            content, _ = read_file(file_path)
            metadata, body = frontmatter_io.loads(content)

            if all(metadata.get(k) == v for k, v in fields.items()):
                results.append({"path": file_path, "updated": False, "unchanged": True})
                continue

            for key, value in fields.items():
                metadata[key] = value

            new_content = frontmatter_io.dumps(metadata, body)
            write_file_atomic(file_path, new_content, create_dirs=False)

            results.append({"path": file_path, "updated": True})
            updated_paths.append(file_path)
        except FileNotFoundError:
            results.append({"path": file_path, "updated": False, "error": "File not found"})
        except ValueError as e:
            results.append({"path": file_path, "updated": False, "error": str(e)})
        except Exception as e:
            results.append({"path": file_path, "updated": False, "error": str(e)})

    if updated_paths:
        fire_post_write("updated frontmatter in", updated_paths)

    return json.dumps({"results": results})


def vault_patch(path: str, old_text: str, new_text: str) -> str:
    """Replace a unique text occurrence in a file. Fails if old_text is not found or matches multiple times."""
    try:
        content, _ = read_file(path)
        count = content.count(old_text)
        if count == 0:
            return json.dumps({"error": "old_text not found in file", "path": path})
        if count > 1:
            return json.dumps({
                "error": f"old_text matches {count} times — provide more context to make it unique",
                "path": path,
            })
        new_content = content.replace(old_text, new_text, 1)
        _, size = write_file_atomic(path, new_content, create_dirs=False)
        fire_post_write("updated", [path])
        return json.dumps({"path": path, "patched": True, "size": size})
    except FileNotFoundError:
        return json.dumps({"error": f"File not found: {path}", "path": path})
    except ValueError as e:
        return json.dumps({"error": str(e), "path": path})
    except Exception as e:
        logger.error(f"vault_patch error for {path}: {e}")
        return json.dumps({"error": str(e), "path": path})


def vault_append(path: str, content: str, create_if_missing: bool = False) -> str:
    """Append content to the end of a file. Adds a newline before appending if the file doesn't end with one."""
    try:
        is_new = False
        try:
            existing, _ = read_file(path)
            if existing and not existing.endswith("\n"):
                content = "\n" + content
            new_content = existing + content
        except FileNotFoundError:
            if not create_if_missing:
                return json.dumps({"error": f"File not found: {path}", "path": path})
            new_content = content
            is_new = True

        _, size = write_file_atomic(path, new_content, create_dirs=create_if_missing)
        fire_post_write("created" if is_new else "updated", [path])
        return json.dumps({"path": path, "appended": True, "size": size})
    except ValueError as e:
        return json.dumps({"error": str(e), "path": path})
    except Exception as e:
        logger.error(f"vault_append error for {path}: {e}")
        return json.dumps({"error": str(e), "path": path})
