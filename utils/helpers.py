import json
import os
import sys

file_path = "config.json"


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