from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List
import json
import urllib.request


@dataclass
class StreamEvent:
    """Evento normalizado proveniente de una respuesta de /api/chat de Ollama."""

    kind: str  # "thinking" | "content" | "tool_calls" | "done"
    text: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    eval_count: int = 0
    eval_duration: int = 0


def iter_ollama_events(response, stream: bool) -> Iterator[StreamEvent]:
    """Parsea un stream NDJSON o una respuesta JSON completa de Ollama en eventos tipados."""
    if stream:
        for raw_line in response:
            if not raw_line:
                continue
            line_str = raw_line.decode("utf-8").strip()
            if not line_str:
                continue
            try:
                res = json.loads(line_str)
            except json.JSONDecodeError:
                continue

            msg_obj = res.get("message") or {}

            thinking = msg_obj.get("thinking")
            if thinking:
                yield StreamEvent(kind="thinking", text=thinking)

            content = msg_obj.get("content")
            if content:
                yield StreamEvent(kind="content", text=content)

            chunk_tools = msg_obj.get("tool_calls")
            if chunk_tools:
                yield StreamEvent(kind="tool_calls", tool_calls=chunk_tools)

            if res.get("done"):
                yield StreamEvent(
                    kind="done",
                    eval_count=res.get("eval_count", 0) or 0,
                    eval_duration=res.get("eval_duration", 0) or 0,
                )
    else:
        response_body = response.read().decode("utf-8")
        res = json.loads(response_body)
        msg_obj = res.get("message") or {}

        thinking = msg_obj.get("thinking")
        if thinking:
            yield StreamEvent(kind="thinking", text=thinking)

        content = msg_obj.get("content")
        if content:
            yield StreamEvent(kind="content", text=content)

        chunk_tools = msg_obj.get("tool_calls")
        if chunk_tools:
            yield StreamEvent(kind="tool_calls", tool_calls=chunk_tools)

        yield StreamEvent(
            kind="done",
            eval_count=res.get("eval_count", 0) or 0,
            eval_duration=res.get("eval_duration", 0) or 0,
        )


def stream_ollama_chat(req: urllib.request.Request, stream: bool) -> Iterator[StreamEvent]:
    """Abre la conexión HTTP con Ollama y produce eventos tipados de la respuesta."""
    with urllib.request.urlopen(req) as response:
        yield from iter_ollama_events(response, stream=stream)
