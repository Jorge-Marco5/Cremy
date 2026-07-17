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

# Inicializar colorama
init(autoreset=True)

def render_response(model: str, req: urllib.request.Request, stream: bool):
    """
    Metodo para renderizar la respuesta en la terminal
    """
    full_response_content = ""
    try:
        spinner = Halo(text=f'{Fore.CYAN}Pensando...{Style.RESET_ALL}', spinner='dots')
        print(f"{Fore.MAGENTA}{Style.BRIGHT}\nModel: {model}{Style.RESET_ALL}")
        console = Console(force_terminal=True)
        tokens = 0
        duration = 0
        spinner.start()
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
                            
                        content = res.get("message", {}).get("content", "")
                        if not content:
                            if res.get("done"):
                                full_response_content = current_line
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
                        full_response_content = current_line
                else:
                    
                    response_body = response.read().decode("utf-8")
                    res = json.loads(response_body)
                    content = res.get("message", {}).get("content", "")
                    
                    
                    tokens = res.get("eval_count", 0)
                    duration = res.get("eval_duration", 0)
                    full_response_content = content
                    console.print(Markdown(content))
        finally:
            spinner.stop()

        
        if tokens > 0:
            print(f"{Fore.GREEN}{Style.BRIGHT}\nTokens: {Style.RESET_ALL}{tokens}")
        if duration > 0:
            print(f'{Fore.GREEN}{Style.BRIGHT}Duracion: {Style.RESET_ALL}{format_duration(duration)}') 
        save_usage(model, tokens, duration)
        return full_response_content, 0
    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}Error de conexión: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Asegúrate de que Ollama está corriendo con el comando:{Style.RESET_ALL} {Fore.CYAN}ollama serve{Style.RESET_ALL}")
        return None, 1