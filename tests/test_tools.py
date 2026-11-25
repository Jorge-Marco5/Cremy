import unittest
import tempfile
import os
from tools.registry import ToolRegistry
from tools.definitions import DateTimeTool, CalculatorTool, ReadFileTool, BashTool


class TestTools(unittest.TestCase):

    def setUp(self):
        self.registry = ToolRegistry()

    def test_default_tools_registered(self):
        tools = self.registry.list_tools()
        names = [t.name for t in tools]
        self.assertIn("get_current_datetime", names)
        self.assertIn("calculator", names)
        self.assertIn("read_file", names)
        self.assertIn("execute_bash", names)

    def test_datetime_tool(self):
        tool = DateTimeTool()
        result = tool.run()
        self.assertTrue(result["success"])
        self.assertIn("datetime", result["result"])

    def test_calculator_tool_valid(self):
        tool = CalculatorTool()
        result = tool.run(expression="10 + 5 * 2")
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["result"], 20)

    def test_calculator_tool_power(self):
        tool = CalculatorTool()
        result = tool.run(expression="2 ^ 3")
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["result"], 8)

    def test_calculator_tool_invalid(self):
        tool = CalculatorTool()
        result = tool.run(expression="__import__('os').system('ls')")
        self.assertFalse(result["success"])

    def test_read_file_tool(self):
        tool = ReadFileTool()
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("Line 1\nLine 2\nLine 3\n")
            temp_path = f.name

        try:
            result = tool.run(file_path=temp_path, max_lines=2)
            self.assertTrue(result["success"])
            self.assertEqual(result["result"]["lines_read"], 2)
            self.assertTrue(result["result"]["truncated"])
            self.assertEqual(result["result"]["content"], "Line 1\nLine 2\n")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_bash_tool_echo(self):
        tool = BashTool()
        result = tool.run(command="echo 'Cremy_test'")
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["exit_code"], 0)
        self.assertIn("Cremy_test", result["result"]["stdout"])

    def test_registry_schemas_filtering(self):
        cfg = {
            "enabled": True,
            "tools": {
                "get_current_datetime": {"enabled": True},
                "calculator": {"enabled": False},
                "read_file": {"enabled": True},
                "execute_bash": {"enabled": False}
            }
        }
        schemas = self.registry.get_active_tools_schemas(cfg)
        tool_names = [s["function"]["name"] for s in schemas]
        self.assertIn("get_current_datetime", tool_names)
        self.assertIn("read_file", tool_names)
        self.assertNotIn("calculator", tool_names)
        self.assertNotIn("execute_bash", tool_names)

    def test_registry_global_disable(self):
        cfg = {"enabled": False}
        schemas = self.registry.get_active_tools_schemas(cfg)
        self.assertEqual(schemas, [])

    def test_confirmation_required(self):
        cfg = {
            "tools": {
                "get_current_datetime": {"require_confirmation": True},
                "execute_bash": {"require_confirmation": False}
            }
        }
        self.assertTrue(self.registry.is_confirmation_required("get_current_datetime", cfg))
        self.assertFalse(self.registry.is_confirmation_required("execute_bash", cfg))

    def test_helpers_tool_config(self):
        from utils.helpers import get_tools_config, update_tool_setting, toggle_tools_global
        cfg = get_tools_config()
        self.assertIn("tools", cfg)
        self.assertIn("calculator", cfg["tools"])

        update_tool_setting("calculator", enabled=False, require_confirmation=True)
        updated_cfg = get_tools_config()
        self.assertFalse(updated_cfg["tools"]["calculator"]["enabled"])
        self.assertTrue(updated_cfg["tools"]["calculator"]["require_confirmation"])

        # Restaurar
        update_tool_setting("calculator", enabled=True, require_confirmation=False)

        # Toggle global
        curr = get_tools_config().get("enabled", True)
        new_val = toggle_tools_global()
        self.assertNotEqual(curr, new_val)
        toggle_tools_global(True)
        self.assertTrue(get_tools_config()["enabled"])

    def test_is_tool_enabled(self):
        cfg = {
            "enabled": True,
            "tools": {
                "calculator": {"enabled": True},
                "read_file": {"enabled": False}
            }
        }
        self.assertTrue(self.registry.is_tool_enabled("calculator", cfg))
        self.assertFalse(self.registry.is_tool_enabled("read_file", cfg))
        self.assertFalse(self.registry.is_tool_enabled("herramienta_fantasma", cfg))

        # Cuando está deshabilitado globalmente
        cfg_disabled = {"enabled": False, "tools": {"calculator": {"enabled": True}}}
        self.assertFalse(self.registry.is_tool_enabled("calculator", cfg_disabled))

    def test_execute_tool_runtime_validations(self):
        # 1. Global deshabilitado
        cfg_global_off = {"enabled": False}
        res = self.registry.execute_tool("calculator", {"expression": "2+2"}, tools_config=cfg_global_off)
        self.assertFalse(res["success"])
        self.assertIn("deshabilitado", res["error"])

        # 2. Herramienta no existente
        cfg_ok = {"enabled": True, "tools": {}}
        res = self.registry.execute_tool("non_existent_tool", {}, tools_config=cfg_ok)
        self.assertFalse(res["success"])
        self.assertIn("no encontrada", res["error"])

        # 3. Herramienta deshabilitada individualmente
        cfg_tool_off = {
            "enabled": True,
            "tools": {"calculator": {"enabled": False}}
        }
        res = self.registry.execute_tool("calculator", {"expression": "2+2"}, tools_config=cfg_tool_off)
        self.assertFalse(res["success"])
        self.assertIn("deshabilitada en la configuración", res["error"])

        # 4. Requiere confirmación y no fue confirmada
        cfg_confirm = {
            "enabled": True,
            "tools": {"calculator": {"enabled": True, "require_confirmation": True}}
        }
        res = self.registry.execute_tool("calculator", {"expression": "2+2"}, tools_config=cfg_confirm, confirmed=False)
        self.assertFalse(res["success"])
        self.assertIn("no fue autorizada", res["error"])

        # 5. Requiere confirmación y sí fue autorizada
        res = self.registry.execute_tool("calculator", {"expression": "2+2"}, tools_config=cfg_confirm, confirmed=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["result"]["result"], 4)

        # 6. No requiere confirmación
        cfg_no_confirm = {
            "enabled": True,
            "tools": {"calculator": {"enabled": True, "require_confirmation": False}}
        }
        res = self.registry.execute_tool("calculator", {"expression": "5 * 4"}, tools_config=cfg_no_confirm, confirmed=False)
        self.assertTrue(res["success"])
        self.assertEqual(res["result"]["result"], 20)




if __name__ == "__main__":
    unittest.main()
