from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Clase base abstracta para todas las herramientas de IAMarker."""

    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    require_confirmation: bool = False
    enabled_by_default: bool = True

    def to_ollama_tool(self) -> Dict[str, Any]:
        """Convierte la definición de la herramienta al formato compatible con la API de Ollama."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Ejecuta la lógica de la herramienta y retorna un resultado serializable."""
        pass

    def run(self, **kwargs) -> Dict[str, Any]:
        """Envoltorio seguro para ejecutar la herramienta capturando excepciones."""
        try:
            result = self.execute(**kwargs)
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
