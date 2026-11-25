from abc import ABC, abstractmethod
import asyncio
import inspect
from typing import Any, Dict, List, Optional


class BaseTool(ABC):
    """Clase base abstracta para todas las herramientas de Cremy."""

    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    require_confirmation: bool = False
    enabled_by_default: bool = True
    aliases: List[str] = []
    primary_arg: Optional[str] = None

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
        """Ejecuta la lógica de la herramienta y retorna un resultado serializable.
        
        Puede ser un método síncrono 'def execute' o asíncrono 'async def execute'.
        """
        pass

    def run(self, **kwargs) -> Dict[str, Any]:
        """Envoltorio seguro para ejecutar la herramienta capturando excepciones.
        Soporta automáticamente funciones síncronas o corrutinas asíncronas (asyncio).
        """
        try:
            if inspect.iscoroutinefunction(self.execute):
                result = asyncio.run(self.execute(**kwargs))
            else:
                result = self.execute(**kwargs)
                if inspect.iscoroutine(result):
                    result = asyncio.run(result)

            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

