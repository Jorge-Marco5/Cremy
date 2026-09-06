import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.json"
file_path = str(CONFIG_FILE)


def read_config():
    try:
        if not os.path.exists(file_path):
            return {}
        with open(file_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def write_config(key: str, value):
    try:
        current = read_config()
        current[key] = value
        with open(file_path, "w") as f:
            json.dump(current, f, indent=4)
    except Exception as e:
        print(f"Error al guardar la configuración: {e}")


def get_config(key: str):
    try:
        current = read_config()
        return current.get(key)
    except Exception as e:
        print(f"Error al obtener la configuración: {e}")
        return None

def save_usage(model, tokens, duration):
    try:
        """Guardar o actualizar estadísticas de uso en config.json"""
        usage = get_config("usage") or {}
        if model not in usage:
            usage[model] = {}
        total_tokens = usage.get(model, {}).get("tokens", 0)
        total_duration = usage.get(model, {}).get("duration", 0)
        usage[model]["tokens"] = total_tokens + (tokens or 0)
        usage[model]["duration"] = total_duration + (duration or 0)
        write_config("usage", usage)
    except Exception as e:
        print(f"Error al guardar las estadísticas de uso: {e}")



def clear_active_line(text: str, width: int):
    """Borra la línea activa teniendo en cuenta el ancho del terminal."""
    if not text:
        return
    num_rows = (len(text) + width - 1) // width
    if num_rows > 1:
        sys.stdout.write(f"\033[{num_rows - 1}A")
    sys.stdout.write("\r\033[J")
    sys.stdout.flush()

def parse_option_value(value: str):
    """Convierte un string de la CLI al tipo adecuado (bool, int, float o str)."""
    if not isinstance(value, str):
        return value
    val_lower = value.strip().lower()
    if val_lower == "true":
        return True
    if val_lower == "false":
        return False
    # Intentar como int
    try:
        return int(value.strip())
    except ValueError:
        pass
    # Intentar como float
    try:
        return float(value.strip())
    except ValueError:
        pass
    # Intentar como JSON (para listas de stop words ej. ["stop1"])
    try:
        parsed = json.loads(value.strip())
        if isinstance(parsed, (list, dict)):
            return parsed
    except Exception:
        pass
    return value.strip()

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

def encode_image(image_path: str) -> str:
    """Valida y codifica un archivo de imagen en Base64 para la API de Ollama."""
    import base64
    path = Path(image_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"No se encontró el archivo de imagen: '{image_path}'")
    if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        exts = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
        raise ValueError(f"Extensión no soportada '{path.suffix}'. Formatos soportados: {exts}")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def parse_interactive_image_input(user_input: str) -> tuple:
    """
    Detecta comandos interactivos como:
    /image /ruta/a/imagen.png Pregunta sobre la imagen
    /img "ruta con espacios.jpg" Otra pregunta
    Retorna (texto_pregunta, lista_de_rutas_imagenes).
    """
    stripped = user_input.strip()
    if not (stripped.startswith("/image") or stripped.startswith("/img")):
        return user_input, []

    parts = stripped.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        return "", []

    rest = parts[1].strip()
    import shlex
    try:
        tokens = shlex.split(rest)
    except ValueError:
        tokens = rest.split()

    if not tokens:
        return "", []

    img_path = tokens[0]
    if len(tokens) > 1:
        prompt = " ".join(tokens[1:])
    else:
        prompt = "¿Puedes describir y analizar esta imagen en detalle?"

    return prompt, [img_path]

def format_bytes(size_bytes: int) -> str:
    """Convierte bytes a formato legible (B, KB, MB, GB)."""
    if size_bytes is None:
        return "N/A"
    try:
        size = float(size_bytes)
    except (ValueError, TypeError):
        return "N/A"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}" if unit in ["MB", "GB", "TB"] else f"{int(size)} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"