from tools.registry import registry
from tools.definitions.weather_tool import WeatherTool

def init_tools():
    """
    Define y carga las tools personalizadas del usuario
    """
    registry.register(WeatherTool())
