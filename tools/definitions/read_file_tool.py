import os
from pathlib import Path
from typing import Any, Dict
from tools.base import BaseTool


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Lee el contenido de un archivo de texto en el sistema de archivos local."
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Ruta relativa o absoluta del archivo a leer."
            },
            "max_lines": {
                "type": "integer",
                "description": "Número máximo de líneas a leer (por defecto 200)."
            }
        },
        "required": ["file_path"]
    }
    require_confirmation = False
    enabled_by_default = True

    def execute(self, **kwargs) -> Dict[str, Any]:
        file_path_str = kwargs.get("file_path", "").strip()
        max_lines = kwargs.get("max_lines") or 200

        if not file_path_str:
            raise ValueError("Debes proporcionar una ruta de archivo válida.")

        target_path = Path(file_path_str).expanduser().resolve()

        if not target_path.exists():
            raise FileNotFoundError(f"El archivo '{file_path_str}' no existe.")

        if not target_path.is_file():
            raise ValueError(f"'{file_path_str}' no es un archivo regular.")

        lines = []
        truncated = False
        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            for idx, line in enumerate(f):
                if idx >= max_lines:
                    truncated = True
                    break
                lines.append(line)

        return {
            "file_path": str(target_path),
            "lines_read": len(lines),
            "truncated": truncated,
            "content": "".join(lines)
        }
