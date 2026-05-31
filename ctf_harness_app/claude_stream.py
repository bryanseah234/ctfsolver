from __future__ import annotations

import json
from typing import Any


MAX_BLOCK_CHARS = 4000


def _shorten(value: Any, limit: int = MAX_BLOCK_CHARS) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return text[:limit].rstrip() + f"\n... [{omitted} chars omitted]"


def _clean_output(value: Any) -> str:
    return str(value).rstrip()


def _tool_input_summary(tool_name: str, tool_input: Any) -> str:
    if not isinstance(tool_input, dict):
        return ""
    if tool_name == "Bash" and tool_input.get("command"):
        description = tool_input.get("description")
        detail = f"$ {tool_input['command']}"
        return f"{description}\n{detail}" if description else detail
    if tool_input:
        return _shorten(json.dumps(tool_input, ensure_ascii=False, indent=2))
    return ""


def _tool_fields(tool_name: str, tool_input: Any) -> dict[str, str]:
    fields: dict[str, str] = {}
    if isinstance(tool_input, dict):
        if tool_name == "Bash":
            if tool_input.get("description"):
                fields["description"] = _shorten(tool_input["description"], 1000)
            if tool_input.get("command"):
                fields["command"] = _shorten(tool_input["command"], 3000)
        elif tool_input:
            fields["input"] = _shorten(json.dumps(tool_input, ensure_ascii=False, indent=2))
    elif tool_input:
        fields["input"] = _shorten(tool_input)
    return fields


def _result_fields(result: Any) -> dict[str, str]:
    fields: dict[str, str] = {}
    if isinstance(result, dict):
        for key in ("stdout", "stderr"):
            if result.get(key):
                fields[key] = _shorten(_clean_output(result[key]))
        if "interrupted" in result:
            fields["interrupted"] = str(result["interrupted"])
        if not fields:
            fields["result"] = _shorten(json.dumps(result, ensure_ascii=False, indent=2).rstrip())
        return fields
    text = str(result)
    if text.startswith("Error: "):
        fields["error"] = _shorten(_clean_output(text.removeprefix("Error: ")))
    else:
        fields["result"] = _shorten(_clean_output(text))
    return fields


def _append_unique(lines: list[str], value: str) -> None:
    value = value.strip()
    if value and (not lines or lines[-1] != value):
        lines.append(value)


def _append_event(
    events: list[dict[str, Any]],
    kind: str,
    title: str,
    body: Any = "",
    meta: str = "",
    fields: dict[str, str] | None = None,
) -> None:
    event = {
        "kind": kind,
        "title": title.strip(),
        "body": _shorten(body).strip(),
        "meta": meta.strip(),
        "fields": fields or {},
    }
    if event["title"] or event["body"]:
        if not events or events[-1] != event:
            events.append(event)


def parse_claude_stream(text: str, limit: int | None = None) -> list[dict[str, Any]]:
    """Turn Claude Code stream-json output into typed dashboard events."""
    events: list[dict[str, Any]] = []
    partial_text: list[str] = []
    partial_tool_inputs: dict[int, str] = {}
    partial_tool_names: dict[int, str] = {}

    def flush_text() -> None:
        if partial_text:
            _append_event(events, "assistant", "Claude", "".join(partial_text).strip())
            partial_text.clear()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not line.startswith("{"):
            if line.startswith("[ctf-harness]") or line.startswith("$ ") or line.startswith("==="):
                _append_event(events, "harness", "Harness", line)
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type")
        if event_type == "system":
            subtype = event.get("subtype")
            if subtype == "init":
                model = event.get("model", "unknown model")
                cwd = event.get("cwd", "unknown cwd")
                permission = event.get("permissionMode", "unknown permissions")
                _append_event(events, "session", "Session started", f"{model}\n{permission}\n{cwd}")
            elif subtype == "status" and event.get("status"):
                _append_event(events, "status", str(event["status"]).title())
            continue

        if event_type == "stream_event":
            stream = event.get("event") or {}
            stream_type = stream.get("type")
            if stream_type == "message_start":
                _append_event(events, "status", "Claude request started")
            elif stream_type == "content_block_start":
                block = stream.get("content_block") or {}
                index = stream.get("index")
                if block.get("type") == "thinking":
                    _append_event(events, "status", "Thinking")
                elif block.get("type") == "text":
                    _append_event(events, "status", "Responding")
                elif block.get("type") == "tool_use" and isinstance(index, int):
                    partial_tool_names[index] = str(block.get("name") or "tool")
                    partial_tool_inputs[index] = ""
                    _append_event(events, "status", "Preparing tool call", partial_tool_names[index])
            elif stream_type == "content_block_delta":
                delta = stream.get("delta") or {}
                if delta.get("type") == "text_delta":
                    partial_text.append(str(delta.get("text") or ""))
                elif delta.get("type") == "input_json_delta" and isinstance(stream.get("index"), int):
                    partial_tool_inputs[stream["index"]] = partial_tool_inputs.get(stream["index"], "") + str(delta.get("partial_json") or "")
            elif stream_type == "content_block_stop":
                index = stream.get("index")
                if isinstance(index, int) and index in partial_tool_names:
                    flush_text()
                    tool_name = partial_tool_names.pop(index, "tool")
                    raw_input = partial_tool_inputs.pop(index, "")
                    try:
                        tool_input = json.loads(raw_input) if raw_input else {}
                    except json.JSONDecodeError:
                        tool_input = {"partial_input": raw_input}
                    summary = _tool_input_summary(tool_name, tool_input)
                    _append_event(events, "tool", tool_name, summary, fields=_tool_fields(tool_name, tool_input))
            elif stream_type == "message_delta":
                delta = stream.get("delta") or {}
                stop_reason = delta.get("stop_reason")
                if stop_reason:
                    _append_event(events, "status", "Message finished", str(stop_reason).replace("_", " "))
            elif stream_type == "message_stop":
                flush_text()
            continue

        if event_type == "assistant":
            flush_text()
            message = event.get("message") or {}
            for block in message.get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and block.get("text"):
                    _append_event(events, "assistant", "Claude", block["text"])
                elif block.get("type") == "tool_use":
                    tool_name = str(block.get("name") or "tool")
                    tool_input = block.get("input")
                    summary = _tool_input_summary(tool_name, tool_input)
                    _append_event(events, "tool", tool_name, summary, fields=_tool_fields(tool_name, tool_input))
            continue

        if event_type == "user":
            result = event.get("tool_use_result")
            if result:
                _append_event(events, "result", "Tool result", result, fields=_result_fields(result))
                continue
            message = event.get("message") or {}
            for block in message.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    prefix = "Tool error" if block.get("is_error") else "Tool result"
                    content = block.get("content", "")
                    _append_event(
                        events,
                        "error" if block.get("is_error") else "result",
                        prefix,
                        content,
                        fields=_result_fields(f"Error: {content}" if block.get("is_error") else content),
                    )
            continue

        if event_type == "result":
            title = "Claude error" if event.get("is_error") or event.get("api_error_status") else "Claude completed"
            kind = "error" if event.get("is_error") or event.get("api_error_status") else "status"
            fields = _result_fields(event)
            if event.get("api_error_status"):
                fields["api_error_status"] = str(event["api_error_status"])
            if event.get("terminal_reason"):
                fields["terminal_reason"] = str(event["terminal_reason"])
            _append_event(events, kind, title, event.get("result", ""), fields=fields)

    flush_text()
    return events if limit is None else events[-limit:]


def format_claude_stream(text: str, limit: int | None = None) -> str:
    """Turn Claude Code stream-json output into a dashboard-friendly transcript."""
    events = parse_claude_stream(text, limit=limit)
    if not events:
        return "No parsed Claude stream events yet."
    lines: list[str] = []
    for event in events:
        title = event.get("title") or event.get("kind", "event")
        body = event.get("body") or ""
        lines.append(title + (f":\n{body}" if body else ""))
    return "\n\n".join(lines)
