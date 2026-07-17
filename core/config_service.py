import json

file_path = "config.json"

def read_config():
    with open(file_path, "r") as file:
        return json.load(file)

def write_config(key: str, value):
    current_config = read_config()
    current_config[key] = value
    with open(file_path, "w") as file:
        json.dump(current_config, file, indent=4)

def get_config(key: str):
    current_config = read_config()
    return current_config.get(key)