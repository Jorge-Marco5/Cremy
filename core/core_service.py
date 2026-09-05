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
from utils.helpers import get_config, write_config, parse_option_value, parse_interactive_image_input, encode_image
from utils.format_time import format_duration
from core.chat_service import send_chat_request, clear_context, context
from gui.render import render_message
from persistent.db import DataService
from gui.render import render_conversation
# pyrefly: ignore [missing-import]
from simple_term_menu import TerminalMenu


init(autoreset=True)

dataservice = DataService()


def instant_req(args):
    """
    Realizar una pregunta rapida a Ollama
    """
    if not args.text or not args.text.strip():
        print(f"{Fore.RED}{Style.BRIGHT}Error: La pregunta no puede estar vacía.{Style.RESET_ALL}")
        return 1

    args.uuid = None

    return send_chat_request(args)


def chat(args):
    """
    Iniciar una conversacion con un modelo de IA local usando Ollama
    """
    if not args.text or not args.text.strip():
        print(f"{Fore.RED}{Style.BRIGHT}Error: La pregunta no puede estar vacía.{Style.RESET_ALL}")
        return 1

    # Limpiar el contexto en memoria para una nueva conversación
    clear_context()

    #obtener las 5 primeras palabras del prompt
    name = " ".join(args.text.split()[:5])
    args.uuid = dataservice.create_conversation(name)

    exit_code = send_chat_request(args)

    while exit_code == 0:
        req = input(f"\n{Fore.YELLOW}{Style.BRIGHT}Usuario: {Style.RESET_ALL}")
        if not req.strip():
            continue
        if req == 'exit':
            render_message("System", "**Saliendo...**")
            break
        prompt, attached_images = parse_interactive_image_input(req)
        if attached_images:
            exit_code = send_chat_request(args, user_input=prompt, images=attached_images)
        else:
            exit_code = send_chat_request(args, user_input=req)
    return 0

def continue_chat(args):
    """
    Iniciar una conversacion con un modelo de IA local usando Ollama
    """
    uuid = select_conversation()
    if not uuid or uuid == 1:
        print(f"{Fore.RED}{Style.BRIGHT}Error: No se seleccionó una conversación válida.{Style.RESET_ALL}")
        return 0
    
    # Asignar el UUID a los argumentos para que send_chat_request lo use
    args.uuid = uuid

    # Limpiar contexto y cargar el historial de la conversación seleccionada
    clear_context()
    messages = dataservice.show_messages(str(uuid))
    if messages:
        for message in messages:
            msg_obj = {"role": message[1], "content": message[2]}
            if len(message) > 4 and message[4]:
                try:
                    img_list = json.loads(message[4]) if isinstance(message[4], str) else message[4]
                    if img_list:
                        b64_list = []
                        for p in img_list:
                            try:
                                b64_list.append(encode_image(p))
                            except Exception:
                                pass
                        if b64_list:
                            msg_obj["images"] = b64_list
                except Exception:
                    pass
            context.append(msg_obj)

    render_conversation(str(uuid))
    exit_code = 0

    while exit_code == 0:
        req = input(f"\n{Fore.YELLOW}{Style.BRIGHT}Usuario: {Style.RESET_ALL}")
        if not req.strip():
            continue
        if req == "exit":
            render_message("System", "**Saliendo...**")
            break
        prompt, attached_images = parse_interactive_image_input(req)
        if attached_images:
            exit_code = send_chat_request(args, user_input=prompt, images=attached_images)
        else:
            exit_code = send_chat_request(args, user_input=req) # args ya tiene el uuid

    return 0

def delete_chat(args):
    """
    Iniciar una conversacion con un modelo de IA local usando Ollama
    """
    uuid = select_conversation()
    if not uuid or uuid == 1:
        print(f"{Fore.RED}{Style.BRIGHT}Error: No se seleccionó una conversación válida.{Style.RESET_ALL}")
        return 0
    
    delete = dataservice.delete(uuid)
    if delete:
        print(f"{Fore.GREEN}{Style.BRIGHT}Conversación eliminada exitosamente.{Style.RESET_ALL}") 
    return 0

def select_conversation():
    """
    Seleccionar una conversacion guardada en la base de datos y retornar UUID
    """
    conversations = dataservice.show_all()
    #diccionario de conversaciones
    conversations_dict = {}
    if not conversations:
        print(f"{Fore.YELLOW}{Style.BRIGHT}No hay conversaciones guardadas.{Style.RESET_ALL}")
        return 1
    for conversation in conversations:
        conversations_dict[conversation[0] + " - " + conversation[1]] = conversation[0]

    if not conversations_dict:
        print(f"{Fore.YELLOW}{Style.BRIGHT}No hay conversaciones guardadas.{Style.RESET_ALL}")
        return 1
    
    textos_menu = list(conversations_dict.keys())
    terminal_menu = TerminalMenu(textos_menu, title="Seleccione una conversación")
    menu_entry_index = terminal_menu.show()

    if menu_entry_index is None:
        print("Operación cancelada.")
        return 1

    if isinstance(menu_entry_index, (tuple, list)):
        sel_index = menu_entry_index[0] if menu_entry_index else None
    else:
        sel_index = menu_entry_index

    if sel_index is None:
        print("Operación cancelada.")
        return 1

    try:
        sel_index = int(sel_index)
    except (TypeError, ValueError):
        print(f"Índice de selección inválido: {sel_index}")
        return 1

    uuid = conversations_dict[textos_menu[sel_index]]
    return uuid


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
    from utils.helpers import save_usage as _save
    return _save(model, tokens, duration)

def show_usage(args):
    spinner = Halo(text=f'{Fore.CYAN}Obteniendo modelos...{Style.RESET_ALL}', spinner='dots')
    spinner.start()
    usage = get_config("usage")
    if not usage:
        spinner.stop()
        print(f"{Fore.YELLOW}{Style.BRIGHT}No hay estadísticas de uso disponibles.")
        return
    if not args.model:
        spinner.stop()
        usage = dict(sorted(usage.items(), key=lambda item: item[1]['tokens'], reverse=True))
        for model, data in usage.items():
            print(f"{Fore.GREEN}{Style.BRIGHT}\n• {model}:")
            print(f"{Fore.CYAN}     Tokens totales: {Style.RESET_ALL}{data['tokens']}")
            print(f"{Fore.CYAN}     Tiempo de actividad: {Style.RESET_ALL}{format_duration(data['duration'])}")
        return

    if args.model not in usage:
        spinner.stop()
        print(f"{Fore.YELLOW}{Style.BRIGHT}No hay estadísticas de uso para el modelo '{args.model}'.")
        return
    spinner.stop()
    print(f"{Fore.GREEN}{Style.BRIGHT}\n• {args.model}:")
    print(f"{Fore.CYAN}     Tokens totales: {Style.RESET_ALL}{usage[args.model]['tokens']}")
    print(f"{Fore.CYAN}     Tiempo de actividad: {Style.RESET_ALL}{format_duration(usage[args.model]['duration'])}")
    print("\n")

def change_server(args):
    try:
        if not args.url:
            print(f"{Fore.YELLOW}{Style.BRIGHT}Ingresa la URL del servidor.{Style.RESET_ALL}")
            return 1

        write_config("url", args.url)
        print(f"{Fore.GREEN}{Style.BRIGHT}\nURL del servidor cambiada exitosamente a: {get_config('url')}{Style.RESET_ALL}")
        return 0
    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}Error al cambiar la URL del servidor: {e}{Style.RESET_ALL}")

def system_prompt(args):
    try:
        if not args.text:
            print(f"{Fore.YELLOW}{Style.BRIGHT}Ingresa el system prompt.{Style.RESET_ALL}")
            return 1
        write_config("system_prompt", args.text)
        print(f"{Fore.GREEN}{Style.BRIGHT}\nSystem prompt cambiado exitosamente.{Style.RESET_ALL}")
        return 0
    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}Error al cambiar el system prompt: {e}{Style.RESET_ALL}")
        return 1

def show_options(args):
    options = get_config("options") or {}
    print(f"{Fore.MAGENTA}{Style.BRIGHT}\nParámetros de opciones configurados:{Style.RESET_ALL}")
    if not options:
        print(f"{Fore.YELLOW}  (Ninguna opción personalizada configurada. Se usan los valores por defecto del modelo en Ollama){Style.RESET_ALL}")
    else:
        for key, val in options.items():
            print(f"{Fore.CYAN}  • {key}: {Fore.GREEN}{val} {Fore.WHITE}({type(val).__name__}){Style.RESET_ALL}")

    print(f"{Fore.MAGENTA}{Style.BRIGHT}\nOpciones comunes soportadas por Ollama:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • {Fore.CYAN}temperature{Style.RESET_ALL} (float): Creatividad / aleatoriedad (ej. 0.2 factual, 0.7 balanceado, 1.2 creativo)")
    print(f"{Fore.WHITE}  • {Fore.CYAN}num_ctx{Style.RESET_ALL} (int): Tamaño de ventana de contexto en tokens (ej. 2048, 4096, 8192, 32768)")
    print(f"{Fore.WHITE}  • {Fore.CYAN}top_p{Style.RESET_ALL} (float): Muestreo por núcleo (ej. 0.9)")
    print(f"{Fore.WHITE}  • {Fore.CYAN}top_k{Style.RESET_ALL} (int): Limita a los K tokens más probables (ej. 40)")
    print(f"{Fore.WHITE}  • {Fore.CYAN}num_predict{Style.RESET_ALL} (int): Máximo de tokens a generar (-1 para ilimitado)")
    print(f"{Fore.WHITE}  • {Fore.CYAN}repeat_penalty{Style.RESET_ALL} (float): Penalización por repetición (ej. 1.1)")
    print(f"{Fore.WHITE}  • {Fore.CYAN}seed{Style.RESET_ALL} (int): Semilla para reproducibilidad de respuestas")
    print(f"\n{Fore.YELLOW}Tip: Modifica una opción con {Fore.CYAN}python main.py set_option -k <clave> -v <valor>{Style.RESET_ALL}")
    return 0

def set_option(args):
    if not args.key or args.value is None:
        print(f"{Fore.YELLOW}{Style.BRIGHT}Uso requerido: set_option -k <clave> -v <valor>{Style.RESET_ALL}")
        return 1

    options = get_config("options") or {}
    parsed_value = parse_option_value(args.value)
    options[args.key] = parsed_value
    write_config("options", options)
    print(f"{Fore.GREEN}{Style.BRIGHT}\nOpción configurada exitosamente:{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  • {args.key}: {Fore.GREEN}{parsed_value} {Fore.WHITE}({type(parsed_value).__name__}){Style.RESET_ALL}")
    return 0

def reset_options(args):
    write_config("options", {})
    print(f"{Fore.GREEN}{Style.BRIGHT}\nOpciones restablecidas exitosamente. Ahora se usan los valores por defecto de Ollama.{Style.RESET_ALL}")
    return 0