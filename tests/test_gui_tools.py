import unittest
from unittest.mock import patch
from io import StringIO
from gui.tools_view import render_tool_call_request, ask_tool_confirmation, render_tool_result


class TestGuiTools(unittest.TestCase):

    def test_render_tool_call_request(self):
        # Asegurar que se ejecuta sin lanzar excepciones
        render_tool_call_request("calculator", {"expression": "2 + 2"})

    def test_ask_tool_confirmation_yes(self):
        with patch("builtins.input", return_value="s"):
            res = ask_tool_confirmation("calculator", {"expression": "2 + 2"})
            self.assertTrue(res)

    def test_ask_tool_confirmation_no(self):
        with patch("builtins.input", return_value="n"):
            res = ask_tool_confirmation("calculator", {"expression": "2 + 2"})
            self.assertFalse(res)

    def test_render_tool_result(self):
        # Asegurar que corre sin errores tanto con éxito como con error
        render_tool_result("calculator", {"result": 4}, is_error=False)
        render_tool_result("calculator", "Error syntax", is_error=True)


if __name__ == "__main__":
    unittest.main()
