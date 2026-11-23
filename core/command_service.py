import json
import shlex
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from colorama import Fore, Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tools.base import BaseTool
from tools.registry import registry
from utils.helpers import get_config, get_tools_config, parse_option_value


@dataclass
class CommandDispatchResult:
    """Resultado del procesamiento de un comando."""
    is_command: bool
    handled: bool = False
    should_exit: bool = False
    should_skip_model: bool = False
    enriched_prompt: Optional[str] = None
    exit_code: int = 0
    error_message: Optional[str] = None


class CommandService:
    """Servicio central para la detección, resolución y ejecución de comandos slash (/command)."""

    SESSION_COMMANDS = {
        "help": "Muestra la guía de comandos slash y herramientas disponibles.",
        "tools": "Muestra el estado detallado de las herramientas del sistema.",
        "clear": "Limpia el contexto de la conversación en memoria.",
        "model": "Muestra o cambia temporalmente el modelo activo en la sesión.",
        "exit": "Termina la sesión interactiva.",
    }

    def is_command(self, text: Optional[str]) -> bool:
        """Determina si un texto ingresado por el usuario es un comando slash o palabra clave de control."""
        if not text:
            return False
        stripped = text.strip()
        if not stripped:
            return False
        if stripped.startswith("/"):
            return True
        if stripped.lower() in ["exit", "quit"]:
            return True
        return False

    def parse_command_input(self, raw_input: str) -> Tuple[str, str, Optional[str]]:
        """Parsea la entrada del usuario extrayendo:
        1. El nombre del comando (sin la barra '/')
        2. Los argumentos para la herramienta o comando (antes de '--')
        3. La instrucción opcional para el modelo LLM (después de '--')
        """
        stripped = raw_input.strip()
        if stripped.startswith("/"):
            stripped = stripped[1:]

        user_prompt: Optional[str] = None
        if " -- " in stripped:
            parts = stripped.split(" -- ", 1)
            command_part = parts[0].strip()
            user_prompt = parts[1].strip() or None
        else:
            command_part = stripped

        tokens = command_part.split(maxsplit=1)
        if not tokens:
            return "", "", user_prompt

        command_name = tokens[0].lower().strip()
        args_str = tokens[1].strip() if len(tokens) > 1 else ""

        return command_name, args_str, user_prompt

    def find_tool_by_command(self, command_name: str) -> Optional[BaseTool]:
        """Busca una herramienta en el registro por su nombre exacto o por cualquiera de sus alias."""
        if not command_name:
            return None

        cmd_lower = command_name.lower()
        for tool in registry.list_tools():
            if tool.name.lower() == cmd_lower:
                return tool
            aliases = [a.lower() for a in getattr(tool, "aliases", [])]
            if cmd_lower in aliases:
                return tool

        return None

    def parse_tool_arguments(self, tool: BaseTool, args_str: str) -> Dict[str, Any]:
        """Convierte la cadena de argumentos en un diccionario apto para tool.run(**kwargs).
        Soporta:
        - Argumentos clave=valor (ej. file_path=main.py max_lines=20)
        - Argumento posicional único mapeado a tool.primary_arg
        - Detección de tipos comunes (bool, int, float)
        """
        if not args_str:
            return {}

        args_dict: Dict[str, Any] = {}

        # Intentar tokenizar con shlex respetando comillas
        try:
            tokens = shlex.split(args_str)
        except ValueError:
            tokens = args_str.split()

        # Comprobar si hay argumentos explícitos clave=valor
        has_key_values = any("=" in t for t in tokens)

        if has_key_values:
            pos_index = 0
            properties = tool.parameters.get("properties", {}) if tool.parameters else {}
            prop_keys = list(properties.keys())

            for token in tokens:
                if "=" in token:
                    k, v = token.split("=", 1)
                    args_dict[k.strip()] = parse_option_value(v.strip())
                else:
                    # Argumento posicional residual
                    if pos_index < len(prop_keys):
                        target_key = prop_keys[pos_index]
                        args_dict[target_key] = parse_option_value(token)
                        pos_index += 1
            return args_dict

        # Si no hay clave=valor y hay un argumento primario definido
        if tool.primary_arg:
            # Si el argumento primario es calculator (expresión) o bash (comando), usamos todo args_str
            if tool.primary_arg in ["expression", "command"]:
                args_dict[tool.primary_arg] = args_str.strip()
                return args_dict

            # Si es read_file y vienen varios tokens (ej: file_path 50)
            properties = tool.parameters.get("properties", {}) if tool.parameters else {}
            if len(tokens) > 1 and "max_lines" in properties:
                args_dict[tool.primary_arg] = tokens[0]
                try:
                    args_dict["max_lines"] = int(tokens[1])
                except ValueError:
                    pass
                return args_dict

            # Asignación general al argumento primario
            args_dict[tool.primary_arg] = args_str.strip()
            return args_dict

        # Caso por defecto sin argumento primario (ej. formato en datetime si hay argumento)
        properties = tool.parameters.get("properties", {}) if tool.parameters else {}
        prop_keys = list(properties.keys())
        if prop_keys and args_str.strip():
            args_dict[prop_keys[0]] = args_str.strip()

        return args_dict

    def execute_manual_tool(
        self,
        tool: BaseTool,
        args_dict: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], bool]:
        """Ejecuta manualmente una herramienta validando estado y confirmación interactiva.
        Retorna (success, resultado_dict, fue_cancelado_por_usuario).
        """
        from gui.tools_view import ask_tool_confirmation, render_tool_result

        tools_cfg = get_tools_config()

        # 1. Validar que el sistema global esté activo
        if not tools_cfg.get("enabled", True):
            print(f"\n{Fore.YELLOW}⚠️  El sistema de herramientas está desactivado globalmente.{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Puedes reactivarlo con: {Fore.GREEN}python main.py toggle_tools{Style.RESET_ALL}\n")
            return False, {"error": "El sistema global de herramientas está desactivado."}, False

        # 2. Validar que la herramienta esté habilitada individualmente
        if not registry.is_tool_enabled(tool.name, tools_cfg):
            print(f"\n{Fore.YELLOW}⚠️  La herramienta '{Fore.CYAN}{tool.name}{Fore.YELLOW}' está desactivada en la configuración.{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Puedes activarla con: {Fore.GREEN}python main.py enable_tool -t {tool.name}{Style.RESET_ALL}\n")
            return False, {"error": f"La herramienta '{tool.name}' está desactivada."}, False

        # 3. Validar confirmación interactiva si la política lo exige
        needs_confirm = registry.is_confirmation_required(tool.name, tools_cfg)
        if needs_confirm:
            confirmed = ask_tool_confirmation(tool.name, args_dict)
            if not confirmed:
                return False, {"error": "Ejecución cancelada por el usuario."}, True
        else:
            confirmed = True
            print(f"{Fore.CYAN}⚡ [Ejecutando herramienta manual: {tool.name}]{Style.RESET_ALL}")

        # 4. Ejecutar la herramienta
        exec_res = registry.execute_tool(tool.name, args_dict, tools_config=tools_cfg, confirmed=confirmed)
        is_err = not exec_res.get("success", False)
        res_display = exec_res.get("result") if not is_err else exec_res.get("error")
        render_tool_result(tool.name, res_display, is_error=is_err)

        return exec_res.get("success", False), exec_res, False

    def build_enriched_prompt(
        self,
        tool: BaseTool,
        args_dict: Dict[str, Any],
        exec_res: Dict[str, Any],
        user_prompt: Optional[str]
    ) -> str:
        """Construye el mensaje enriquecido en Markdown que se le enviará al modelo LLM."""
        is_success = exec_res.get("success", False)
        data_content = exec_res.get("result") if is_success else exec_res.get("error")

        if isinstance(data_content, (dict, list)):
            formatted_data = json.dumps(data_content, indent=2, ensure_ascii=False)
        else:
            formatted_data = str(data_content)

        args_str = json.dumps(args_dict, ensure_ascii=False) if args_dict else "sin argumentos"

        if is_success:
            header = f"[Herramienta ejecutada manualmente: {tool.name}]"
            details = (
                f"{header}\n"
                f"Parámetros: {args_str}\n"
                f"Resultado obtenido:\n```json\n{formatted_data}\n```"
            )
            if user_prompt:
                final_instruction = f"Instrucción del usuario:\n{user_prompt}"
            else:
                final_instruction = (
                    "Por favor, analiza y presenta los datos obtenidos de la herramienta de forma clara, "
                    "precisa y útil para el usuario."
                )
        else:
            header = f"[Error al ejecutar herramienta manual: {tool.name}]"
            details = (
                f"{header}\n"
                f"Parámetros: {args_str}\n"
                f"Detalle del error:\n```\n{formatted_data}\n```"
            )
            if user_prompt:
                final_instruction = f"Pregunta del usuario a pesar del error:\n{user_prompt}"
            else:
                final_instruction = (
                    "Informa al usuario sobre el inconveniente ocurrido al ejecutar la herramienta y sugiere "
                    "cómo solucionarlo o ingresar parámetros válidos."
                )

        return f"{details}\n\n{final_instruction}"

    def show_help(self) -> None:
        """Muestra una pantalla de ayuda Rich con comandos de sesión, herramientas y ejemplos."""
        console = Console(force_terminal=True)

        table_session = Table(
            title="[bold cyan]Comandos de Control de Sesión[/bold cyan]",
            header_style="bold magenta",
            border_style="dim blue",
            show_lines=False
        )
        table_session.add_column("Comando", style="bold green", min_width=14)
        table_session.add_column("Descripción", justify="left")

        for cmd, desc in self.SESSION_COMMANDS.items():
            table_session.add_row(f"/{cmd}", desc)

        table_tools = Table(
            title="[bold cyan]Herramientas Disponibles para Ejecución Manual[/bold cyan]",
            header_style="bold yellow",
            border_style="dim blue",
            show_lines=False
        )
        table_tools.add_column("Herramienta", style="bold cyan", min_width=20)
        table_tools.add_column("Comando / Alias", style="bold green", min_width=22)
        table_tools.add_column("Descripción", justify="left")

        for tool in registry.list_tools():
            aliases = getattr(tool, "aliases", [])
            alias_str = ", ".join([f"/{a}" for a in aliases]) if aliases else f"/{tool.name}"
            cmd_display = f"/{tool.name}\n[dim]({alias_str})[/dim]" if aliases else f"/{tool.name}"
            table_tools.add_row(tool.name, cmd_display, tool.description)

        console.print()
        console.print(table_session)
        console.print()
        console.print(table_tools)

        panel_syntax = Panel(
            "[bold white]1. Ejecución simple:[/bold white]\n"
            "   [cyan]/calc 150 * 1.16[/cyan]  o  [cyan]/weather Madrid[/cyan]  o  [cyan]/datetime[/cyan]\n\n"
            "[bold white]2. Ejecución con instrucción adicional para el modelo (usando '--'):[/bold white]\n"
            "   [cyan]/read_file README.md -- Resume los puntos principales[/cyan]\n"
            "   [cyan]/weather Tokio -- ¿Qué tipo de ropa debo empacar para este clima?[/cyan]\n"
            "   [cyan]/bash git status -- Explica qué cambios están pendientes de commit[/cyan]",
            title="[bold yellow]💡 Guía de Sintaxis[/bold yellow]",
            border_style="yellow",
            expand=False
        )
        console.print()
        console.print(panel_syntax)
        console.print()

    def handle_session_command(
        self,
        command_name: str,
        args_str: str,
        args: Any
    ) -> CommandDispatchResult:
        """Maneja comandos que controlan la sesión interactiva (no llaman a Ollama)."""
        from core.chat_service import clear_context

        cmd = command_name.lower()

        if cmd in ["exit", "quit"]:
            from gui.render import render_message
            render_message("System", "**Saliendo...**")
            return CommandDispatchResult(is_command=True, handled=True, should_exit=True, should_skip_model=True)

        if cmd == "help":
            self.show_help()
            return CommandDispatchResult(is_command=True, handled=True, should_skip_model=True)

        if cmd == "tools":
            from core.core_service import show_tools
            show_tools(args)
            return CommandDispatchResult(is_command=True, handled=True, should_skip_model=True)

        if cmd == "clear":
            clear_context()
            print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ Contexto de la conversación en memoria limpiado exitosamente.{Style.RESET_ALL}\n")
            return CommandDispatchResult(is_command=True, handled=True, should_skip_model=True)

        if cmd == "model":
            target_model = args_str.strip()
            if target_model:
                args.model = target_model
                print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ Modelo de la sesión cambiado a: {Fore.CYAN}{target_model}{Style.RESET_ALL}\n")
            else:
                current_model = getattr(args, "model", None) or get_config("model")
                print(f"\n{Fore.CYAN}ℹ️  Modelo activo actualmente: {Fore.GREEN}{current_model}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Tip: Cambia el modelo temporalmente con: {Fore.CYAN}/model <nombre>{Style.RESET_ALL}\n")
            return CommandDispatchResult(is_command=True, handled=True, should_skip_model=True)

        return CommandDispatchResult(is_command=True, handled=False)

    def dispatch(
        self,
        raw_input: str,
        args: Any
    ) -> CommandDispatchResult:
        """Punto de entrada principal para despachar cualquier input del usuario en instant_req, chat o continue_chat."""
        if not self.is_command(raw_input):
            return CommandDispatchResult(is_command=False)

        cmd_name, tool_args_str, user_prompt = self.parse_command_input(raw_input)

        # 1. Comprobar si es un comando de sesión (/help, /tools, /clear, /model, /exit)
        if cmd_name in self.SESSION_COMMANDS or cmd_name in ["quit"]:
            return self.handle_session_command(cmd_name, tool_args_str, args)

        # 2. Comprobar si corresponde a una herramienta registrada
        tool = self.find_tool_by_command(cmd_name)
        if not tool:
            print(f"\n{Fore.RED}{Style.BRIGHT}Error: Comando '/{cmd_name}' no reconocido.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Escribe {Fore.CYAN}/help{Fore.YELLOW} para ver la lista de comandos y herramientas disponibles.{Style.RESET_ALL}\n")
            return CommandDispatchResult(
                is_command=True,
                handled=False,
                should_skip_model=True,
                exit_code=1,
                error_message=f"Comando '/{cmd_name}' no reconocido."
            )

        # 3. Parsear argumentos de la herramienta
        parsed_args = self.parse_tool_arguments(tool, tool_args_str)

        # 4. Ejecutar la herramienta manualmente
        success, exec_res, was_cancelled = self.execute_manual_tool(tool, parsed_args)
        if was_cancelled:
            return CommandDispatchResult(
                is_command=True,
                handled=True,
                should_skip_model=True,
                exit_code=0
            )

        # 5. Construir prompt enriquecido para el modelo LLM
        enriched_prompt = self.build_enriched_prompt(tool, parsed_args, exec_res, user_prompt)

        return CommandDispatchResult(
            is_command=True,
            handled=True,
            should_skip_model=False,
            enriched_prompt=enriched_prompt,
            exit_code=0
        )


# Instancia singleton del despachador
command_service = CommandService()
