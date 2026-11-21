import json
import sys
from typing import Any, Dict
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from colorama import Fore, Style


def render_tool_call_request(tool_name: str, arguments: Dict[str, Any]):
    """Muestra una tarjeta estilizada en la terminal cuando el modelo solicita ejecutar una herramienta."""
    console = Console(force_terminal=True)
    args_json = json.dumps(arguments, indent=2, ensure_ascii=False)
    syntax = Syntax(args_json, lexer="json", theme="github-dark", word_wrap=True)

    panel = Panel(
        syntax,
        title=f"[bold yellow]🛠️  Llamada a Herramienta: [bold cyan]{tool_name}[/bold cyan][/bold yellow]",
        subtitle="[dim]Parámetros de ejecución[/dim]",
        border_style="yellow",
        expand=False
    )
    console.print(panel)


def ask_tool_confirmation(tool_name: str, arguments: Dict[str, Any]) -> bool:
    """Muestra los detalles de la herramienta y solicita confirmación interactiva al usuario."""
    render_tool_call_request(tool_name, arguments)
    
    prompt_text = (
        f"{Fore.YELLOW}{Style.BRIGHT}¿Deseas permitir la ejecución de esta herramienta? "
        f"{Style.RESET_ALL}[{Fore.GREEN}s{Style.RESET_ALL}/{Fore.RED}n{Style.RESET_ALL}]: "
    )
    try:
        user_choice = input(prompt_text).strip().lower()
        if user_choice in ["s", "si", "sí", "y", "yes"]:
            print(f"{Fore.GREEN}✓ Ejecución autorizada por el usuario.{Style.RESET_ALL}\n")
            return True
        else:
            print(f"{Fore.RED}✗ Ejecución denegada por el usuario.{Style.RESET_ALL}\n")
            return False
    except (KeyboardInterrupt, EOFError):
        print(f"\n{Fore.RED}✗ Operación cancelada.{Style.RESET_ALL}\n")
        return False


def render_tool_result(tool_name: str, result: Any, is_error: bool = False):
    """Muestra el resultado devuelto por la herramienta de forma limpia y formateada."""
    console = Console(force_terminal=True)
    if is_error:
        icon = "[bold red]✗[/bold red]"
        title = f"{icon} Error en [bold red]{tool_name}[/bold red]"
        border_style = "red"
    else:
        icon = "[bold green]✓[/bold green]"
        title = f"{icon} Resultado de [bold cyan]{tool_name}[/bold cyan]"
        border_style = "green"

    if isinstance(result, (dict, list)):
        text_content = json.dumps(result, indent=2, ensure_ascii=False)
        syntax = Syntax(text_content, lexer="json", theme="github-dark", word_wrap=True)
        content_to_print = syntax
    else:
        content_to_print = str(result)

    panel = Panel(
        content_to_print,
        title=title,
        border_style=border_style,
        expand=False
    )
    console.print(panel)
