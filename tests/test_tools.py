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
        result = tool.run(command="echo 'iamarker_test'")
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["exit_code"], 0)
        self.assertIn("iamarker_test", result["result"]["stdout"])

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


if __name__ == "__main__":
    unittest.main()
