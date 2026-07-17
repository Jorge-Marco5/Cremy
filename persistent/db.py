import sqlite3
import os
from pathlib import Path
from datetime import datetime
from uuid import uuid4

file_path = "database.db"

class DataService:
    def __init__(self):
        """Inicializa la conexión a la base de datos de historial y crea la tabla si no existe."""
        db_path = Path(file_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self._create_table()

    def _create_table(self):
        """Crea la tabla de historial si no existe."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                uuid TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_uuid TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_uuid) REFERENCES Conversations (uuid)
            );
            """
        )

        self.conn.commit()

    #Configuraciones

    def create_conversation(self, name: str):
        """Crea una nueva conversacion en la tabla de configuraciones."""
        cursor = self.conn.cursor()
        uuid = str(uuid4())
        cursor.execute(""" INSERT INTO conversations (uuid, name) VALUES (?, ?) """, (uuid,name,))
        self.conn.commit()

        item = self.show_one(str(uuid))
        return item[0]

    def show_all(self):
        """Obtiene todas las conversaciones de la tabla de conversaciones."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT uuid, name, created_at FROM conversations")
        return cursor.fetchall()

    def show_one(self, uuid: str):
        """Obtiene una conversacion específica de la tabla de conversaciones."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT uuid, name, created_at FROM conversations WHERE uuid = ?",
            (uuid,)
        )
        return cursor.fetchone()

    def show_messages(self, uuid: str, limit: int = 20):
        """Obtiene el historial de mensajes de una conversacion específica."""
        if not uuid:
            print("No se proporcionó un UUID válido.")
            return None

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, role, content, created_at FROM messages WHERE conversation_uuid = ? ORDER BY created_at ASC LIMIT ?",
            (str(uuid), int(limit))
        )
        return cursor.fetchall()

    def insert_message(self, data: dict):
        """Guarda un nuevo mensaje de una conversacion."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO messages (
                conversation_uuid, role, content
            ) VALUES (?, ?, ?)
        """, (
            data["conversation_uuid"],
            data["role"],
            data["content"],
        ))

        self.conn.commit()
        return True

    def update(self, data: dict):
        """Actualiza el nombre de una conversacion."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE conversations SET
                name = ?
            WHERE uuid = ?
        """, (
            data["name"],
            data["uuid"]
        ))

        self.conn.commit()

        item = self.show_one(data['alias'])
        return item

    def delete(self, uuid: str):
        """Elimina una conversation de la tabla de configuraciones."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM conversations WHERE uuid = ?", (uuid,))
            cursor.execute("DELETE FROM messages WHERE conversation_uuid = ?", (uuid,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error al eliminar la configuracion: {e}")
            return False