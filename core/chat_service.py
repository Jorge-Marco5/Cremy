from utils.helpers import get_config, write_config
from gui.render import render_response
import urllib.request
import json

# El historial del chat es un estado de la sesión, debe vivir aquí.
context = []

def send_chat_request(args, user_input=None):
    """Realiza una peticion '/api/chat' a la API de Ollama."""
    url_base = get_config("url")
    stream = get_config("stream")
    model = args.model if args.model else get_config("model")

    # Determina el contenido del mensaje
    if user_input:
        content = user_input
    elif hasattr(args, 'text') and args.text:
        content = args.text
    else:
        return 1 # No hay texto para enviar

    # Añade el mensaje del usuario al contexto
    context.append({"role": "user", "content": content})

    url = f"{url_base}/api/chat"

    # Simplificamos el payload. El contexto siempre se envía completo.
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
    # La función render_response ahora devolverá el contenido de la respuesta para guardarlo
    response_content, exit_code = render_response(str(model), req, bool(stream))
    if exit_code == 0 and response_content:
        context.append({"role": "assistant", "content": response_content})
    return exit_code


