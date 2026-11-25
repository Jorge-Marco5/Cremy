from typing import Any, Dict, List, Optional
from tools.base import BaseTool
from tools.definitions import (
    DateTimeTool,
    CalculatorTool,
    ReadFileTool,
    BashTool,
)


class ToolRegistry:
    """Registro central de herramientas disponibles en Cremy."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Registra las herramientas integradas por defecto."""
        self.register(DateTimeTool())
        self.register(CalculatorTool())
        self.register(ReadFileTool())
        self.register(BashTool())

    def register(self, tool: BaseTool):
        """Registra una instancia de herramienta en el registro."""
        if not tool.name:
            raise ValueError("La herramienta debe tener un nombre definido.")
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Obtiene una herramienta por su nombre."""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """Retorna la lista de todas las herramientas registradas."""
        return list(self._tools.values())

    def get_default_tools_config(self) -> Dict[str, Any]:
        """Genera el esquema de configuración por defecto para config.json."""
        return {
            "enabled": True,
            "require_confirmation": True,
            "tools": {
                tool.name: {
                    "enabled": tool.enabled_by_default,
                    "require_confirmation": tool.require_confirmation
                }
                for tool in self._tools.values()
            }
        }

    def get_active_tools_schemas(self, tools_config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Retorna los esquemas de herramientas habilitadas para enviar a la API de Ollama."""
        cfg = tools_config or {}
        if not cfg.get("enabled", True):
            return []

        tools_settings = cfg.get("tools", {})
        active_schemas = []

        for tool in self._tools.values():
            tool_setting = tools_settings.get(tool.name, {})
            is_enabled = tool_setting.get("enabled", tool.enabled_by_default)
            if is_enabled:
                active_schemas.append(tool.to_ollama_tool())

        return active_schemas

    def is_tool_enabled(self, tool_name: str, tools_config: Optional[Dict[str, Any]] = None) -> bool:
        """Determina si una herramienta existe y está habilitada tanto a nivel global como individual."""
        tool = self.get_tool(tool_name)
        if not tool:
            return False

        cfg = tools_config or {}
        if not cfg.get("enabled", True):
            return False

        tool_setting = cfg.get("tools", {}).get(tool_name, {})
        return bool(tool_setting.get("enabled", tool.enabled_by_default))

    def is_confirmation_required(self, tool_name: str, tools_config: Optional[Dict[str, Any]] = None) -> bool:
        """Determina si una herramienta requiere confirmación previa del usuario."""
        tool = self.get_tool(tool_name)
        if not tool:
            return True

        cfg = tools_config or {}
        tool_settings = cfg.get("tools", {}).get(tool_name, {})

        # Si hay configuración explícita para la herramienta, usarla
        if "require_confirmation" in tool_settings:
            return bool(tool_settings["require_confirmation"])

        # Por defecto, usar la configuración de la propia herramienta
        return tool.require_confirmation

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tools_config: Optional[Dict[str, Any]] = None,
        confirmed: bool = False
    ) -> Dict[str, Any]:
        """Ejecuta una herramienta validando en el momento de ejecución:
        1. Que el sistema global de herramientas esté habilitado.
        2. Que la herramienta exista en el registro.
        3. Que esté habilitada individualmente en la configuración.
        4. Que se cumpla su política de confirmación requerida.
        """
        if tools_config is None:
            try:
                from utils.helpers import get_tools_config
                cfg = get_tools_config()
            except Exception:
                cfg = {}
        else:
            cfg = tools_config

        # 1. Que el sistema global de herramientas esté habilitado
        if not cfg.get("enabled", True):
            return {
                "success": False,
                "error": "El sistema global de herramientas está deshabilitado."
            }

        # 2. Que la herramienta exista
        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"Herramienta '{tool_name}' no encontrada en el registro."
            }

        # 3. Que esté habilitada individualmente
        tool_settings = cfg.get("tools", {}).get(tool_name, {})
        is_enabled = tool_settings.get("enabled", tool.enabled_by_default)
        if not is_enabled:
            return {
                "success": False,
                "error": f"La herramienta '{tool_name}' está deshabilitada en la configuración."
            }

        # 4. Que se cumpla su política de confirmación
        needs_confirm = self.is_confirmation_required(tool_name, cfg)
        if needs_confirm and not confirmed:
            return {
                "success": False,
                "error": f"La herramienta '{tool_name}' requiere confirmación explícita del usuario y no fue autorizada."
            }

        return tool.run(**arguments)


# Instancia singleton del registro de herramientas
registry = ToolRegistry()
