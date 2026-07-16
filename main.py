import argparse
import json
import urllib.request
import sys
import os
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.syntax import Syntax
from halo import Halo
from colorama import init, Fore, Style

# Inicializar colorama
init(autoreset=True)

file_path = "config.json"

default_data = {
    "url": "http://localhost:11434",
    "model": "ollama",
    "stream": True,
    "models": {},
    "usage":{}
}

if not os.path.exists(file_path):
    with open(file_path, "w") as file:
        json.dump(default_data, file, indent=4)

def clear_active_line(text: str, width: int):
    if not text:
        return
    num_rows = (len(text) + width - 1) // width
    if num_rows > 1:
        sys.stdout.write(f"\033[{num_rows - 1}A")
    sys.stdout.write("\r\033[J")
    sys.stdout.flush()

def read_config():
    with open(file_path, "r") as file:
        return json.load(file)

def write_config(key: str, value):
    current_config = read_config()
    current_config[key] = value
    with open(file_path, "w") as file:
        json.dump(current_config, file, indent=4)

def get_config(key: str):
    current_config = read_config()
    return current_config.get(key)

def question(args):
    """
    Envía una consulta a Ollama y renderiza la respuesta como Markdown en tiempo real.
    """
    if not args.text or not args.text.strip():
        print(f"{Fore.RED}{Style.BRIGHT}Error: La pregunta no puede estar vacía.{Style.RESET_ALL}")
        return 1

    url_base = get_config("url")
    stream = get_config("stream")
    model = args.model if args.model else get_config("model")

    url = f"{url_base}/api/chat"

    data = {
        "model": str(model),
        "messages": [
            {"role": "user", "content": str(args.text)}
        ],
        "stream": stream
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        spinner = Halo(text=f'{Fore.CYAN}Pensando...{Style.RESET_ALL}', spinner='dots')
        print(f"{Fore.MAGENTA}{Style.BRIGHT}\nModel: {model}{Style.RESET_ALL}")
        console = Console(force_terminal=True)
        tokens = 0 # Initialize tokens count
        duration = 0 # Initialize duration in nanoseconds
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
                    code_language = "python"
                    
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
                        
                        # Extract tokens and duration from the final chunk if 'done' is true
                        if res.get("done"):
                            tokens = res.get("eval_count", 0)
                            duration = res.get("eval_duration", 0)
                            
                        content = res.get("message", {}).get("content", "")
                        if not content:
                            continue
                            
                        # Procesar el streaming de forma estrictamente línea por línea
                        if "\n" in content:
                            parts = content.split("\n")
                            
                            # 1. Procesar la parte completada de la línea activa actual
                            completed_line = current_line + parts[0]
                            if in_code_block:
                                clear_active_line("" + current_line, terminal_width)
                            else:
                                clear_active_line(current_line, terminal_width)
                            
                            # Imprimir línea completada
                            if "```" in completed_line:
                                in_code_block = not in_code_block
                                # Calculate the number of dashes based on terminal width
                                num_dashes = terminal_width - len(f'{Fore.CYAN} ───|{Style.BRIGHT}{code_language}|') - 1
                                if in_code_block:
                                    lang = completed_line.replace("```", "").strip()
                                    code_language = lang if lang else "sh"
                                    print(f'{Fore.CYAN} ───|{Style.BRIGHT}{code_language}|{"─" * num_dashes}')
                                else:
                                    print(f"{Fore.CYAN} ────────────────────────────────────────────────────────────────")
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
                            
                            # 3. La última parte se convierte en la nueva línea activa
                            current_line = parts[-1]
                            if current_line:
                                if in_code_block:
                                    sys.stdout.write(f"{current_line}")
                                else:
                                    sys.stdout.write(current_line)
                                sys.stdout.flush()
                        else:
                            # Limpiar la línea activa previa e imprimir el estado actualizado
                            if in_code_block:
                                clear_active_line("" + current_line, terminal_width)
                                current_line += content
                                sys.stdout.write(f"{current_line}")
                            else:
                                clear_active_line(current_line, terminal_width)
                                current_line += content
                                sys.stdout.write(current_line)
                            sys.stdout.flush()
                            
                    # Limpiar y vaciar cualquier texto remanente al final
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
                    # Si stream es False
                    response_body = response.read().decode("utf-8")
                    res = json.loads(response_body)
                    content = res.get("message", {}).get("content", "")
                    
                    # Extract tokens and duration for non-streaming response
                    tokens = res.get("eval_count", 0)
                    duration = res.get("eval_duration", 0)
                    console.print(Markdown(content))
        finally:
            spinner.stop()

        # Display tokens and duration if available
        if tokens > 0:
            print(f"{Fore.GREEN}{Style.BRIGHT}\nTokens: {Style.RESET_ALL}{tokens}")
        if duration > 0:
            print(f'{Fore.GREEN}{Style.BRIGHT}Duracion: {Style.RESET_ALL}{format_duration(duration)}') # Convert nanoseconds to seconds
        save_usage(model, tokens, duration)
        return 0
    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}Error de conexión: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Asegúrate de que Ollama está corriendo con el comando:{Style.RESET_ALL} {Fore.CYAN}ollama serve{Style.RESET_ALL}")
        return 1

def show_models(args):
    url_base = get_config("url")
    url = f"{url_base}/api/tags"
    req = urllib.request.Request(
        url,
        headers={"Content-Type": "application/json"}
    )

    spinner = Halo(text=f'{Fore.CYAN}Obteniendo modelos...{Style.RESET_ALL}', spinner='dots')
    try:
        spinner.start()
        with urllib.request.urlopen(req) as response:
            spinner.stop()
            response_body = response.read().decode("utf-8")
            data = json.loads(response_body)

            models = data.get("models", [])
            models_dict = {}
            if models:
                print(f"{Fore.GREEN}{Style.BRIGHT}\nModelos disponibles:{Style.RESET_ALL}")
                for model in models:
                    model_name = model.get('name')
                    print(f"{Fore.CYAN}  • {model_name}{Style.RESET_ALL}")
                    models_dict[model_name] = model_name
                # Escribimos a la configuración una sola vez, fuera del bucle
                write_config("models", models_dict)
            else:
                print(f"{Fore.YELLOW}{Style.BRIGHT}No se encontraron modelos.{Style.RESET_ALL}")
            
            print(f"{Fore.MAGENTA}{Style.BRIGHT}\nDefault:{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  • {get_config('model')}{Style.RESET_ALL}")
            return 0
    except json.JSONDecodeError:
        spinner.stop()
        print(f"{Fore.RED}{Style.BRIGHT}Error: La respuesta del servidor no es un JSON válido.{Style.RESET_ALL}")
        return 1
    except Exception as e:
        spinner.stop()
        print(f"{Fore.RED}{Style.BRIGHT}Error de conexión: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Asegúrate de que Ollama está corriendo con el comando:{Style.RESET_ALL} {Fore.CYAN}ollama serve{Style.RESET_ALL}")
        return 1

def change_models(args):
    if not args.model:
        print(f"{Fore.YELLOW}{Style.BRIGHT}Ingresa el nombre del modelo. Consulta con 'models' para ver los disponibles.{Style.RESET_ALL}")
        return 1

    models = get_config("models")
    if not models:
        print(f"{Fore.YELLOW}{Style.BRIGHT}No tienes modelos guardados en la configuración. Consulta con 'models' primero.{Style.RESET_ALL}")
        return 1

    if args.model not in models:
        show_models(args)
        print(f"{Fore.RED}{Style.BRIGHT}\nModelo '{args.model}' no encontrado, verifica el nombre.{Style.RESET_ALL}")
        return 1

    write_config("model", args.model)
    print(f"{Fore.GREEN}{Style.BRIGHT}\nModelo default cambiado exitosamente a: {get_config('model')}{Style.RESET_ALL}")
    return 0

def save_usage(model, tokens, duration):
    #guardar u actualizar estadisticas de uso
    usage = get_config("usage")
    if not usage:
        usage = {}
    if model not in usage:
        usage[model] = {}
    total_tokens = usage.get(model, {}).get("tokens", 0)
    total_duration = usage.get(model, {}).get("duration", 0)
    usage[model]["tokens"] = total_tokens + tokens
    usage[model]["duration"] = total_duration + duration
    write_config("usage", usage)

def show_usage(args):
    usage = get_config("usage")
    if not usage:
        print(f"{Fore.YELLOW}{Style.BRIGHT}No hay estadísticas de uso disponibles.")
        return
    if not args.model:
        for model, data in usage.items():
            print(f"{Fore.GREEN}{Style.BRIGHT}\n• {model}:")
            print(f"{Fore.CYAN}     Tokens totales: {Style.RESET_ALL}{data['tokens']}")
            print(f"{Fore.CYAN}     Tiempo de actividad: {Style.RESET_ALL}{format_duration(data['duration'])}")
        return

    if args.model not in usage:
        print(f"{Fore.YELLOW}{Style.BRIGHT}No hay estadísticas de uso para el modelo '{args.model}'.")
        return
    
    print(f"{Fore.GREEN}{Style.BRIGHT}\n• {args.model}:")
    print(f"{Fore.CYAN}     Tokens totales: {Style.RESET_ALL}{usage[args.model]['tokens']}")
    print(f"{Fore.CYAN}     Tiempo de actividad: {Style.RESET_ALL}{format_duration(usage[args.model]['duration'])}")
    print("\n")

def change_server(args):
    if not args.url:
        print(f"{Fore.YELLOW}{Style.BRIGHT}Ingresa la URL del servidor.{Style.RESET_ALL}")
        return 1

    write_config("url", args.url)
    print(f"{Fore.GREEN}{Style.BRIGHT}\nURL del servidor cambiada exitosamente a: {get_config('url')}{Style.RESET_ALL}")
    return 0


def format_duration(nanoseconds):
    if nanoseconds is None:
        return "N/A"

    seconds = nanoseconds / 1_000_000_000

    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:  # Less than an hour
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.0f}s"
    elif seconds < 86400:  # Less than a day
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        remaining_seconds = (seconds % 3600) % 60
        return f"{hours}h {remaining_minutes}m {remaining_seconds:.0f}s"
    else:  # Days or more
        days = int(seconds // 86400)
        remaining_hours = int((seconds % 86400) // 3600)
        remaining_minutes = int(((seconds % 86400) % 3600) // 60)
        remaining_seconds = ((seconds % 86400) % 3600) % 60
        return f"{days}d {remaining_hours}h {remaining_minutes}m {remaining_seconds:.0f}s"


def main():
    try:
        parser = argparse.ArgumentParser(description="Herramienta CLI para usar modelos de IA locales Ollama con salida formato MD")
        subparsers = parser.add_subparsers(title="Funciones", dest="comando", help="Subcomandos disponibles")

        parser_question = subparsers.add_parser("req", help="Realizar consulta a un modelo de IA local")
        parser_question.add_argument("-t", "--text", help="Agrega tu pregunta")
        parser_question.add_argument("-m", "--model", help="Nombre del modelo", nargs='?')
        parser_question.set_defaults(func=question)

        parser_show_models = subparsers.add_parser("models", help="Mostrar modelos disponibles")
        parser_show_models.set_defaults(func=show_models)

        parser_default_model = subparsers.add_parser("change_model", help="Cambiar el modelo por defecto")
        parser_default_model.add_argument("-m", "--model", help="Nombre del modelo")
        parser_default_model.set_defaults(func=change_models)

        parse_change_server = subparsers.add_parser("change_server", help="Cambiar la direccion del servidor")
        parse_change_server.add_argument("-u", "--url", help="Url del servidor")
        parse_change_server.set_defaults(func=change_server)

        parser_show_usage = subparsers.add_parser("metrics", help="Mostrar estadísticas de uso")
        parser_show_usage.add_argument("-m", "--model", help="Nombre del modelo")
        parser_show_usage.set_defaults(func=show_usage)

        args = parser.parse_args()

        if not hasattr(args, "func"):
            parser.print_help()
            sys.exit(1)

        sys.exit(args.func(args))
    except KeyboardInterrupt:
        print("\nSaliendo...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()