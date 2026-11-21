from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.syntax import Syntax
import urllib.request
import json
import sys
import os
from halo import Halo
from colorama import init, Fore, Style
from utils.helpers import clear_active_line, save_usage
from utils.format_time import format_duration
from persistent.db import DataService

dataService = DataService()

# Inicializar colorama
init(autoreset=True)

def render_response(agent: str, req: urllib.request.Request, stream: bool):
    """
    Metodo para renderizar la respuesta del modelo en la terminal
    """
    full_response_content = ""
    tool_calls = []
    try:
        spinner = Halo(text=f'{Fore.CYAN}Pensando...{Style.RESET_ALL}', spinner='dots')
        print(f"{Fore.MAGENTA}{Style.BRIGHT}\nModel: {agent}{Style.RESET_ALL}")
        console = Console(force_terminal=True)
        tokens = 0
        duration = 0
        spinner.start()
        sys.stdout.write("")
        sys.stdout.flush()
        try:
            with urllib.request.urlopen(req) as response:
                spinner.stop()
                if stream:
                    try:
                        terminal_width = os.get_terminal_size().columns
                    except OSError:
                        terminal_width = console.width or 80
                        
                    current_line = ""
                    in_code_block = False
                    code_language = "sh"
                    
                    for raw_line in response:
                        if not raw_line:
                            continue
                        line_str = raw_line.decode("utf-8").strip()
                        if not line_str:
                            continue
                        try:
                            res = json.loads(line_str)
                        except json.JSONDecodeError:
                            continue
                        
                        if res.get("done"):
                            tokens = res.get("eval_count", 0)
                            duration = res.get("eval_duration", 0)
                            
                        msg_obj = res.get("message", {})
                        chunk_tools = msg_obj.get("tool_calls")
                        if chunk_tools:
                            tool_calls.extend(chunk_tools)

                        content = msg_obj.get("content", "")
                        if not content:
                            # No hay contenido en este fragmento, continuar
                            continue
                            
                        if "\n" in content:
                            parts = content.split("\n")
                            
                            completed_line = current_line + parts[0]
                            if in_code_block:
                                clear_active_line("" + current_line, terminal_width)
                            else:
                                clear_active_line(current_line, terminal_width)
                            
                            if "```" in completed_line:
                                in_code_block = not in_code_block
                                num_dashes = terminal_width - len(f'{Fore.CYAN}────┤{Style.BRIGHT}{code_language}├')
                                footer_dashes = terminal_width - len(f'{Fore.CYAN}───')
                                if in_code_block:
                                    lang = completed_line.replace("```", "").strip()
                                    code_language = lang if lang else "sh"
                                    print(f'{Fore.CYAN}────┤{Style.BRIGHT}{code_language}├{"─" * num_dashes}')
                                else:
                                    print(f'{Fore.CYAN}{"─" * footer_dashes}')
                            elif in_code_block:
                                sys.stdout.write("")
                                sys.stdout.flush()
                                try:
                                    syntax = Syntax(completed_line, lexer=code_language, theme="github-dark", word_wrap=True)
                                except Exception:
                                    syntax = Syntax(completed_line, lexer="text", theme="github-dark", word_wrap=True)
                                console.print(syntax)
                            else:
                                if completed_line.strip():
                                    console.print(Markdown(completed_line))
                                else:
                                    console.print()
                            
                            
                            current_line = parts[-1]
                            if current_line:
                                if in_code_block:
                                    sys.stdout.write(f"{current_line}")
                                else:
                                    sys.stdout.write(current_line)
                                sys.stdout.flush()
                        else:
                            
                            if in_code_block:
                                clear_active_line("" + current_line, terminal_width)
                                current_line += content
                                sys.stdout.write(f"{current_line}")
                            else:
                                clear_active_line(current_line, terminal_width)
                                current_line += content
                                sys.stdout.write(current_line)
                            sys.stdout.flush()
                        full_response_content += content
                    
                    if current_line:
                        if in_code_block:
                            clear_active_line("" + current_line, terminal_width)
                            sys.stdout.write("")
                            sys.stdout.flush()
                            try:
                                syntax = Syntax(current_line, lexer=code_language, theme="github-dark", word_wrap=True)
                            except Exception:
                                syntax = Syntax(current_line, lexer="text", theme="github-dark", word_wrap=True)
                            console.print(syntax)
                            console.print(" ────", style="dim cyan")
                        else:
                            clear_active_line(current_line, terminal_width)
                            console.print(Markdown(current_line, code_theme="github-dark"))
                else:
                    response_body = response.read().decode("utf-8")
                    res = json.loads(response_body)
                    msg_obj = res.get("message", {})
                    content = msg_obj.get("content", "")
                    tool_calls = msg_obj.get("tool_calls", [])
                    
                    tokens = res.get("eval_count", 0)
                    duration = res.get("eval_duration", 0)
                    full_response_content = content
                    if content:
                        console.print(Markdown(content))
        finally:
            spinner.stop()
        if tokens > 0:
            print(f"{Fore.GREEN}{Style.BRIGHT}\nTokens: {Style.RESET_ALL}{tokens}")
        if duration > 0:
            print(f'{Fore.GREEN}{Style.BRIGHT}Duracion: {Style.RESET_ALL}{format_duration(duration)}') 
        save_usage(agent, tokens, duration)
        return full_response_content, 0, tool_calls
    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}Error de conexión: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Asegúrate de que Ollama está corriendo con el comando:{Style.RESET_ALL} {Fore.CYAN}ollama serve{Style.RESET_ALL}")
        return None, 1, []

def render_message(agent: str, content: str):
    """
    Metodo para renderizar un mensaje en la terminal
    """
    console = Console(force_terminal=True)
    print(f"{Fore.RED}{Style.BRIGHT}\n{agent}{Style.RESET_ALL}")
    #text = str(content)
    console.print(Markdown(content))
    return 0

def render_conversation(uuid: str):
    """
    Metodo para renderizar una conversacion con los ultimos 20 mensajes en la terminal o los que indique el usuario con el uuid de la conversacion
    """
    try:
        messages = dataService.show_messages(uuid, 20)
        if not messages:
            print(f"{Fore.YELLOW}{Style.BRIGHT}No hay mensajes en esta conversacion.{Style.RESET_ALL}")
            return
        
        #Renderizar mensajes
        for message in messages:
            role = message[1]
            content = message[2]
            raw_imgs = message[4] if len(message) > 4 else None
            raw_tools = message[5] if len(message) > 5 else None

            console = Console(force_terminal=True)

            if role == "user":
                print(f"{Fore.YELLOW}{Style.BRIGHT}\nUsuario:{Style.RESET_ALL}")
                if raw_imgs:
                    try:
                        raw_list = json.loads(raw_imgs) if isinstance(raw_imgs, str) else raw_imgs
                        if raw_list:
                            img_str = ", ".join(raw_list) if isinstance(raw_list, list) else str(raw_list)
                            print(f"{Fore.CYAN}🖼️  [Imagen adjunta: {img_str}]{Style.RESET_ALL}")
                    except Exception:
                        pass
                if content:
                    render_static_message(content, console)
            elif role == "tool":
                print(f"{Fore.BLUE}{Style.BRIGHT}\nHerramienta (Resultado):{Style.RESET_ALL}")
                try:
                    tool_json = json.loads(content)
                    syntax = Syntax(json.dumps(tool_json, indent=2, ensure_ascii=False), lexer="json", theme="github-dark", word_wrap=True)
                    console.print(syntax)
                except Exception:
                    render_static_message(content, console)
            else:
                print(f"{Fore.MAGENTA}{Style.BRIGHT}\nAsistente:{Style.RESET_ALL}")
                if raw_tools:
                    try:
                        parsed_tools = json.loads(raw_tools) if isinstance(raw_tools, str) else raw_tools
                        if parsed_tools:
                            for tc in parsed_tools:
                                fn = tc.get("function", {})
                                fn_name = fn.get("name", "tool")
                                fn_args = fn.get("arguments", {})
                                print(f"{Fore.YELLOW}🛠️  [Llamada a {fn_name}: {json.dumps(fn_args, ensure_ascii=False)}]{Style.RESET_ALL}")
                    except Exception:
                        pass
                if content:
                    render_static_message(content, console)
        
    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}Error al obtener los mensajes: {e}{Style.RESET_ALL}")
        return
    
def render_static_message(content: str, console: Console):
    """
    Renderiza un mensaje de texto estático, aplicando formato de Markdown y bloques de código.
    """
    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        terminal_width = console.width or 80

    # Dividir el contenido por los delimitadores de bloque de código
    parts = content.split("```")

    for i, part in enumerate(parts):
        if not part:
            continue

        # Las partes impares (1, 3, 5...) están dentro de un bloque de código
        if i % 2 == 1:
            # El bloque de código tiene el lenguaje en la primera línea
            lines = part.split('\n', 1)
            language = lines[0].strip() or "sh"
            code = lines[1] if len(lines) > 1 else ""

            # Renderizar encabezado del bloque de código
            header_text = f'┤{language}├'
            num_dashes = terminal_width - len(header_text) - 4
            print(f'{Fore.CYAN}────{Style.BRIGHT}{header_text}{Style.NORMAL}{"─" * num_dashes}{Style.RESET_ALL}')

            # Renderizar el código con resaltado de sintaxis
            if code:
                try:
                    syntax = Syntax(code, lexer=language, theme="github-dark", word_wrap=True)
                except Exception:
                    syntax = Syntax(code, lexer="text", theme="github-dark", word_wrap=True)
                console.print(syntax)
            
            # Renderizar pie del bloque de código
            print(f'{Fore.CYAN}{"─" * terminal_width}{Style.RESET_ALL}')
        else:
            # Las partes pares (0, 2, 4...) son Markdown normal
            # Eliminar saltos de línea vacíos al principio o final para evitar espacios extra
            part_to_render = part.strip('\n')
            if part_to_render:
                console.print(Markdown(part_to_render, code_theme="github-dark"))