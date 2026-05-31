from __future__ import annotations

import json
from typing import Any

from .claude_stream import _append_event, _result_fields, _shorten


def _command_fields(item: dict[str, Any]) -> dict[str, str]:
    fields: dict[str, str] = {}
    if item.get("command"):
        fields["command"] = _shorten(item["command"], 3000)
    output = str(item.get("aggregated_output") or "").rstrip()
    if output:
        fields["stdout"] = _shorten(output)
    if item.get("exit_code") is not None:
        fields["exit_code"] = str(item["exit_code"])
    if item.get("status"):
        fields["status"] = str(item["status"])
    return fields


def parse_codex_stream(text: str, limit: int | None = None) -> list[dict[str, Any]]:
    """Turn Codex `exec --json` JSONL output into typed dashboard events."""
    events: list[dict[str, Any]] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not line.startswith("{"):
            if line.startswith("[ctf-harness]") or line.startswith("$ ") or line.startswith("==="):
                _append_event(events, "harness", "Harness", line)
            elif line.startswith("Reading "):
                _append_event(events, "status", "Codex", line)
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type")
        if event_type == "thread.started":
            _append_event(events, "session", "Thread started", event.get("thread_id", ""))
            continue
        if event_type == "turn.started":
            _append_event(events, "status", "Turn started")
            continue
        if event_type == "turn.completed":
            _append_event(events, "status", "Turn completed")
            continue
        if event_type == "error":
            _append_event(events, "error", "Codex error", event.get("message") or event, fields=_result_fields(event))
            continue

        if event_type not in {"item.started", "item.completed"}:
            continue
        item = event.get("item") or {}
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        status = str(item.get("status") or ("started" if event_type == "item.started" else "completed"))

        if item_type == "agent_message":
            text_value = item.get("text") or ""
            _append_event(events, "assistant", "Codex", text_value)
            continue

        if item_type == "command_execution":
            fields = _command_fields(item)
            if event_type == "item.started":
                _append_event(events, "tool", "Command started", fields.get("command", ""), meta=status, fields=fields)
            else:
                title = "Command completed"
                if item.get("exit_code") not in (None, 0):
                    title = "Command failed"
                _append_event(events, "result", title, meta=status, fields=fields)
            continue

        if item_type:
            _append_event(events, "status", str(item_type).replace("_", " ").title(), _shorten(json.dumps(item, ensure_ascii=False, indent=2)))

    return events if limit is None else events[-limit:]
