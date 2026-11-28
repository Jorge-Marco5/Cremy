import io
import json
import unittest
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

from rich.console import Console

from core.ollama_client import StreamEvent, iter_ollama_events
from gui.render import (
    _TailRenderable,
    render_conversation,
    render_event_stream,
    render_response,
    render_static_message,
)


class _FakeHTTPResponse:
    """Simula un objeto HTTPResponse de urllib para pruebas sin red."""

    def __init__(self, lines):
        self._lines = [
            line.encode("utf-8") if isinstance(line, str) else line
            for line in lines
        ]

    def __iter__(self):
        return iter(self._lines)

    def read(self):
        return b"".join(self._lines)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


def _make_test_console():
    buf = io.StringIO()
    return Console(file=buf, force_terminal=False, width=100, color_system=None), buf


class TestOllamaClient(unittest.TestCase):

    def test_iter_ollama_events_stream_multiline_thinking_and_tools(self):
        ndjson_lines = [
            json.dumps({"message": {"thinking": "Analizando paso 1\n"}, "done": False}) + "\n",
            "linea-invalida-no-json\n",
            json.dumps({"message": {"content": "linea1\nlinea2\nlinea3"}, "done": False}) + "\n",
            json.dumps({
                "message": {
                    "tool_calls": [{"function": {"name": "calculator", "arguments": {"expression": "2+2"}}}]
                },
                "done": False,
            }) + "\n",
            json.dumps({"message": {"content": ""}, "done": True, "eval_count": 42, "eval_duration": 1_500_000_000}) + "\n",
        ]
        events = list(iter_ollama_events(_FakeHTTPResponse(ndjson_lines), stream=True))

        self.assertEqual([e.kind for e in events], ["thinking", "content", "tool_calls", "done"])
        self.assertEqual(events[0].text, "Analizando paso 1\n")
        self.assertEqual(events[1].text, "linea1\nlinea2\nlinea3")
        self.assertEqual(events[2].tool_calls[0]["function"]["name"], "calculator")
        self.assertEqual(events[3].eval_count, 42)
        self.assertEqual(events[3].eval_duration, 1_500_000_000)

    def test_iter_ollama_events_non_stream(self):
        payload = json.dumps({
            "message": {
                "thinking": "Razonamiento breve",
                "content": "Respuesta final",
                "tool_calls": [],
            },
            "eval_count": 15,
            "eval_duration": 500_000_000,
        })
        events = list(iter_ollama_events(_FakeHTTPResponse([payload]), stream=False))

        self.assertEqual([e.kind for e in events], ["thinking", "content", "done"])
        self.assertEqual(events[0].text, "Razonamiento breve")
        self.assertEqual(events[1].text, "Respuesta final")
        self.assertEqual(events[2].eval_count, 15)


class TestRenderModule(unittest.TestCase):

    def test_render_event_stream_preserves_multiline_chunks(self):
        test_console, buf = _make_test_console()
        spinner = MagicMock()
        events = [
            StreamEvent(kind="content", text="primera\nsegunda\ntercera"),
            StreamEvent(kind="done", eval_count=10, eval_duration=100),
        ]

        content, tool_calls, tokens, duration = render_event_stream(
            events, stream=True, spinner=spinner, target_console=test_console
        )

        output = buf.getvalue()
        self.assertEqual(content, "primera\nsegunda\ntercera")
        self.assertEqual(tool_calls, [])
        self.assertEqual(tokens, 10)
        self.assertEqual(duration, 100)
        self.assertIn("primera", output)
        self.assertIn("segunda", output)
        self.assertIn("tercera", output)
        spinner.stop.assert_called_once()

    def test_render_event_stream_markdown_table_and_multiline_code(self):
        test_console, buf = _make_test_console()
        md_chunk_1 = "| ColA | ColB |\n| --- | --- |\n| val1 | val2 |\n\n"
        md_chunk_2 = '```python\n"""\ncomentario multilinea\n"""\ndef hola():\n    return "ok"\n```\n'
        events = [
            StreamEvent(kind="content", text=md_chunk_1),
            StreamEvent(kind="content", text=md_chunk_2),
            StreamEvent(kind="done", eval_count=20, eval_duration=200),
        ]

        content, _, _, _ = render_event_stream(
            events, stream=True, target_console=test_console
        )

        output = buf.getvalue()
        self.assertEqual(content, md_chunk_1 + md_chunk_2)
        self.assertIn("ColA", output)
        self.assertIn("val2", output)
        self.assertIn("comentario multilinea", output)
        self.assertIn("def hola():", output)

    def test_render_event_stream_thinking_rendered_but_excluded_from_content(self):
        for stream_mode in (True, False):
            with self.subTest(stream=stream_mode):
                test_console, buf = _make_test_console()
                events = [
                    StreamEvent(kind="thinking", text="Paso interno de razonamiento"),
                    StreamEvent(kind="content", text="Respuesta visible"),
                    StreamEvent(kind="done", eval_count=30, eval_duration=300),
                ]

                content, _, _, _ = render_event_stream(
                    events, stream=stream_mode, target_console=test_console
                )

                output = buf.getvalue()
                self.assertEqual(content, "Respuesta visible")
                self.assertIn("Razonamiento", output)
                self.assertIn("Paso interno de razonamiento", output)
                self.assertIn("Respuesta visible", output)

    @patch("gui.render.save_usage")
    @patch("gui.render.Halo")
    @patch("gui.render.stream_ollama_chat")
    def test_render_response_network_error_vs_render_error(
        self, mock_stream, mock_halo, mock_save_usage
    ):
        req = urllib.request.Request("http://localhost:11434/api/chat")
        test_console, _ = _make_test_console()

        # 1. Error de red -> debe mencionar ollama serve
        mock_stream.side_effect = urllib.error.URLError("Connection refused")
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            content, code, tools = render_response(
                "llama3", req, stream=True, target_console=test_console
            )
        self.assertIsNone(content)
        self.assertEqual(code, 1)
        self.assertEqual(tools, [])
        self.assertIn("Error de conexión", stdout_buf.getvalue())
        self.assertIn("ollama serve", stdout_buf.getvalue())

        # 2. Error interno de renderizado -> NO debe culpar a ollama serve
        mock_stream.side_effect = ValueError("fallo interno")
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            content, code, tools = render_response(
                "llama3", req, stream=True, target_console=test_console
            )
        self.assertIsNone(content)
        self.assertEqual(code, 1)
        self.assertEqual(tools, [])
        self.assertIn("Error al procesar o renderizar la respuesta", stdout_buf.getvalue())
        self.assertNotIn("ollama serve", stdout_buf.getvalue())
        mock_save_usage.assert_not_called()

    def test_render_static_message_with_inline_backticks_and_code(self):
        test_console, buf = _make_test_console()
        md = "Usa `` ``` `` para bloques.\n\n```python\nx = 1\n```"
        render_static_message(md, test_console)
        output = buf.getvalue()
        self.assertIn("para bloques.", output)
        self.assertIn("x = 1", output)

    def test_render_conversation_roles(self):
        test_console, buf = _make_test_console()
        mock_ds = MagicMock()
        mock_ds.show_messages.return_value = [
            (1, "user", "Hola **mundo**", "2026-01-01 00:00:00", json.dumps(["foto.png"]), None, None),
            (
                2,
                "assistant",
                "Calculando...",
                "2026-01-01 00:00:01",
                None,
                json.dumps([{"function": {"name": "calculator", "arguments": {"expression": "2+2"}}}]),
                None,
            ),
            (3, "tool", json.dumps({"result": 4}), "2026-01-01 00:00:02", None, None, "calculator"),
        ]

        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            render_conversation("fake-uuid", limit=20, data_service=mock_ds, target_console=test_console)

        mock_ds.show_messages.assert_called_once_with("fake-uuid", 20)
        std_out = stdout_buf.getvalue()
        rich_out = buf.getvalue()
        self.assertIn("Imagen adjunta: foto.png", std_out)
        self.assertIn("Llamada a calculator", std_out)
        self.assertIn("Hola mundo", rich_out)
        self.assertIn("Calculando...", rich_out)
        self.assertIn('"result": 4', rich_out)

    def test_tail_renderable_clamps_to_max_lines(self):
        from rich.text import Text

        test_console, _ = _make_test_console()
        long_text = "\n".join(f"linea-{i}" for i in range(1, 51))
        tail = _TailRenderable(Text(long_text), max_lines=5)
        rendered_lines = test_console.render_lines(tail, pad=False)

        self.assertEqual(len(rendered_lines), 5)
        joined = "\n".join("".join(seg.text for seg in line) for line in rendered_lines)
        self.assertNotIn("linea-1\n", joined)
        self.assertIn("linea-46", joined)
        self.assertIn("linea-50", joined)

    def test_render_event_stream_long_thinking_and_content_committed_once_without_overflow(self):
        buf = io.StringIO()
        small_console = Console(file=buf, force_terminal=False, width=80, height=12, color_system=None)
        events = [
            StreamEvent(kind="thinking", text="\n".join(f"paso-{i}" for i in range(1, 31))),
            StreamEvent(kind="content", text="\n".join(f"- item-{i}" for i in range(1, 31))),
            StreamEvent(kind="done", eval_count=100, eval_duration=1000),
        ]

        content, _, tokens, _ = render_event_stream(
            events, stream=True, target_console=small_console
        )

        output = buf.getvalue()
        self.assertEqual(tokens, 100)
        self.assertIn("item-1", content)
        self.assertIn("item-30", content)
        # Al finalizar, el razonamiento completo y la respuesta completa se imprimen íntegros
        self.assertIn("Razonamiento", output)
        self.assertIn("paso-1", output)
        self.assertIn("paso-30", output)
        self.assertIn("item-1", output)
        self.assertIn("item-30", output)


if __name__ == "__main__":
    unittest.main()
