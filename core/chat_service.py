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

def send_chat_request(args, user_input=None, images=None):
    """Realiza una peticion '/api/chat' a la API de Ollama."""
    try:
        url_base = get_config("url")
        stream = get_config("stream")
        models = get_config("models")
        model = args.model if args.model else get_config("model")

        if models and model not in models:
            clear_context()
            print(f"\n{Fore.RED}{Style.BRIGHT}Error: {Style.RESET_ALL}El modelo '{model}' no está disponible. Usa 'models' para ver los modelos disponibles.")
            return 1
    
        # Validar si el modelo soporta visión
        models_info = get_config("models") or {}
        target_model_data = models_info.get(str(model))
        model_caps = []
        if isinstance(target_model_data, dict):
            model_caps = target_model_data.get("capabilities", [])
    
        name_lower = str(model).lower()
        supports_vision = ("vision" in model_caps) or any(
            vn in name_lower for vn in ["vision", "minicpm-v", "llava", "moondream", "vl", "qwen3.5"]
        )

        # Determina el contenido del mensaje del usuario
        if user_input:
            content = user_input
        elif hasattr(args, 'text') and args.text:
            content = args.text
        else:
            clear_context()
            return 1 # No hay texto para enviar

        # Determina las imágenes adjuntas si fueron pasadas
        image_paths = []
        if images:
            image_paths = [images] if isinstance(images, str) else list(images)
        elif not user_input and getattr(args, 'image', None):
            raw_img = args.image
            image_paths = [raw_img] if isinstance(raw_img, str) else list(raw_img)

        b64_images = []
        if image_paths:

            if target_model_data and isinstance(target_model_data, dict) and not supports_vision:
                vision_models = [
                    m_name for m_name, m_val in models_info.items()
                    if isinstance(m_val, dict) and ("vision" in m_val.get("capabilities", []) or any(vn in m_name.lower() for vn in ["vision", "minicpm-v", "llava"]))
                ]
                print(f"\n{Fore.RED}{Style.BRIGHT}Error de compatibilidad:{Style.RESET_ALL} El modelo '{Fore.CYAN}{model}{Style.RESET_ALL}' no tiene capacidad de procesamiento de imágenes (visión).")
                if vision_models:
                    print(f"{Fore.YELLOW}Modelos disponibles con soporte de visión en tu servidor:{Style.RESET_ALL}")
                    for vm in vision_models:
                        print(f"  • {Fore.GREEN}{vm}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Ejemplo para usar un modelo con visión: {Fore.CYAN}-m {vision_models[0]}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}Ninguno de tus modelos instalados soporta visión. Puedes descargar uno ejecutando:{Style.RESET_ALL}")
                    print(f"  {Fore.CYAN}ollama run qwen3.5:2b{Style.RESET_ALL} o {Fore.CYAN}ollama run llama3.2-vision{Style.RESET_ALL}")
                return 1

            from utils.helpers import encode_image
            try:
                for img_p in image_paths:
                    b64_images.append(encode_image(img_p))
                print(f"{Fore.CYAN}🖼️  [Imagen adjunta: {', '.join(image_paths)}]{Style.RESET_ALL}")
            except Exception as img_err:
                print(f"\n{Fore.RED}{Style.BRIGHT}Error al procesar imagen: {img_err}{Style.RESET_ALL}")
                return 1

        # Añade el mensaje del usuario al contexto y a la BD si aplica
        user_message = {"role": "user", "content": content}
        if b64_images:
            user_message["images"] = b64_images
        context.append(user_message)

        if args.uuid:
            dataServices.insert_message({
                "conversation_uuid": args.uuid,
                "role": "user",
                "content": content,
                "images": image_paths if image_paths else None
            })

        url = f"{url_base}/api/chat"

        sys_prompt = get_config("system_prompt")
        messages_payload = []
        if sys_prompt and str(sys_prompt).strip():
            messages_payload.append({"role": "system", "content": str(sys_prompt)})

        sanitized_images_count = 0
        for msg in context:
            if not supports_vision and "images" in msg:
                sanitized_msg = {"role": msg["role"], "content": msg["content"]}
                messages_payload.append(sanitized_msg)
                sanitized_images_count += 1
            else:
                messages_payload.append(msg)

        if sanitized_images_count > 0:
            print(f"{Fore.YELLOW}ℹ️  Aviso: El modelo '{model}' no soporta visión. Se omitieron las imágenes históricas ({sanitized_images_count}).{Style.RESET_ALL}")

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
            "think": get_config("think"),
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
