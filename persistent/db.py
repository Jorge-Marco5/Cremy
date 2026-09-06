import sqlite3
import os
from pathlib import Path
from datetime import datetime
from uuid import uuid4
BASE_DIR = Path(__file__).resolve().parent.parent
file_path = BASE_DIR / "database.db"

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
                model TEXT DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        try:
            cursor.execute("ALTER TABLE conversations ADD COLUMN model TEXT DEFAULT NULL;")
        except sqlite3.OperationalError:
            pass

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_uuid TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                images TEXT DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_uuid) REFERENCES conversations (uuid)
            );
            """
        )
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN images TEXT DEFAULT NULL;")
        except sqlite3.OperationalError:
            pass

        self.conn.commit()

    #Configuraciones

    def create_conversation(self, name: str, model: str = None):
        """Crea una nueva conversacion en la tabla de configuraciones."""
        cursor = self.conn.cursor()
        uuid = str(uuid4())
        cursor.execute(
            """ INSERT INTO conversations (uuid, name, model) VALUES (?, ?, ?) """,
            (uuid, name, model)
        )
        self.conn.commit()

        item = self.show_one(str(uuid))
        return item[0]

    def show_all(self):
        """Obtiene todas las conversaciones de la tabla de conversaciones ordenadas de forma descendente en base a la fecha de creacion."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT uuid, name, created_at, model FROM conversations ORDER BY created_at DESC")
        return cursor.fetchall()

    def show_one(self, uuid: str):
        """Obtiene una conversacion específica de la tabla de conversaciones."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT uuid, name, created_at, model FROM conversations WHERE uuid = ?",
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
            "SELECT id, role, content, created_at, images FROM messages WHERE conversation_uuid = ? ORDER BY created_at ASC LIMIT ?",
            (str(uuid), int(limit))
        )
        return cursor.fetchall()

    def insert_message(self, data: dict):
        """Guarda un nuevo mensaje de una conversacion."""
        cursor = self.conn.cursor()
        images_val = data.get("images")
        if isinstance(images_val, list):
            import json
            images_val = json.dumps(images_val)

        cursor.execute("""
            INSERT INTO messages (
                conversation_uuid, role, content, images
            ) VALUES (?, ?, ?, ?)
        """, (
            data["conversation_uuid"],
            data["role"],
            data["content"],
            images_val,
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

        item = self.show_one(data['uuid'])
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