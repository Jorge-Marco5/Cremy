import unittest
import os
import tempfile
import sqlite3
from unittest.mock import patch
from persistent.db import DataService


class TestDatabaseTools(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_database.db")
        with patch("persistent.db.file_path", self.db_path):
            self.service = DataService()

    def tearDown(self):
        self.service.conn.close()
        self.temp_dir.cleanup()

    def test_insert_and_retrieve_tool_calls(self):
        uuid = self.service.create_conversation("Test Tool Conversation", model="qwen2.5:1.5b")
        
        # Guardar mensaje de usuario
        self.service.insert_message({
            "conversation_uuid": uuid,
            "role": "user",
            "content": "¿Cuánto es 2 + 2?"
        })

        # Guardar mensaje del asistente con tool_calls
        tool_calls = [
            {
                "function": {
                    "name": "calculator",
                    "arguments": {"expression": "2 + 2"}
                }
            }
        ]
        self.service.insert_message({
            "conversation_uuid": uuid,
            "role": "assistant",
            "content": "",
            "tool_calls": tool_calls
        })

        # Guardar respuesta de la herramienta
        self.service.insert_message({
            "conversation_uuid": uuid,
            "role": "tool",
            "content": '{"result": 4}'
        })

        messages = self.service.show_messages(uuid)
        self.assertEqual(len(messages), 3)

        # Verificar mensaje del asistente
        ast_msg = messages[1]
        self.assertEqual(ast_msg[1], "assistant")
        self.assertIn("calculator", ast_msg[5])

        # Verificar mensaje de herramienta
        tool_msg = messages[2]
        self.assertEqual(tool_msg[1], "tool")
        self.assertIn('"result": 4', tool_msg[2])


if __name__ == "__main__":
    unittest.main()
