import subprocess
from typing import Any, Dict
from tools.base import BaseTool


class BashTool(BaseTool):
    name = "execute_bash"
    description = "Ejecuta un comando en la shell Bash de Linux y devuelve la salida estándar y de error."
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "El comando bash a ejecutar en la terminal (ej. 'ls -la', 'uname -a')."
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "Tiempo límite de ejecución en segundos (por defecto 15)."
            }
        },
        "required": ["command"]
    }
    # Por seguridad, requiere confirmación obligatoria y viene desactivada por defecto
    require_confirmation = True
    enabled_by_default = False

    def execute(self, **kwargs) -> Dict[str, Any]:
        command = kwargs.get("command", "").strip()
        timeout = kwargs.get("timeout_seconds") or 15

        if not command:
            raise ValueError("El comando bash no puede estar vacío.")

        try:
            result = subprocess.run(
                command,
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "command": command,
                "exit_code": -1,
                "error": f"Tiempo límite de ejecución agotado ({timeout} segundos)."
            }
