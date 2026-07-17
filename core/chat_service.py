from utils.helpers import get_config, write_config
from gui.render import render_response
import urllib.request
from colorama import init, Fore, Style
import json

init(autoreset=True)
# El historial del chat es un estado de la sesión, debe vivir aquí.
context = []

def send_chat_request(args, user_input=None):
    """Realiza una peticion '/api/chat' a la API de Ollama."""
    url_base = get_config("url")
    stream = get_config("stream")
    models = get_config("models")
    model = args.model if args.model else get_config("model")

    if models and model not in models:
        print(f"\n{Fore.RED}{Style.BRIGHT}Error: {Style.RESET_ALL}El modelo '{model}' no está disponible. Usa 'models' para ver los modelos disponibles.")
        return 1

    if user_input:
        content = user_input
    elif hasattr(args, 'text') and args.text:
        content = args.text
    else:
        return 1

    context.append({"role": "user", "content": content})

    url = f"{url_base}/api/chat"

    payload = {
        "model": str(model),
        "messages": context,
        "stream": stream
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    response_content, exit_code = render_response(str(model), req, bool(stream))
    if exit_code == 0 and response_content:
        context.append({"role": "assistant", "content": response_content})
    return exit_code
