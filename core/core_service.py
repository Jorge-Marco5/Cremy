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
# Import helpers and time formatter from utils to avoid circular imports
from utils.helpers import get_config, write_config
from utils.format_time import format_duration
from core.chat_service import send_chat_request

# Inicializar colorama
init(autoreset=True)


def instant_req(args):
    """
    Realizar una pregunta rapida a Ollama
    """
    if not args.text or not args.text.strip():
        print(f"{Fore.RED}{Style.BRIGHT}Error: La pregunta no puede estar vacía.{Style.RESET_ALL}")
        return 1

    # Para 'req', el contexto no se mantiene entre ejecuciones
    return send_chat_request(args)


def chat(args):
    """
    Iniciar una conversacion con un modelo de IA local usando Ollama
    """
    if not args.text or not args.text.strip():
        print(f"{Fore.RED}{Style.BRIGHT}Error: La pregunta no puede estar vacía.{Style.RESET_ALL}")
        return 1
    
    # Enviar el primer mensaje para iniciar el chat
    exit_code = send_chat_request(args)

    # Bucle para continuar el chat si la primera pregunta fue exitosa
    while exit_code == 0:
            req = input(f"\n{Fore.YELLOW}{Style.BRIGHT}Usuario: {Style.RESET_ALL}")
            if not req.strip():
                continue
            if req == "exit":
                break
            exit_code = send_chat_request(args, user_input=req)

    return 0

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
    # moved to utils/helpers.py; kept wrapper for backward compatibility
    from utils.helpers import save_usage as _save
    return _save(model, tokens, duration)

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