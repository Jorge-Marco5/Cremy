from datetime import datetime
from typing import Any, Dict
from tools.base import BaseTool


class DateTimeTool(BaseTool):
    name = "get_current_datetime"
    description = "Obtiene la fecha y hora actual del sistema local."
    parameters = {
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "description": "Formato opcional de fecha (por defecto: '%Y-%m-%d %H:%M:%S')."
            }
        },
        "required": []
    }
    require_confirmation = False
    enabled_by_default = True

    def execute(self, **kwargs) -> Dict[str, Any]:
        fmt = kwargs.get("format") or "%Y-%m-%d %H:%M:%S"
        now = datetime.now()
        return {
            "datetime": now.strftime(fmt),
            "iso": now.isoformat(),
            "weekday": now.strftime("%A")
        }
