from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.syntax import Syntax
from rich.table import Table
import urllib.request
import urllib.error
import json
import sys
import os
from halo import Halo
from colorama import init, Fore, Style
import questionary
from prompt_toolkit.shortcuts import CompleteStyle
from utils.helpers import get_config, write_config, parse_option_value, parse_interactive_image_input, encode_image, format_bytes
from utils.format_time import format_duration
from core.chat_service import send_chat_request, clear_context, context
from gui.render import render_message
from persistent.db import DataService
from gui.render import render_conversation
from simple_term_menu import TerminalMenu
from core.command_service import command_service
from tools.registry import registry


init(autoreset=True)

dataservice = DataService()

from questionary import Style

custom_style = Style([
    ("question", "fg:#89b4fa bold"),
    ("answer", "fg:#a6e3a1 bold"),
    ("pointer", "fg:#cba6f7 bold"),
    ("highlighted", "fg:#f38ba8 bold"),
    ("completion-menu", "bg:#1e1e2e fg:#cdd6f4"),
    ("completion-menu.completion", "bg:#1e1e2e fg:#cdd6f4"),
    ("completion-menu.completion.current", "bg:#45475a fg:#f5c2e7 bold"),
])

def instant_req(args):
    """
    Realizar una pregunta rapida a Ollama, soportando comandos /command de herramientas y sesión.
    """
    if not getattr(args, "text", None):
        req = questionary.autocomplete("Usuario:", choices=command_service.list_all_commands, complete_while_typing=True, style=custom_style).ask()
        args.text = req
    else:
        req = args.text
    if not args.text or not args.text.strip():
        print(f"{Fore.RED}{Style.BRIGHT}Error: La pregunta no puede estar vacía.{Style.RESET_ALL}")
        return 1

    args.uuid = None

    stripped = req.strip()
    if not stripped:
        return 0

    # Soporte para comandos de imagen interactiva (/image o /img)
    if stripped.startswith(("/image", "/img")):
        prompt, attached_images = parse_interactive_image_input(req)
        if attached_images:
            return send_chat_request(args, user_input=prompt, images=attached_images)
        else:
            print(f"{Fore.YELLOW}Uso: {Fore.CYAN}/image <ruta_de_imagen> [pregunta opcional]{Style.RESET_ALL}")
            return 1

    if command_service.is_command(stripped):
        dispatch_res = command_service.dispatch(stripped, args)
        if dispatch_res.should_exit:
            return 0
        if dispatch_res.should_skip_model:
            return dispatch_res.exit_code
        if dispatch_res.enriched_prompt:
            prompt_to_send, attached_images = parse_interactive_image_input(dispatch_res.enriched_prompt)
            if attached_images:
                return send_chat_request(args, user_input=prompt_to_send, images=attached_images)
            else:
                return send_chat_request(args, user_input=dispatch_res.enriched_prompt)
        if dispatch_res.handled:
            return dispatch_res.exit_code

    # Entrada normal del usuario
    prompt, attached_images = parse_interactive_image_input(req)
    if attached_images:
        return send_chat_request(args, user_input=prompt, images=attached_images)
    else:
        return send_chat_request(args, user_input=req)


def handle_interactive_chat_turn(req: str, args):
    """
    Procesa un turno en el bucle interactivo de chat o continue_chat.
    Retorna (should_continue: bool, exit_code: int).
    """
    stripped = req.strip()
    if not stripped:
        return True, 0

    # Soporte para comandos de imagen interactiva (/image o /img)
    if stripped.startswith(("/image", "/img")):
        prompt, attached_images = parse_interactive_image_input(req)
        if attached_images:
            code = send_chat_request(args, user_input=prompt, images=attached_images)
            return True, code
        else:
            print(f"{Fore.YELLOW}Uso: {Fore.CYAN}/image <ruta_de_imagen> [pregunta opcional]{Style.RESET_ALL}")
            return True, 0

    if command_service.is_command(stripped):
        dispatch_res = command_service.dispatch(stripped, args)
        if dispatch_res.should_exit:
            return False, 0
        if dispatch_res.should_skip_model:
            return True, dispatch_res.exit_code
        if dispatch_res.enriched_prompt:
            prompt_to_send, attached_images = parse_interactive_image_input(dispatch_res.enriched_prompt)
            if attached_images:
                code = send_chat_request(args, user_input=prompt_to_send, images=attached_images)
            else:
                code = send_chat_request(args, user_input=dispatch_res.enriched_prompt)
            return True, code
        if dispatch_res.handled:
            return True, dispatch_res.exit_code

    # Entrada normal del usuario
    prompt, attached_images = parse_interactive_image_input(req)
    if attached_images:
        code = send_chat_request(args, user_input=prompt, images=attached_images)
    else:
        code = send_chat_request(args, user_input=req)
    return True, code


def chat(args):
    """
    Iniciar una conversacion con un modelo de IA local usando Ollama
    """
    if not getattr(args, "text", None):
        req = questionary.autocomplete("Usuario:", choices=command_service.list_all_commands, complete_while_typing=True).ask()
        args.text = req
    else:
        req = args.text
    if not args.text or not args.text.strip():
        print(f"{Fore.RED}{Style.BRIGHT}Error: La pregunta no puede estar vacía.{Style.RESET_ALL}")
        return 1

    if get_config('model') == 'ollama':
        print(f"{Fore.RED}{Style.BRIGHT}Error: No se ingreso un modelo valido, configura con el comando 'change_model'.{Style.RESET_ALL}")
        return 1

    # Limpiar el contexto en memoria para una nueva conversación
    clear_context()

    initial_input = args.text
    initial_prompt = initial_input

    # Evaluar si la entrada inicial es un comando slash
    if command_service.is_command(initial_input):
        dispatch_res = command_service.dispatch(initial_input, args)
        if dispatch_res.should_exit:
            return 0
        if dispatch_res.should_skip_model:
            initial_prompt = None
        elif dispatch_res.enriched_prompt:
            initial_prompt = dispatch_res.enriched_prompt

    if initial_prompt:
        name = " ".join(args.text.split()[:5])
        model_to_bind = args.model if getattr(args, 'model', None) else get_config("model")
        args.uuid = dataservice.create_conversation(name, model=model_to_bind)
        print(f'\nNew Chat - {args.uuid}')
        prompt, attached_images = parse_interactive_image_input(initial_prompt)
        if attached_images:
            exit_code = send_chat_request(args, user_input=prompt, images=attached_images)
        else:
            exit_code = send_chat_request(args, user_input=initial_prompt)
    else:
        name = "Nuevo Chat"
        model_to_bind = args.model if getattr(args, 'model', None) else get_config("model")
        args.uuid = dataservice.create_conversation(name, model=model_to_bind)
        print(f'\nNew Chat - {args.uuid}')
        exit_code = 0

    while exit_code == 0:
        req = questionary.autocomplete("Usuario:",choices=command_service.list_all_commands, complete_while_typing=True).ask()
        should_continue, exit_code = handle_interactive_chat_turn(req, args)
        if not should_continue:
            break

    return exit_code


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

    # Detectar el modelo asociado a la conversación
    conv_data = dataservice.show_one(str(uuid))
    bound_model = conv_data[3] if conv_data and len(conv_data) > 3 else None

    if not getattr(args, 'model', None):
        if bound_model:
            args.model = bound_model
            print(f"{Fore.CYAN}ℹ️  Modelo asociado al chat: {Fore.GREEN}{args.model}{Style.RESET_ALL}")
    else:
        if bound_model and args.model != bound_model:
            print(f"{Fore.YELLOW}ℹ️  Cambiando temporalmente el modelo a: {Fore.GREEN}{args.model}{Style.RESET_ALL} (original: {bound_model})")

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
            if len(message) > 5 and message[5]:
                try:
                    tools_list = json.loads(message[5]) if isinstance(message[5], str) else message[5]
                    if tools_list:
                        msg_obj["tool_calls"] = tools_list
                except Exception:
                    pass
            context.append(msg_obj)

    render_conversation(str(uuid))
    exit_code = 0

    while exit_code == 0:
        req = questionary.autocomplete("Usuario:",choices=command_service.list_all_commands, complete_while_typing=True).ask()
        should_continue, exit_code = handle_interactive_chat_turn(req, args)
        if not should_continue:
            break

    return exit_code

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
        model_tag = f" [{conversation[3]}]" if len(conversation) > 3 and conversation[3] else ""
        conversations_dict[f"{conversation[0]} - {conversation[1]}{model_tag}"] = conversation[0]

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

    spinner = Halo(text=f'{Fore.CYAN}Consultando modelos en {url_base}...{Style.RESET_ALL}', spinner='dots')
    try:
        spinner.start()
        with urllib.request.urlopen(req, timeout=5) as response:
            spinner.stop()
            response_body = response.read().decode("utf-8")
            data = json.loads(response_body)

            models = data.get("models", [])
            models_dict = {}

            if not models:
                print(f"{Fore.YELLOW}{Style.BRIGHT}\nNo se encontraron modelos instalados en tu servidor Ollama.{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Puedes descargar un modelo ejecutando por ejemplo:")
                print(f"  ollama run qwen3.5:2b{Style.RESET_ALL} (visión y razonamiento)")
                print(f"  {Fore.CYAN}ollama run llama3.2:1b{Style.RESET_ALL} (ligero y rápido)")
                return 0

            current_default = get_config("model")
            console = Console(force_terminal=True)

            table = Table(
                title=f"[bold magenta]Modelos de IA Disponibles en Ollama[/bold magenta]\n[dim]{url_base}[/dim]",
                header_style="bold cyan",
                border_style="dim blue",
                show_lines=False
            )
            table.add_column("Modelo", style="bold", min_width=22)
            table.add_column("Parámetros", justify="center")
            table.add_column("Cuantización", justify="center")
            table.add_column("Tamaño", justify="right")
            table.add_column("Contexto", justify="center")
            table.add_column("Capacidades Detectadas", justify="left")

            for m in models:
                model_name = m.get("name") or m.get("model", "desconocido")
                size_bytes = m.get("size", 0)
                size_str = format_bytes(size_bytes)
                details = m.get("details") or {}
                param_size = details.get("parameter_size", "N/A")
                quant = details.get("quantization_level", "N/A")
                ctx_len = details.get("context_length")

                if ctx_len:
                    ctx_str = f"{int(ctx_len // 1024)}k" if ctx_len >= 1024 else str(ctx_len)
                else:
                    ctx_str = "N/A"

                raw_caps = list(m.get("capabilities", []))
                families = [f.lower() for f in details.get("families", [])]
                family = str(details.get("family", "")).lower()
                name_lower = model_name.lower()

                # Inferir capacidades si no vienen explícitas
                if not raw_caps:
                    if any(vf in families or vf == family for vf in ["clip", "mllama", "vision", "qwen35"]) or any(vn in name_lower for vn in ["vision", "llava", "minicpm-v", "moondream", "vl"]):
                        raw_caps.append("vision")
                    if any(rn in name_lower for rn in ["r1", "thinking", "reason", "qwq"]):
                        raw_caps.append("thinking")
                    if "coder" in name_lower or "code" in name_lower:
                        raw_caps.append("code")
                    if not raw_caps:
                        raw_caps.append("completion")

                badges = []
                if "vision" in raw_caps or any(vn in name_lower for vn in ["vision", "minicpm-v", "llava"]):
                    badges.append("[bold cyan]Visión[/bold cyan]")
                if "thinking" in raw_caps or any(rn in name_lower for rn in ["thinking", "r1"]):
                    badges.append("[bold magenta]Razonamiento[/bold magenta]")
                if "tools" in raw_caps:
                    badges.append("[bold yellow]Tools[/bold yellow]")
                if "code" in raw_caps or "coder" in name_lower:
                    badges.append("[bold blue]Código[/bold blue]")
                if "completion" in raw_caps:
                    badges.append("[dim]Texto[/dim]")

                cap_display = " ".join(badges) if badges else "[dim]General[/dim]"

                is_default = (model_name == current_default)
                if is_default:
                    name_display = f"[bold green]{model_name}[/bold green] [bold yellow]★ (Default)[/bold yellow]"
                else:
                    name_display = f"[white]{model_name}[/white]"

                table.add_row(name_display, param_size, quant, size_str, ctx_str, cap_display)

                models_dict[model_name] = {
                    "name": model_name,
                    "capabilities": raw_caps,
                    "parameter_size": param_size,
                    "quantization": quant,
                    "size": size_bytes,
                    "context_length": ctx_len
                }

            write_config("models", models_dict)
            print()
            console.print(table)
            print(f"\n{Fore.MAGENTA}{Style.BRIGHT}Modelo activo por defecto:{Style.RESET_ALL} {Fore.GREEN}{current_default}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Tip: Cambia el modelo por defecto con: {Fore.CYAN}python main.py change_model -m <nombre>{Style.RESET_ALL}")
            return 0

    except urllib.error.HTTPError as e:
        spinner.stop()
        print(f"{Fore.RED}{Style.BRIGHT}\nError HTTP del servidor ({e.code}): {e.reason}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Verifica que la URL del servidor Ollama sea correcta: {Fore.CYAN}{url_base}{Style.RESET_ALL}")
        return 1
    except urllib.error.URLError as e:
        spinner.stop()
        print(f"{Fore.RED}{Style.BRIGHT}\nError de conexión con Ollama: {e.reason}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}No se pudo contactar al servidor en: {Fore.CYAN}{url_base}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Verifica que el servicio esté corriendo con: {Fore.CYAN}ollama serve{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}O cambia la URL configurada con: {Fore.CYAN}python main.py change_server -u <url>{Style.RESET_ALL}")
        return 1
    except TimeoutError:
        spinner.stop()
        print(f"{Fore.RED}{Style.BRIGHT}\nTiempo de espera agotado al conectar con Ollama en {url_base}.{Style.RESET_ALL}")
        return 1
    except json.JSONDecodeError:
        spinner.stop()
        print(f"{Fore.RED}{Style.BRIGHT}\nError: La respuesta del servidor no es un JSON válido.{Style.RESET_ALL}")
        return 1
    except Exception as e:
        spinner.stop()
        print(f"{Fore.RED}{Style.BRIGHT}\nError inesperado: {e}{Style.RESET_ALL}")
        return 1

def change_models(args):
    if not args.model:
        print(f"\nModelo actual: {get_config("model")}\n")
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

def change_host(args):
    try:
        if not args.url:
            print(f"\nHost actual: {get_config("url")}\n")
            print(f"{Fore.YELLOW}{Style.BRIGHT}Ingresa la URL del host.{Style.RESET_ALL}")
            return 1

        write_config("url", args.url)
        print(f"{Fore.GREEN}{Style.BRIGHT}\nURL del host cambiada exitosamente a: {get_config('url')}{Style.RESET_ALL}")
        return 0
    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}Error al cambiar la URL del host: {e}{Style.RESET_ALL}")

def system_prompt(args):
    try:
        if not args.text:
            print(f"\nSystem prompt actual: {get_config("system_prompt")}\n")
            print(f"{Fore.YELLOW}{Style.BRIGHT}No se ingreso un nuevo system prompt.{Style.RESET_ALL}")
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

def think_handler(args):
    think_enabled = get_config("think")
    if think_enabled:
        write_config("think", False)
        print(f"{Fore.GREEN}{Style.BRIGHT}\nModo razonamiento desactivado exitosamente.{Style.RESET_ALL}")
    else:
        write_config("think", True)
        print(f"{Fore.GREEN}{Style.BRIGHT}\nModo razonamiento activado exitosamente.{Style.RESET_ALL}")
    return 0

def show_tools(args):
    """Muestra una tabla con las herramientas disponibles, estado y confirmación."""
    from tools.registry import registry
    from utils.helpers import get_tools_config

    cfg = get_tools_config()
    global_enabled = cfg.get("enabled", True)
    tools_settings = cfg.get("tools", {})
    all_tools = registry.list_tools()

    console = Console(force_terminal=True)
    status_badge = "[bold green]ACTIVADO[/bold green]" if global_enabled else "[bold red]DESACTIVADO[/bold red]"
    
    table = Table(
        title=f"[bold magenta]Herramientas de IA (Tools / Function Calling)[/bold magenta]\nEstado global: {status_badge}",
        header_style="bold cyan",
        border_style="dim blue",
        show_lines=False
    )
    table.add_column("Herramienta", style="bold", min_width=20)
    table.add_column("Estado", justify="center")
    table.add_column("Confirmación", justify="center")
    table.add_column("Descripción", justify="left")

    for tool in all_tools:
        tool_cfg = tools_settings.get(tool.name, {})
        is_enabled = tool_cfg.get("enabled", tool.enabled_by_default)
        needs_confirm = tool_cfg.get("require_confirmation", tool.require_confirmation)

        enabled_str = "[bold green]🟢 Activada[/bold green]" if is_enabled else "[bold red]🔴 Desactivada[/bold red]"
        confirm_str = "[yellow]🔒 Requerida[/yellow]" if needs_confirm else "[dim green]⚡ Automática[/dim green]"

        table.add_row(
            f"[bold cyan]{tool.name}[/bold cyan]",
            enabled_str,
            confirm_str,
            tool.description
        )

    console.print(table)
    print(f"\n{Fore.YELLOW}Tip:{Style.RESET_ALL}")
    print(f"  • Activar/desactivar: {Fore.CYAN}python main.py enable_tool -t <nombre>{Style.RESET_ALL} / {Fore.CYAN}disable_tool -t <nombre>{Style.RESET_ALL}")
    print(f"  • Cambiar confirmación: {Fore.CYAN}python main.py tool_confirm -t <nombre> -v <true/false>{Style.RESET_ALL}")
    print(f"  • Conmutar globalmente: {Fore.CYAN}python main.py toggle_tools{Style.RESET_ALL}")
    return 0

def enable_tool(args):
    """Activa una herramienta específica."""
    from tools.registry import registry
    from utils.helpers import update_tool_setting

    tool_name = args.tool.strip()
    if not registry.get_tool(tool_name):
        print(f"{Fore.RED}{Style.BRIGHT}Error:{Style.RESET_ALL} La herramienta '{tool_name}' no existe en el catálogo.")
        return 1

    update_tool_setting(tool_name, enabled=True)
    print(f"{Fore.GREEN}{Style.BRIGHT}\nHerramienta '{tool_name}' activada exitosamente.{Style.RESET_ALL}")
    return 0

def disable_tool(args):
    """Desactiva una herramienta específica."""
    from tools.registry import registry
    from utils.helpers import update_tool_setting

    tool_name = args.tool.strip()
    if not registry.get_tool(tool_name):
        print(f"{Fore.RED}{Style.BRIGHT}Error:{Style.RESET_ALL} La herramienta '{tool_name}' no existe en el catálogo.")
        return 1

    update_tool_setting(tool_name, enabled=False)
    print(f"{Fore.YELLOW}{Style.BRIGHT}\nHerramienta '{tool_name}' desactivada exitosamente.{Style.RESET_ALL}")
    return 0

def set_tool_confirmation(args):
    """Configura si una herramienta requiere confirmación previa."""
    from tools.registry import registry
    from utils.helpers import update_tool_setting, parse_option_value

    tool_name = args.tool.strip()
    if not registry.get_tool(tool_name):
        print(f"{Fore.RED}{Style.BRIGHT}Error:{Style.RESET_ALL} La herramienta '{tool_name}' no existe en el catálogo.")
        return 1

    parsed_val = parse_option_value(args.value)
    if not isinstance(parsed_val, bool):
        print(f"{Fore.RED}{Style.BRIGHT}Error:{Style.RESET_ALL} El valor debe ser 'true' o 'false'.")
        return 1

    update_tool_setting(tool_name, require_confirmation=parsed_val)
    mode_str = "requerirá confirmación del usuario" if parsed_val else "se ejecutará automáticamente sin confirmación"
    print(f"{Fore.GREEN}{Style.BRIGHT}\nConfiguración actualizada:{Style.RESET_ALL} La herramienta '{tool_name}' {mode_str}.")
    return 0

def toggle_tools_handler(args):
    """Conmuta el uso de herramientas a nivel global."""
    from utils.helpers import toggle_tools_global

    new_state = toggle_tools_global()
    if new_state:
        print(f"{Fore.GREEN}{Style.BRIGHT}\nSistema de herramientas activado globalmente.{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}{Style.BRIGHT}\nSistema de herramientas desactivado globalmente.{Style.RESET_ALL}")
    return 0
