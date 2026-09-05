import argparse
import json
import sys
import os
from core.core_service import instant_req, chat, continue_chat, delete_chat, show_models, change_models, change_server, system_prompt, show_usage
from utils.helpers import file_path

default_data = {
    "url": "http://localhost:11434",
    "model": "ollama",
    "stream": True,
    "system_prompt": "Eres un asistente útil.",
    "models": {},
    "usage":{}
}

if not os.path.exists(file_path):
    with open(file_path, "w") as file:
        json.dump(default_data, file, indent=4)

def main():
    try:
        parser = argparse.ArgumentParser(description="Herramienta CLI para usar modelos de IA locales Ollama con salida formato MD")
        subparsers = parser.add_subparsers(title="Funciones", dest="comando", help="Subcomandos disponibles")

        parser_question = subparsers.add_parser("req", help="Realizar consulta rapida a un modelo de IA local")
        parser_question.add_argument("-t", "--text", help="Agrega tu pregunta envuelta en ' '")
        parser_question.add_argument("-m", "--model", help="Nombre del modelo", nargs='?')
        parser_question.set_defaults(func=instant_req)

        parser_init_chat = subparsers.add_parser("chat", help="Iniciar un chat con un modelo de IA local")
        parser_init_chat.add_argument("-t", "--text", help="Agrega tu pregunta envuelta en ' '")
        parser_init_chat.add_argument("-m", "--model", help="Nombre del modelo", nargs='?')
        parser_init_chat.set_defaults(func=chat)

        parser_continue_chat = subparsers.add_parser("continue_chat", help="Continuar un chat con un modelo de IA local")
        parser_continue_chat.add_argument("-m", "--model", help="Nombre del modelo")
        parser_continue_chat.set_defaults(func=continue_chat)

        parser_delete_chat = subparsers.add_parser("delete_chat", help="Eliminar la conversacion completa de un chat")
        parser_delete_chat.set_defaults(func=delete_chat)

        parser_show_models = subparsers.add_parser("models", help="Mostrar modelos disponibles")
        parser_show_models.set_defaults(func=show_models)

        parser_default_model = subparsers.add_parser("change_model", help="Cambiar el modelo por defecto")
        parser_default_model.add_argument("-m", "--model", help="Nombre del modelo")
        parser_default_model.set_defaults(func=change_models)

        parse_change_server = subparsers.add_parser("change_server", help="Cambiar la direccion del servidor")
        parse_change_server.add_argument("-u", "--url", help="Url del servidor")
        parse_change_server.set_defaults(func=change_server)

        parse_system_prompt = subparsers.add_parser("system_prompt", help="Definir un system prompt personalizado")
        parse_system_prompt.add_argument("-t", "--text", help="System prompt personalizado envuelto en ' '")
        parse_system_prompt.set_defaults(func=system_prompt)

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