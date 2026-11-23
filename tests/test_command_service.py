import unittest
from unittest.mock import patch, MagicMock
import argparse
from core.command_service import CommandService, command_service
from core.core_service import instant_req, handle_interactive_chat_turn
from tools.definitions import CalculatorTool, DateTimeTool, ReadFileTool, BashTool


class TestCommandService(unittest.TestCase):

    def setUp(self):
        self.cmd_svc = CommandService()

    def test_is_command(self):
        self.assertTrue(self.cmd_svc.is_command("/calc 10 + 5"))
        self.assertTrue(self.cmd_svc.is_command("/help"))
        self.assertTrue(self.cmd_svc.is_command("/exit"))
        self.assertTrue(self.cmd_svc.is_command("exit"))
        self.assertTrue(self.cmd_svc.is_command("quit"))
        self.assertFalse(self.cmd_svc.is_command("hola mundo"))
        self.assertFalse(self.cmd_svc.is_command(""))
        self.assertFalse(self.cmd_svc.is_command(None))

    def test_parse_command_input(self):
        # 1. Simple command without args
        cmd, args, prompt = self.cmd_svc.parse_command_input("/help")
        self.assertEqual(cmd, "help")
        self.assertEqual(args, "")
        self.assertIsNone(prompt)

        # 2. Command with args
        cmd, args, prompt = self.cmd_svc.parse_command_input("/calc 25 * 4")
        self.assertEqual(cmd, "calc")
        self.assertEqual(args, "25 * 4")
        self.assertIsNone(prompt)

        # 3. Command with args and extra prompt via delimiter '--'
        cmd, args, prompt = self.cmd_svc.parse_command_input("/read_file main.py -- Resume las funciones principales")
        self.assertEqual(cmd, "read_file")
        self.assertEqual(args, "main.py")
        self.assertEqual(prompt, "Resume las funciones principales")

        # 4. Command without leading slash
        cmd, args, prompt = self.cmd_svc.parse_command_input("exit")
        self.assertEqual(cmd, "exit")
        self.assertEqual(args, "")
        self.assertIsNone(prompt)

    def test_find_tool_by_command(self):
        # Buscar por nombre exacto
        calc_tool = self.cmd_svc.find_tool_by_command("calculator")
        self.assertIsNotNone(calc_tool)
        self.assertEqual(calc_tool.name, "calculator")

        # Buscar por alias
        calc_alias = self.cmd_svc.find_tool_by_command("calc")
        self.assertIsNotNone(calc_alias)
        self.assertEqual(calc_alias.name, "calculator")

        bash_alias = self.cmd_svc.find_tool_by_command("bash")
        self.assertIsNotNone(bash_alias)
        self.assertEqual(bash_alias.name, "execute_bash")

        read_alias = self.cmd_svc.find_tool_by_command("read")
        self.assertIsNotNone(read_alias)
        self.assertEqual(read_alias.name, "read_file")

        date_alias = self.cmd_svc.find_tool_by_command("datetime")
        self.assertIsNotNone(date_alias)
        self.assertEqual(date_alias.name, "get_current_datetime")

        # Inexistente
        unknown = self.cmd_svc.find_tool_by_command("no_existe_tool")
        self.assertIsNone(unknown)

    def test_parse_tool_arguments_primary_arg(self):
        tool = CalculatorTool()
        args = self.cmd_svc.parse_tool_arguments(tool, "10 * (5 + 2)")
        self.assertEqual(args, {"expression": "10 * (5 + 2)"})

    def test_parse_tool_arguments_key_value(self):
        tool = ReadFileTool()
        args = self.cmd_svc.parse_tool_arguments(tool, "file_path=test.txt max_lines=25")
        self.assertEqual(args, {"file_path": "test.txt", "max_lines": 25})

    def test_parse_tool_arguments_read_file_positional(self):
        tool = ReadFileTool()
        args = self.cmd_svc.parse_tool_arguments(tool, "main.py 40")
        self.assertEqual(args, {"file_path": "main.py", "max_lines": 40})

    def test_build_enriched_prompt_success(self):
        tool = CalculatorTool()
        args_dict = {"expression": "25 * 4"}
        exec_res = {"success": True, "result": {"result": 100}}
        user_prompt = "¿Cuánto es en dólares si 1 USD = 20?"

        prompt = self.cmd_svc.build_enriched_prompt(tool, args_dict, exec_res, user_prompt)
        self.assertIn("[Herramienta ejecutada manualmente: calculator]", prompt)
        self.assertIn('"result": 100', prompt)
        self.assertIn("Instrucción del usuario:", prompt)
        self.assertIn(user_prompt, prompt)

    def test_build_enriched_prompt_error(self):
        tool = CalculatorTool()
        args_dict = {"expression": "1 / 0"}
        exec_res = {"success": False, "error": "division by zero"}

        prompt = self.cmd_svc.build_enriched_prompt(tool, args_dict, exec_res, user_prompt=None)
        self.assertIn("[Error al ejecutar herramienta manual: calculator]", prompt)
        self.assertIn("division by zero", prompt)
        self.assertIn("Informa al usuario sobre el inconveniente", prompt)

    @patch("core.command_service.get_tools_config")
    @patch("tools.registry.registry.execute_tool")
    @patch("gui.tools_view.render_tool_result")
    def test_execute_manual_tool_success(self, mock_render, mock_exec, mock_get_cfg):
        mock_get_cfg.return_value = {
            "enabled": True,
            "tools": {"calculator": {"enabled": True, "require_confirmation": False}}
        }
        mock_exec.return_value = {"success": True, "result": {"result": 42}}

        tool = CalculatorTool()
        success, res, cancelled = self.cmd_svc.execute_manual_tool(tool, {"expression": "6 * 7"})

        self.assertTrue(success)
        self.assertFalse(cancelled)
        self.assertEqual(res["result"]["result"], 42)
        mock_render.assert_called_once()

    @patch("core.command_service.get_tools_config")
    @patch("gui.tools_view.ask_tool_confirmation", return_value=False)
    def test_execute_manual_tool_cancelled(self, mock_ask_confirm, mock_get_cfg):
        mock_get_cfg.return_value = {
            "enabled": True,
            "tools": {"execute_bash": {"enabled": True, "require_confirmation": True}}
        }
        tool = BashTool()
        success, res, cancelled = self.cmd_svc.execute_manual_tool(tool, {"command": "rm -rf /tmp/foo"})

        self.assertFalse(success)
        self.assertTrue(cancelled)
        mock_ask_confirm.assert_called_once()

    def test_handle_session_command_exit(self):
        args = argparse.Namespace()
        result = self.cmd_svc.handle_session_command("exit", "", args)
        self.assertTrue(result.is_command)
        self.assertTrue(result.should_exit)
        self.assertTrue(result.should_skip_model)

    @patch("core.chat_service.clear_context")
    def test_handle_session_command_clear(self, mock_clear_context):
        args = argparse.Namespace()
        result = self.cmd_svc.handle_session_command("clear", "", args)
        self.assertTrue(result.is_command)
        self.assertFalse(result.should_exit)
        self.assertTrue(result.should_skip_model)
        mock_clear_context.assert_called_once()

    def test_handle_session_command_model(self):
        args = argparse.Namespace(model="qwen2.5:1.5b")
        result = self.cmd_svc.handle_session_command("model", "llama3.2:3b", args)
        self.assertTrue(result.is_command)
        self.assertEqual(args.model, "llama3.2:3b")
        self.assertTrue(result.should_skip_model)

    @patch("core.command_service.CommandService.show_help")
    def test_handle_session_command_help(self, mock_show_help):
        args = argparse.Namespace()
        result = self.cmd_svc.handle_session_command("help", "", args)
        self.assertTrue(result.is_command)
        self.assertTrue(result.should_skip_model)
        mock_show_help.assert_called_once()


class TestCoreServiceCommandIntegration(unittest.TestCase):

    @patch("core.core_service.send_chat_request")
    def test_instant_req_with_tool_command(self, mock_send_req):
        mock_send_req.return_value = 0
        args = argparse.Namespace(text="/calc 10 + 20")

        exit_code = instant_req(args)

        self.assertEqual(exit_code, 0)
        mock_send_req.assert_called_once()
        user_input_arg = mock_send_req.call_args[1].get("user_input")
        self.assertIn("[Herramienta ejecutada manualmente: calculator]", user_input_arg)
        self.assertIn('"result": 30', user_input_arg)

    @patch("core.core_service.send_chat_request")
    def test_instant_req_with_session_command_help(self, mock_send_req):
        args = argparse.Namespace(text="/help")
        with patch("core.command_service.command_service.show_help"):
            exit_code = instant_req(args)
            self.assertEqual(exit_code, 0)
            mock_send_req.assert_not_called()

    @patch("core.core_service.send_chat_request")
    def test_handle_interactive_chat_turn_normal_text(self, mock_send_req):
        mock_send_req.return_value = 0
        args = argparse.Namespace()
        should_continue, code = handle_interactive_chat_turn("Hola asistente", args)

        self.assertTrue(should_continue)
        self.assertEqual(code, 0)
        mock_send_req.assert_called_once_with(args, user_input="Hola asistente")

    @patch("core.core_service.send_chat_request")
    def test_handle_interactive_chat_turn_tool_command(self, mock_send_req):
        mock_send_req.return_value = 0
        args = argparse.Namespace()
        should_continue, code = handle_interactive_chat_turn("/calc 5 * 5", args)

        self.assertTrue(should_continue)
        self.assertEqual(code, 0)
        mock_send_req.assert_called_once()
        user_input_arg = mock_send_req.call_args[1].get("user_input")
        self.assertIn('"result": 25', user_input_arg)

    @patch("core.core_service.send_chat_request")
    def test_handle_interactive_chat_turn_image_command(self, mock_send_req):
        mock_send_req.return_value = 0
        args = argparse.Namespace()
        should_continue, code = handle_interactive_chat_turn("/image test.png ¿Qué hay aquí?", args)

        self.assertTrue(should_continue)
        self.assertEqual(code, 0)
        mock_send_req.assert_called_once_with(args, user_input="¿Qué hay aquí?", images=["test.png"])

    @patch("core.core_service.send_chat_request")
    def test_handle_interactive_chat_turn_image_without_path(self, mock_send_req):
        args = argparse.Namespace()
        should_continue, code = handle_interactive_chat_turn("/image", args)

        self.assertTrue(should_continue)
        self.assertEqual(code, 0)
        mock_send_req.assert_not_called()

    def test_handle_interactive_chat_turn_exit(self):
        args = argparse.Namespace()
        should_continue, code = handle_interactive_chat_turn("/exit", args)
        self.assertFalse(should_continue)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
