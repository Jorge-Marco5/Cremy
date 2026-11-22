import unittest
from unittest.mock import patch, MagicMock
import json
import argparse
from core.chat_service import send_chat_request, clear_context, context, _build_messages_payload


class TestChatServiceTools(unittest.TestCase):

    def setUp(self):
        clear_context()

    def tearDown(self):
        clear_context()

    def test_build_messages_payload(self):
        test_context = [
            {"role": "user", "content": "hola"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "calculator", "arguments": {"expression": "2+2"}}}]
            },
            {"role": "tool", "content": '{"result": 4}'}
        ]
        with patch("core.chat_service.get_config", return_value="System prompt"):
            payload = _build_messages_payload(test_context, supports_vision=False)
            self.assertEqual(len(payload), 4) # system + 3 messages
            self.assertEqual(payload[0]["role"], "system")
            self.assertEqual(payload[2]["tool_calls"][0]["function"]["name"], "calculator")

    @patch("utils.helpers.get_tools_config")
    @patch("core.chat_service.render_response")
    @patch("core.chat_service.dataServices")
    @patch("core.chat_service.get_config")
    def test_send_chat_request_tool_loop(self, mock_get_config, mock_dataservices, mock_render_response, mock_get_tools_cfg):
        mock_get_tools_cfg.return_value = {
            "enabled": True,
            "tools": {
                "calculator": {"enabled": True, "require_confirmation": False}
            }
        }
        # Mock configs
        def mock_config(key):
            if key == "url":
                return "http://localhost:11434"
            if key == "model":
                return "qwen2.5:1.5b"
            if key == "models":
                return {
                    "qwen2.5:1.5b": {
                        "capabilities": ["completion", "tools"]
                    }
                }
            if key == "stream":
                return False
            if key == "think":
                return False
            if key == "system_prompt":
                return None
            if key == "options":
                return {}
            return None

        mock_get_config.side_effect = mock_config

        # 1st call to render_response returns tool_call for calculator
        # 2nd call returns final text response
        mock_render_response.side_effect = [
            ("", 0, [{"function": {"name": "calculator", "arguments": {"expression": "10 * 5"}}}]),
            ("El resultado de 10 * 5 es 50.", 0, [])
        ]

        args = argparse.Namespace(
            model="qwen2.5:1.5b",
            text="Calcula 10 * 5",
            uuid=None
        )

        exit_code = send_chat_request(args)
        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_render_response.call_count, 2)

        # Verificar contexto acumulado:
        # 1. user: Calcula 10 * 5
        # 2. assistant (con tool_calls)
        # 3. tool (resultado de la calculadora)
        # 4. assistant (respuesta final)
        self.assertEqual(len(context), 4)
        self.assertEqual(context[0]["role"], "user")
        self.assertEqual(context[1]["role"], "assistant")
        self.assertIn("tool_calls", context[1])
        self.assertEqual(context[2]["role"], "tool")
        self.assertIn('"result": 50', context[2]["content"])
        self.assertEqual(context[3]["role"], "assistant")
        self.assertIn("50", context[3]["content"])

    @patch("utils.helpers.get_tools_config")
    @patch("core.chat_service.render_response")
    @patch("core.chat_service.dataServices")
    @patch("core.chat_service.get_config")
    def test_send_chat_request_disabled_tool_blocked(self, mock_get_config, mock_dataservices, mock_render_response, mock_get_tools_cfg):
        mock_get_tools_cfg.return_value = {
            "enabled": True,
            "tools": {
                "calculator": {"enabled": False, "require_confirmation": False}
            }
        }
        # Herramienta 'calculator' deshabilitada en la configuración
        def mock_config(key):
            if key == "url":
                return "http://localhost:11434"
            if key == "model":
                return "qwen2.5:1.5b"
            if key == "models":
                return {"qwen2.5:1.5b": {"capabilities": ["completion", "tools"]}}
            if key == "stream":
                return False
            if key == "think":
                return False
            if key == "system_prompt":
                return None
            if key == "options":
                return {}
            return None

        mock_get_config.side_effect = mock_config

        # 1st call devuelve tool call de 'calculator' (a pesar de estar deshabilitada)
        # 2nd call devuelve respuesta final
        mock_render_response.side_effect = [
            ("", 0, [{"function": {"name": "calculator", "arguments": {"expression": "2+2"}}}]),
            ("No puedo calcularlo porque la herramienta está deshabilitada.", 0, [])
        ]

        args = argparse.Namespace(model="qwen2.5:1.5b", text="calcula", uuid=None)
        exit_code = send_chat_request(args)
        self.assertEqual(exit_code, 0)

        # En el contexto, la respuesta del tool debe indicar error de que está deshabilitada
        tool_message = context[2]
        self.assertEqual(tool_message["role"], "tool")
        tool_content = json.loads(tool_message["content"])
        self.assertFalse(tool_content["success"])
        self.assertIn("deshabilitada en la configuración", tool_content["error"])


if __name__ == "__main__":
    unittest.main()

