from utils.helpers import get_config, write_config
from gui.render import render_response
import urllib.request
from colorama import init, Fore, Style
from persistent.db import DataService
import json

dataServices = DataService()

init(autoreset=True)
# El historial del chat es un estado de la sesión, debe vivir aquí.
context = []

def clear_context():
    """Limpia el historial del chat en memoria."""
    context.clear()

def send_chat_request(args, user_input=None):
    try:
        """Realiza una peticion '/api/chat' a la API de Ollama."""
        url_base = get_config("url")
        stream = get_config("stream")
        models = get_config("models")
        model = args.model if args.model else get_config("model")

        if models and model not in models:
            clear_context()
            print(f"\n{Fore.RED}{Style.BRIGHT}Error: {Style.RESET_ALL}El modelo '{model}' no está disponible. Usa 'models' para ver los modelos disponibles.")
            return 1
        
        # Determina el contenido del mensaje del usuario
        if user_input:
            content = user_input
        elif hasattr(args, 'text') and args.text:
            content = args.text
        else:
            clear_context()
            return 1 # No hay texto para enviar

        # Añade el mensaje del usuario al contexto y a la BD si aplica
        context.append({"role": "user", "content": content})
        if args.uuid:
            dataServices.insert_message({
                "conversation_uuid": args.uuid,
                "role": "user",
                "content": content
            })

        url = f"{url_base}/api/chat"

        sys_prompt = get_config("system_prompt")
        messages_payload = []
        if sys_prompt and str(sys_prompt).strip():
            messages_payload.append({"role": "system", "content": str(sys_prompt)})
        messages_payload.extend(context)

        options = dict(get_config("options") or {})
        if getattr(args, 'temperature', None) is not None:
            options['temperature'] = float(args.temperature)
        if getattr(args, 'num_ctx', None) is not None:
            options['num_ctx'] = int(args.num_ctx)
        if getattr(args, 'top_p', None) is not None:
            options['top_p'] = float(args.top_p)
        if getattr(args, 'top_k', None) is not None:
            options['top_k'] = int(args.top_k)

        payload = {
            "model": str(model),
            "messages": messages_payload,
            "stream": stream
        }
        if options:
            payload["options"] = options

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        response_content, exit_code = render_response(str(model), req, bool(stream))
        if exit_code == 0 and response_content:
            context.append({"role": "assistant", "content": response_content})
            if args.uuid:
                success = dataServices.insert_message({
                    "conversation_uuid": args.uuid,
                    "role": "assistant",
                    "content": response_content
                })
                if not success:
                    print(f"\n{Fore.YELLOW}{Style.BRIGHT}Advertencia:{Style.RESET_ALL} No se pudo guardar la respuesta del asistente en la base de datos.")
        
        return exit_code
    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}Error de conexión: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Asegúrate de que Ollama está corriendo con el comando:{Style.RESET_ALL} {Fore.CYAN}ollama serve{Style.RESET_ALL}")
        return 1
