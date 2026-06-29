"""
Audit log — persists structured entries to audit_log.jsonl (one JSON object per line).

The file is append-only for new submissions. Appeals rewrite the file in-place to
update the relevant entry's status and add appeal fields, then append an appeal event
entry for a full audit trail.
"""

import json
import os
from typing import Any

_LOG_PATH = os.path.join(os.path.dirname(__file__), "audit_log.jsonl")


def append_log_entry(entry: dict[str, Any]) -> None:
    with open(_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def get_log_entries(limit: int = 50) -> list[dict[str, Any]]:
    if not os.path.exists(_LOG_PATH):
        return []
    with open(_LOG_PATH, encoding="utf-8") as fh:
        lines = fh.readlines()
    entries = []
    for line in reversed(lines):
        line = line.strip()
        if line:
            entries.append(json.loads(line))
        if len(entries) >= limit:
            break
    return entries


def get_entry_by_content_id(content_id: str) -> dict[str, Any] | None:
    """Return the most recent log entry for a content_id, or None if not found."""
    if not os.path.exists(_LOG_PATH):
        return None
    with open(_LOG_PATH, encoding="utf-8") as fh:
        lines = fh.readlines()
    # Walk newest-first so we get the latest version of an entry
    for line in reversed(lines):
        line = line.strip()
        if line:
            entry = json.loads(line)
            if entry.get("content_id") == content_id:
                return entry
    return None


def update_entry_status(content_id: str, new_status: str, extra_fields: dict[str, Any]) -> bool:
    """
    Rewrite audit_log.jsonl, updating the FIRST (original) submission entry for
    content_id in-place, then return True.  Returns False if content_id not found.

    extra_fields are merged into the matched entry (used to add appeal_reasoning,
    appeal_timestamp, etc.).
    """
    if not os.path.exists(_LOG_PATH):
        return False

    with open(_LOG_PATH, encoding="utf-8") as fh:
        lines = fh.readlines()

    updated = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            new_lines.append(line)
            continue
        entry = json.loads(stripped)
        if entry.get("content_id") == content_id and not updated:
            entry["status"] = new_status
            entry.update(extra_fields)
            new_lines.append(json.dumps(entry) + "\n")
            updated = True
        else:
            new_lines.append(line)

    if updated:
        with open(_LOG_PATH, "w", encoding="utf-8") as fh:
            fh.writelines(new_lines)

    return updated
