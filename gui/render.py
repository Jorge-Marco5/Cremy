import json
import urllib.error
import urllib.request
from typing import Any, Dict, Iterable, List, Optional, Tuple

from halo import Halo
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from core.ollama_client import StreamEvent, stream_ollama_chat
from gui.theme import (
    CatppuccinMocha,
    CatppuccinMochaPygmentsStyle,
    C_ASSISTANT,
    C_ERROR,
    C_INFO,
    C_RESET,
    C_SUCCESS,
    C_SYSTEM,
    C_TOOL,
    C_USER,
    C_WARNING,
    ansi_hex,
    console,
)
from persistent.db import DataService
from utils.format_time import format_duration
from utils.helpers import save_usage


def render_banner(args=""):
    """
    Construcción y renderizado del banner principal en Catppuccin Mocha
    """
    # Capas de color para la mascota
    c_body = ansi_hex(CatppuccinMocha.ROSEWATER)
    c_crest = ansi_hex(CatppuccinMocha.TEXT, bold=True)
    c_eyes = ansi_hex(CatppuccinMocha.TEXT, bold=True)
    c_blush = ansi_hex(CatppuccinMocha.MAROON, bold=True)
    c_base = ansi_hex(CatppuccinMocha.OVERLAY2)

    # Texto
    c1 = ansi_hex(CatppuccinMocha.MAUVE, bold=True)
    c2 = ansi_hex(CatppuccinMocha.PINK, bold=True)
    c3 = ansi_hex(CatppuccinMocha.BLUE, bold=True)
    c4 = ansi_hex(CatppuccinMocha.TEAL, bold=True)
    c5 = ansi_hex(CatppuccinMocha.GREEN, bold=True)

    # Divisores
    c_div = ansi_hex(CatppuccinMocha.SURFACE1)

    banner_lines = [
        f"{c_crest}                      @:.                      {C_RESET}",
        f"{c_crest}                      @. @                    {C_RESET}",
        f"{c_crest}                     @....@                   {C_RESET}",
        f"{c_crest}                  .@.......@                  {C_RESET}",
        f"{c_body}               .@..........@                  {C_RESET}",
        f"{c_body}              @............{c_crest}@:@@               {C_RESET}",
        f"{c_body}            @..............{c_crest}@....@.            {C_RESET}",
        f"{c_body}           @................*{c_crest}@....@           {C_RESET}{c1}   /@@@@@@@{c2}   /@@@@@@ {c3}   /@@@@@@ {c4}  /@@@@@@/@@@@  {c5}/@@   /@@{C_RESET}",
        f"{c_body}          :@......................@           {C_RESET}{c1}  /@@_____/{c2}  /@@__  @@{c3}  /@@__  @@{c4} | @@_  @@_  @@|{c5} @@  | @@{C_RESET}",
        f"{c_body}        @...@...{c_eyes}:@@@{c_body}......{c_eyes}:@@@@{c_body}...@.          {C_RESET}{c1} | @@      {c2} | @@  \\__/{c3} | @@@@@@@@{c4} | @@ \\ @@ \\ @@|{c5} @@  | @@{C_RESET}",
        f"{c_body}       @.......{c_eyes}%@@  @{c_body}.....{c_eyes}@@@  @{c_body}.....@        {C_RESET}{c1} | @@      {c2} | @@  \\__/{c3} | @@@@@@@@{c4} | @@ \\ @@ \\ @@|{c5} @@  | @@{C_RESET}",
        f"{c_body}       @.......{c_eyes}%@@@@@{c_body}.....{c_eyes}@@@@@@{c_body}......@       {C_RESET}{c1} | @@      {c2} | @@      {c3} | @@_____/{c4} | @@ | @@ | @@|{c5} @@  | @@{C_RESET}",
        f"{c_body}      :@...........................+@.@       {C_RESET}{c1} |  @@@@@@@{c2} | @@      {c3} |  @@@@@@@{c4} | @@ | @@ | @@|{c5}  @@@@@@@{C_RESET}",
        f"{c_body}     @..@.......{c_blush}#{C_RESET}.............{c_blush}#{C_RESET}........@      {C_RESET}{c1}  \\_______/{c2} |__/      {c3}  \\_______/{c4} |__/ |__/ |__/ {c5}\\____  @@{C_RESET}",
        f"{c_body}    @.....@..............................@    {C_RESET}                                                {c5} /@@  | @@{C_RESET}",
        f"{c_body}    @.......:@...........................@   {C_RESET}{C_RESET}                                                 {c5}|  @@@@@@/{C_RESET}",
        f"{c_body}    @...........................@.......@     {C_RESET}                                                 {c5}\\______/ {C_RESET}",
        f"{c_body}     @............................@....@      {C_RESET}",
        f"{c_base}       '@@======...................@@@        {C_RESET}",
        f"{c_base}            @@@@====_________===@@@:            {C_RESET}",
    ]

    accents = [
        CatppuccinMocha.RED,
        CatppuccinMocha.MAROON,
        CatppuccinMocha.PEACH,
        CatppuccinMocha.FLAMINGO,
        CatppuccinMocha.YELLOW,
        CatppuccinMocha.ROSEWATER,
        CatppuccinMocha.GREEN,
        CatppuccinMocha.TEAL,
        CatppuccinMocha.SKY,
        CatppuccinMocha.SAPPHIRE,
        CatppuccinMocha.BLUE,
        CatppuccinMocha.LAVENDER,
        CatppuccinMocha.MAUVE,
        CatppuccinMocha.PINK,
    ]
    dots = " ".join(f"{ansi_hex(c)}●{C_RESET}" for c in accents)
    div_bar = f"{c_div}{'─' * 36}{C_RESET}"
    palette_line = f"   {div_bar} {dots} {div_bar}\n"

    print("\n" + "\n".join(banner_lines) + "\n" + palette_line)


def _build_response_renderable(
    thinking_text: str,
    content_text: str,
    is_thinking: bool = False,
) -> Group:
    """Construye el bloque Rich unificado (panel de razonamiento + Markdown nativo)."""
    renderables = []

    if thinking_text:
        title = (
            f"[italic {CatppuccinMocha.MAUVE}]Pensando...[/]"
            if is_thinking
            else f"[italic {CatppuccinMocha.OVERLAY1}]Razonamiento[/]"
        )
        thinking_panel = Panel(
            Text(thinking_text.strip(), style=f"italic {CatppuccinMocha.OVERLAY1}"),
            title=title,
            title_align="left",
            border_style=CatppuccinMocha.SURFACE2,
            padding=(0, 1),
        )
        renderables.append(thinking_panel)

    if content_text:
        renderables.append(
            Markdown(content_text, code_theme=CatppuccinMochaPygmentsStyle)
        )

    return Group(*renderables)


def render_event_stream(
    events: Iterable[StreamEvent],
    stream: bool,
    spinner: Optional[Any] = None,
    target_console: Console = console,
) -> Tuple[str, List[Dict[str, Any]], int, int]:
    """
    Consume eventos tipados de Ollama y los renderiza usando Rich.
    Retorna (full_response_content, tool_calls, tokens, duration).
    """
    thinking_text = ""
    full_response_content = ""
    tool_calls: List[Dict[str, Any]] = []
    tokens = 0
    duration = 0
    spinner_stopped = False

    def _stop_spinner():
        nonlocal spinner_stopped
        if spinner is not None and not spinner_stopped:
            spinner.stop()
            spinner_stopped = True

    if stream:
        live: Optional[Live] = None
        try:
            for event in events:
                if event.kind == "thinking":
                    _stop_spinner()
                    thinking_text += event.text
                    renderable = _build_response_renderable(
                        thinking_text, full_response_content, is_thinking=True
                    )
                    if live is None:
                        live = Live(
                            renderable,
                            console=target_console,
                            refresh_per_second=12,
                            vertical_overflow="visible",
                        )
                        live.start()
                    else:
                        live.update(renderable)

                elif event.kind == "content":
                    _stop_spinner()
                    full_response_content += event.text
                    renderable = _build_response_renderable(
                        thinking_text, full_response_content, is_thinking=False
                    )
                    if live is None:
                        live = Live(
                            renderable,
                            console=target_console,
                            refresh_per_second=12,
                            vertical_overflow="visible",
                        )
                        live.start()
                    else:
                        live.update(renderable)

                elif event.kind == "tool_calls":
                    _stop_spinner()
                    tool_calls.extend(event.tool_calls)

                elif event.kind == "done":
                    _stop_spinner()
                    tokens = event.eval_count
                    duration = event.eval_duration

            if live is not None:
                live.update(
                    _build_response_renderable(
                        thinking_text, full_response_content, is_thinking=False
                    ),
                    refresh=True,
                )
        finally:
            if live is not None:
                live.stop()
            _stop_spinner()
    else:
        try:
            for event in events:
                if event.kind == "thinking":
                    thinking_text += event.text
                elif event.kind == "content":
                    full_response_content += event.text
                elif event.kind == "tool_calls":
                    tool_calls.extend(event.tool_calls)
                elif event.kind == "done":
                    tokens = event.eval_count
                    duration = event.eval_duration
        finally:
            _stop_spinner()

        if thinking_text or full_response_content:
            target_console.print(
                _build_response_renderable(
                    thinking_text, full_response_content, is_thinking=False
                )
            )

    return full_response_content, tool_calls, tokens, duration


def render_response(
    agent: str,
    req: urllib.request.Request,
    stream: bool,
    target_console: Console = console,
) -> Tuple[Optional[str], int, List[Dict[str, Any]]]:
    """
    Método para obtener y renderizar la respuesta del modelo en la terminal.
    """
    spinner = Halo(text=f"{C_INFO}Pensando...{C_RESET}", spinner="dots")
    print(f"\n{C_ASSISTANT}Model: {agent}{C_RESET}")
    spinner.start()

    try:
        events = stream_ollama_chat(req, stream=bool(stream))
        full_response_content, tool_calls, tokens, duration = render_event_stream(
            events,
            stream=bool(stream),
            spinner=spinner,
            target_console=target_console,
        )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionError) as e:
        spinner.stop()
        print(f"\n{C_ERROR}Error de conexión: {e}{C_RESET}")
        print(
            f"{C_WARNING}Asegúrate de que Ollama está corriendo con el comando: "
            f"{C_INFO}ollama serve{C_RESET}"
        )
        return None, 1, []
    except Exception as e:
        spinner.stop()
        print(f"\n{C_ERROR}Error al procesar o renderizar la respuesta: {e}{C_RESET}")
        return None, 1, []
    finally:
        spinner.stop()

    if tokens > 0:
        print(f"\n{C_SUCCESS}Tokens: {C_RESET}{tokens}")
    if duration > 0:
        print(f"{C_TOOL}Duracion: {C_RESET}{format_duration(duration)}")
    save_usage(agent, tokens, duration)
    return full_response_content, 0, tool_calls


def render_message(agent: str, content: str, target_console: Console = console):
    """
    Método para renderizar un mensaje en la terminal.
    """
    print(f"\n{C_SYSTEM}{agent}{C_RESET}")
    target_console.print(Markdown(content, code_theme=CatppuccinMochaPygmentsStyle))
    return 0


def render_conversation(
    uuid: str,
    limit: int = 20,
    data_service: Optional[DataService] = None,
    target_console: Console = console,
):
    """
    Método para renderizar una conversación con los últimos mensajes en la terminal.
    """
    try:
        ds = data_service if data_service is not None else DataService()
        messages = ds.show_messages(uuid, limit)
        if not messages:
            print(f"\n{C_WARNING}No hay mensajes en esta conversación.{C_RESET}")
            return

        for message in messages:
            role = message[1]
            content = message[2]
            raw_imgs = message[4] if len(message) > 4 else None
            raw_tools = message[5] if len(message) > 5 else None

            if role == "user":
                print(f"\n{C_USER}Usuario:{C_RESET}")
                if raw_imgs:
                    try:
                        raw_list = json.loads(raw_imgs) if isinstance(raw_imgs, str) else raw_imgs
                        if raw_list:
                            img_str = ", ".join(raw_list) if isinstance(raw_list, list) else str(raw_list)
                            print(f"{C_INFO}[Imagen adjunta: {img_str}]{C_RESET}")
                    except Exception:
                        pass
                if content:
                    render_static_message(content, target_console)
            elif role == "tool":
                print(f"\n{C_TOOL}Herramienta (Resultado):{C_RESET}")
                try:
                    tool_json = json.loads(content)
                    syntax = Syntax(
                        json.dumps(tool_json, indent=2, ensure_ascii=False),
                        lexer="json",
                        theme=CatppuccinMochaPygmentsStyle,
                        word_wrap=True,
                    )
                    target_console.print(syntax)
                except Exception:
                    render_static_message(content, target_console)
            else:
                print(f"\n{C_ASSISTANT}Asistente:{C_RESET}")
                if raw_tools:
                    try:
                        parsed_tools = json.loads(raw_tools) if isinstance(raw_tools, str) else raw_tools
                        if parsed_tools:
                            for tc in parsed_tools:
                                fn = tc.get("function", {})
                                fn_name = fn.get("name", "tool")
                                fn_args = fn.get("arguments", {})
                                print(
                                    f"{C_WARNING}[Llamada a {fn_name}: "
                                    f"{json.dumps(fn_args, ensure_ascii=False)}]{C_RESET}"
                                )
                    except Exception:
                        pass
                if content:
                    render_static_message(content, target_console)

    except Exception as e:
        print(f"\n{C_ERROR}Error al obtener los mensajes: {e}{C_RESET}")
        return


def render_static_message(content: str, target_console: Console = console):
    """
    Renderiza un mensaje estático usando Rich Markdown con el tema Catppuccin Mocha.
    """
    if not content:
        return
    target_console.print(Markdown(content, code_theme=CatppuccinMochaPygmentsStyle))
