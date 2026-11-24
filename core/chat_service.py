from utils.helpers import get_config, write_config
from gui.render import render_response
import urllib.request
from persistent.db import DataService
import json
from gui.theme import (
    C_ERROR,
    C_INFO,
    C_MUTED,
    C_RESET,
    C_SUCCESS,
    C_TOOL,
    C_WARNING,
)

dataServices = DataService()
# El historial del chat es un estado de la sesión, debe vivir aquí.
context = []

def clear_context():
    """Limpia el historial del chat en memoria."""
    context.clear()

def _build_messages_payload(messages_list, supports_vision):
    """Construye el payload de mensajes formateado para la API de Ollama."""
    sys_prompt = get_config("system_prompt")
    messages_payload = []
    if sys_prompt and str(sys_prompt).strip():
        messages_payload.append({"role": "system", "content": str(sys_prompt)})

    for msg in messages_list:
        msg_dict = {"role": msg["role"], "content": msg.get("content", "")}
        if "tool_calls" in msg and msg["tool_calls"]:
            msg_dict["tool_calls"] = msg["tool_calls"]
        if supports_vision and "images" in msg and msg["images"]:
            msg_dict["images"] = msg["images"]
        messages_payload.append(msg_dict)
    return messages_payload


def send_chat_request(args, user_input=None, images=None):
    """Realiza una peticion '/api/chat' a la API de Ollama."""
    try:
        url_base = get_config("url")
        stream = get_config("stream")
        models = get_config("models")
        model = args.model if args.model else get_config("model")

        if models and model not in models:
            clear_context()
            print(f"\n{C_ERROR}Error: {C_RESET}El modelo '{model}' no está disponible. Usa 'models' para ver los modelos disponibles.")
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
                print(f"\n{C_ERROR}Error de compatibilidad:{C_RESET} El modelo '{C_INFO}{model}{C_RESET}' no tiene capacidad de procesamiento de imágenes (visión).")
                if vision_models:
                    print(f"{C_WARNING}Modelos disponibles con soporte de visión en tu servidor:{C_RESET}")
                    for vm in vision_models:
                        print(f"  • {C_SUCCESS}{vm}{C_RESET}")
                    print(f"{C_WARNING}Ejemplo para usar un modelo con visión: {C_INFO}-m {vision_models[0]}{C_RESET}")
                else:
                    print(f"{C_WARNING}Ninguno de tus modelos instalados soporta visión. Puedes descargar uno ejecutando:{C_RESET}")
                    print(f"  {C_INFO}ollama run qwen3.5:2b{C_RESET} o {C_INFO}ollama run llama3.2-vision{C_RESET}")
                return 1

            from utils.helpers import encode_image
            try:
                for img_p in image_paths:
                    b64_images.append(encode_image(img_p))
                print(f"{C_INFO}[Imagen adjunta: {', '.join(image_paths)}]{C_RESET}")
            except Exception as img_err:
                print(f"\n{C_ERROR}Error al procesar imagen: {img_err}{C_RESET}")
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

        # Detección de soporte y esquemas de herramientas
        supports_tools = ("tools" in model_caps)
        from tools.registry import registry
        from utils.helpers import get_tools_config
        from gui.tools_view import ask_tool_confirmation, render_tool_result

        tools_cfg = get_tools_config()
        active_tools = registry.get_active_tools_schemas(tools_cfg) if supports_tools else []

        messages_payload = _build_messages_payload(context, supports_vision)

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
        if active_tools:
            payload["tools"] = active_tools
        if options:
            payload["options"] = options

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        response_content, exit_code, tool_calls = render_response(str(model), req, bool(stream))

        # Ciclo de ejecución de herramientas (tope de 5 iteraciones)
        max_iterations = 5
        iteration = 0

        while exit_code == 0 and tool_calls and iteration < max_iterations:
            iteration += 1

            # Registrar mensaje del asistente con sus tool_calls
            assistant_turn = {
                "role": "assistant",
                "content": response_content or "",
                "tool_calls": tool_calls
            }
            context.append(assistant_turn)
            if args.uuid:
                dataServices.insert_message({
                    "conversation_uuid": args.uuid,
                    "role": "assistant",
                    "content": response_content or "",
                    "tool_calls": tool_calls
                })

            for tc in tool_calls:
                fn_info = tc.get("function", {})
                t_name = fn_info.get("name", "")
                raw_args = fn_info.get("arguments", {})
                if isinstance(raw_args, str):
                    try:
                        args_dict = json.loads(raw_args)
                    except Exception:
                        args_dict = {}
                elif isinstance(raw_args, dict):
                    args_dict = raw_args
                else:
                    args_dict = {}

                # Validar disponibilidad y confirmación en tiempo de ejecución
                if not registry.is_tool_enabled(t_name, tools_cfg):
                    exec_res = registry.execute_tool(t_name, args_dict, tools_config=tools_cfg)
                    render_tool_result(t_name, exec_res.get("error"), is_error=True)
                else:
                    needs_confirm = registry.is_confirmation_required(t_name, tools_cfg)
                    if needs_confirm:
                        confirmed = ask_tool_confirmation(t_name, args_dict)
                    else:
                        confirmed = True
                        print(f"{C_TOOL}[Ejecutando herramienta: {t_name}]{C_RESET}")

                    exec_res = registry.execute_tool(t_name, args_dict, tools_config=tools_cfg, confirmed=confirmed)
                    is_err = not exec_res.get("success", False)
                    res_display = exec_res.get("result") if not is_err else exec_res.get("error")
                    render_tool_result(t_name, res_display, is_error=is_err)

                tool_msg = {
                    "role": "tool",
                    "tool_name": t_name,
                    "content": json.dumps(exec_res, ensure_ascii=False)
                }
                context.append(tool_msg)
                if args.uuid:
                    dataServices.insert_message({
                        "conversation_uuid": args.uuid,
                        "role": "tool",
                        "content": json.dumps(exec_res, ensure_ascii=False),
                        "tool_name": t_name
                    })

            # Generar siguiente consulta a Ollama con los resultados de las herramientas
            next_messages = _build_messages_payload(context, supports_vision)
            next_payload = {
                "model": str(model),
                "messages": next_messages,
                "think": get_config("think"),
                "stream": stream
            }
            if active_tools:
                next_payload["tools"] = active_tools
            if options:
                next_payload["options"] = options

            next_req = urllib.request.Request(
                url,
                data=json.dumps(next_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            response_content, exit_code, tool_calls = render_response(str(model), next_req, bool(stream))

        if iteration >= max_iterations and tool_calls:
            print(f"\n{C_WARNING}Se alcanzó el límite de {max_iterations} iteraciones de herramientas.{C_RESET}")

        if exit_code == 0 and response_content and not tool_calls:
            context.append({"role": "assistant", "content": response_content})
            if args.uuid:
                success = dataServices.insert_message({
                    "conversation_uuid": args.uuid,
                    "role": "assistant",
                    "content": response_content
                })
                if not success:
                    print(f"\n{C_WARNING}Advertencia:{C_RESET} No se pudo guardar la respuesta del asistente en la base de datos.")

        return exit_code
    except Exception as e:
        print(f"\n{C_ERROR}Error de conexión: {e}{C_RESET}")
        print(f"{C_WARNING}Asegúrate de que Ollama está corriendo con el comando: {C_INFO}ollama serve{C_RESET}")
        return 1
