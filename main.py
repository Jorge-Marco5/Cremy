import argparse
import json
import sys
import os
from core.core_service import (
    instant_req, chat, continue_chat, delete_chat, show_models,
    change_models, change_host, system_prompt, show_usage,
    show_options, set_option, reset_options, think_handler
)
from utils.helpers import file_path

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

        parser_question = subparsers.add_parser("req", help="Realizar consulta rapida a un modelo de IA local")
        parser_question.add_argument("-t", "--text", help="Agrega tu pregunta envuelta en ' '")
        parser_question.add_argument("-m", "--model", help="Nombre del modelo", nargs='?')
        parser_question.add_argument("-i", "--image", nargs="+", help="Ruta de una o más imágenes para modelos multimodales")
        add_options_arguments(parser_question)
        parser_question.set_defaults(func=instant_req)

        parser_init_chat = subparsers.add_parser("chat", help="Iniciar un nuevo chat")
        parser_init_chat.add_argument("-t", "--text", help="Agrega tu pregunta envuelta en ' '")
        parser_init_chat.add_argument("-m", "--model", help="Nombre del modelo", nargs='?')
        parser_init_chat.add_argument("-i", "--image", nargs="+", help="Ruta de una o más imágenes para modelos multimodales")
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