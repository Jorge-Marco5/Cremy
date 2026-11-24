import argparse
import json
import sys
import os
from core.core_service import (
    instant_req, chat, continue_chat, delete_chat, show_models,
    change_models, change_host, system_prompt, show_usage,
    show_options, set_option, reset_options, think_handler,
    show_tools, enable_tool, disable_tool, set_tool_confirmation,
    toggle_tools_handler, render_banner
)
from utils.helpers import file_path

try:
    from extensions import init_tools
    init_tools()
except ImportError:
    pass

default_data = {
    "url": "http://localhost:11434",
    "model": "ollama",
    "think": False,
    "stream": True,
    "options": {},
    "system_prompt": "Eres un asistente útil.",
    "models": {},
    "usage":{}
}

if not os.path.exists(file_path):
    with open(file_path, "w") as file:
        json.dump(default_data, file, indent=4)

def add_options_arguments(subparser):
    """Añade argumentos opcionales de inferencia a un subparser."""
    subparser.add_argument("--temperature", type=float, help="Temperatura de muestreo (ej. 0.2 determinista, 0.7 balanceado, 1.2 creativo)")
    subparser.add_argument("--num-ctx", dest="num_ctx", type=int, help="Tamaño de ventana de contexto en tokens (ej. 4096, 8192)")
    subparser.add_argument("--top-p", dest="top_p", type=float, help="Muestreo por núcleo top_p (ej. 0.9)")
    subparser.add_argument("--top-k", dest="top_k", type=int, help="Muestreo top_k (ej. 40)")

def main():
    try:
        parser = argparse.ArgumentParser(description="Herramienta CLI para usar modelos de IA locales Ollama con salida formato MD")
        subparsers = parser.add_subparsers(title="Funciones", dest="comando", help="Subcomandos disponibles")

        paper_question = subparsers.add_parser("banner", help="Muestra el paper de la aplicación")
        paper_question.set_defaults(func=render_banner)

        parser_question = subparsers.add_parser("req", help="Realizar consulta rapida a un modelo de IA local")
        #parser_question.add_argument("-t", "--text", help="Agrega tu pregunta envuelta en ' '")
        parser_question.add_argument("-m", "--model", help="Nombre del modelo", nargs='?')
        #parser_question.add_argument("-i", "--image", nargs="+", help="Ruta de una o más imágenes para modelos multimodales")
        add_options_arguments(parser_question)
        parser_question.set_defaults(func=instant_req)

        parser_init_chat = subparsers.add_parser("chat", help="Iniciar un nuevo chat")
        #parser_init_chat.add_argument("-t", "--text", help="Agrega tu pregunta envuelta en ' '")
        parser_init_chat.add_argument("-m", "--model", help="Nombre del modelo", nargs='?')
        #parser_init_chat.add_argument("-i", "--image", nargs="+", help="Ruta de una o más imágenes para modelos multimodales")
        add_options_arguments(parser_init_chat)
        parser_init_chat.set_defaults(func=chat)

        parser_continue_chat = subparsers.add_parser("resume", help="Busca y continua un chat anterior")
        parser_continue_chat.add_argument("-m", "--model", help="Nombre del modelo")
        parser_continue_chat.add_argument("-i", "--image", nargs="+", help="Ruta de una o más imágenes para adjuntar en este turno")
        add_options_arguments(parser_continue_chat)
        parser_continue_chat.set_defaults(func=continue_chat)

        parser_delete_chat = subparsers.add_parser("delete_chat", help="Eliminar la conversacion completa de un chat")
        parser_delete_chat.set_defaults(func=delete_chat)

        parser_show_models = subparsers.add_parser("models", help="Mostrar modelos disponibles")
        parser_show_models.set_defaults(func=show_models)

        parser_default_model = subparsers.add_parser("change_model", help="Cambiar el modelo por defecto")
        parser_default_model.add_argument("-m", "--model", help="Nombre del modelo")
        parser_default_model.set_defaults(func=change_models)

        parse_change_host = subparsers.add_parser("change_host", help="Cambiar la direccion del servidor")
        parse_change_host.add_argument("-u", "--url", help="Url del servidor")
        parse_change_host.set_defaults(func=change_host)

        parse_system_prompt = subparsers.add_parser("system_prompt", help="Definir un system prompt personalizado")
        parse_system_prompt.add_argument("-t", "--text", help="System prompt personalizado envuelto en ' '")
        parse_system_prompt.set_defaults(func=system_prompt)

        parser_show_usage = subparsers.add_parser("metrics", help="Mostrar estadísticas de uso")
        parser_show_usage.add_argument("-m", "--model", help="Nombre del modelo")
        parser_show_usage.set_defaults(func=show_usage)

        parser_options = subparsers.add_parser("options", help="Mostrar parámetros de opciones configurados y soportados")
        parser_options.set_defaults(func=show_options)

        parser_set_option = subparsers.add_parser("set_option", help="Configurar un parámetro de opción de Ollama")
        parser_set_option.add_argument("-k", "--key", required=True, help="Nombre del parámetro (ej. temperature, num_ctx, top_p)")
        parser_set_option.add_argument("-v", "--value", required=True, help="Valor del parámetro (ej. 0.7, 4096)")
        parser_set_option.set_defaults(func=set_option)

        parser_think = subparsers.add_parser("think", help="Activar o desactivar el modo razonamiento")
        parser_think.set_defaults(func=think_handler)

        parser_reset_options = subparsers.add_parser("reset_options", help="Restablecer opciones de Ollama a valores por defecto")
        parser_reset_options.set_defaults(func=reset_options)

        parser_tools = subparsers.add_parser("tools", help="Mostrar herramientas de IA disponibles y su estado")
        parser_tools.set_defaults(func=show_tools)

        parser_enable_tool = subparsers.add_parser("enable_tool", help="Activar una herramienta de IA")
        parser_enable_tool.add_argument("-t", "--tool", required=True, help="Nombre de la herramienta")
        parser_enable_tool.set_defaults(func=enable_tool)

        parser_disable_tool = subparsers.add_parser("disable_tool", help="Desactivar una herramienta de IA")
        parser_disable_tool.add_argument("-t", "--tool", required=True, help="Nombre de la herramienta")
        parser_disable_tool.set_defaults(func=disable_tool)

        parser_tool_confirm = subparsers.add_parser("tool_confirm", help="Configurar si una herramienta requiere confirmación previa")
        parser_tool_confirm.add_argument("-t", "--tool", required=True, help="Nombre de la herramienta")
        parser_tool_confirm.add_argument("-v", "--value", required=True, help="true para requerir confirmación, false para auto-ejecutar")
        parser_tool_confirm.set_defaults(func=set_tool_confirmation)

        parser_toggle_tools = subparsers.add_parser("toggle_tools", help="Activar o desactivar el uso de herramientas globalmente")
        parser_toggle_tools.set_defaults(func=toggle_tools_handler)

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