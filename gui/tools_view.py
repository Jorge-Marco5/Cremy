import json
import sys
from typing import Any, Dict
from rich.panel import Panel
from rich.syntax import Syntax

from gui.theme import (
    CatppuccinMocha,
    CatppuccinMochaPygmentsStyle,
    C_ERROR,
    C_RESET,
    C_SUCCESS,
    C_WARNING,
    console,
)


def render_tool_call_request(tool_name: str, arguments: Dict[str, Any]):
    """Muestra una tarjeta estilizada en la terminal cuando el modelo solicita ejecutar una herramienta."""
    args_json = json.dumps(arguments, indent=2, ensure_ascii=False)
    syntax = Syntax(args_json, lexer="json", theme=CatppuccinMochaPygmentsStyle, word_wrap=True)

    panel = Panel(
        syntax,
        title=f"[bold {CatppuccinMocha.PEACH}]Llamada a Herramienta: [bold {CatppuccinMocha.TEAL}]{tool_name}[/bold {CatppuccinMocha.TEAL}][/bold {CatppuccinMocha.PEACH}]",
        subtitle=f"[{CatppuccinMocha.OVERLAY0}]Parámetros de ejecución[/]",
        border_style=CatppuccinMocha.PEACH,
        expand=False,
    )
    console.print(panel)


def ask_tool_confirmation(tool_name: str, arguments: Dict[str, Any]) -> bool:
    """Muestra los detalles de la herramienta y solicita confirmación interactiva al usuario."""
    render_tool_call_request(tool_name, arguments)

    prompt_text = (
        f"{C_WARNING}¿Deseas permitir la ejecución de esta herramienta? "
        f"{C_RESET}[{C_SUCCESS}s{C_RESET}/{C_ERROR}n{C_RESET}]: "
    )
    try:
        user_choice = input(prompt_text).strip().lower()
        if user_choice in ["s", "si", "sí", "y", "yes"]:
            print(f"{C_SUCCESS}Ejecución autorizada por el usuario.{C_RESET}\n")
            return True
        else:
            print(f"{C_ERROR}Ejecución denegada por el usuario.{C_RESET}\n")
            return False
    except (KeyboardInterrupt, EOFError):
        print(f"\n{C_ERROR}Operación cancelada.{C_RESET}\n")
        return False


def render_tool_result(tool_name: str, result: Any, is_error: bool = False):
    """Muestra el resultado devuelto por la herramienta de forma limpia y formateada."""
    if is_error:
        title = f"[bold {CatppuccinMocha.RED}]Error en {tool_name}[/]"
        border_style = CatppuccinMocha.RED
    else:
        title = (
            f"[bold {CatppuccinMocha.GREEN}]Resultado de "
            f"[bold {CatppuccinMocha.TEAL}]{tool_name}[/][/]"
        )
        border_style = CatppuccinMocha.GREEN

    if isinstance(result, (dict, list)):
        text_content = json.dumps(result, indent=2, ensure_ascii=False)
        syntax = Syntax(
            text_content, lexer="json", theme=CatppuccinMochaPygmentsStyle, word_wrap=True
        )
        content_to_print = syntax
    else:
        content_to_print = str(result)

    panel = Panel(
        content_to_print,
        title=title,
        border_style=border_style,
        expand=False,
    )
    console.print(panel)
