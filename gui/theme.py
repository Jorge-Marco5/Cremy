"""
Módulo de tema centralizado para IAMarker basado en la paleta Catppuccin Mocha.
https://catppuccin.com/palette/#flavor
"""

from typing import Dict
from pygments.style import Style as PygmentsStyle
from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
)
from questionary import Style as QuestionaryStyle
from rich.console import Console
from rich.theme import Theme


class CatppuccinMocha:
    """Valores hexadecimales oficiales de Catppuccin Mocha."""

    # Fondos (Base, Mantle, Crust)
    BASE = "#1e1e2e"
    MANTLE = "#181825"
    CRUST = "#11111b"

    # Superficies y separadores
    SURFACE0 = "#313244"
    SURFACE1 = "#45475a"
    SURFACE2 = "#585b70"

    # Overlays (texto atenuado / comentarios)
    OVERLAY0 = "#6c7086"
    OVERLAY1 = "#7f849c"
    OVERLAY2 = "#9399b2"

    # Textos
    SUBTEXT0 = "#a6adc8"
    SUBTEXT1 = "#bac2de"
    TEXT = "#cdd6f4"

    # Acentos cromáticos
    LAVENDER = "#b4befe"
    BLUE = "#89b4fa"
    SAPPHIRE = "#74c7ec"
    SKY = "#89dceb"
    TEAL = "#94e2d5"
    GREEN = "#a6e3a1"
    YELLOW = "#f9e2af"
    PEACH = "#fab387"
    MAROON = "#eba0ac"
    RED = "#f38ba8"
    MAUVE = "#cba6f7"
    PINK = "#f5c2e7"
    FLAMINGO = "#f2cdcd"
    ROSEWATER = "#f5e0dc"


def ansi_hex(hex_code: str, bold: bool = False) -> str:
    """Convierte un color hexadecimal en una secuencia de escape ANSI TrueColor (24-bit)."""
    hex_clean = hex_code.lstrip("#")
    r = int(hex_clean[0:2], 16)
    g = int(hex_clean[2:4], 16)
    b = int(hex_clean[4:6], 16)
    bold_code = "1;" if bold else ""
    return f"\033[{bold_code}38;2;{r};{g};{b}m"


# Secuencia de reset ANSI
C_RESET = "\033[0m"

# Tokens ANSI TrueColor de uso común en mensajes y roles
C_USER = ansi_hex(CatppuccinMocha.BLUE, bold=True)
C_ASSISTANT = ansi_hex(CatppuccinMocha.MAUVE, bold=True)
C_TOOL = ansi_hex(CatppuccinMocha.TEAL, bold=True)
C_SYSTEM = ansi_hex(CatppuccinMocha.PEACH, bold=True)

C_SUCCESS = ansi_hex(CatppuccinMocha.GREEN, bold=True)
C_ERROR = ansi_hex(CatppuccinMocha.RED, bold=True)
C_WARNING = ansi_hex(CatppuccinMocha.YELLOW, bold=True)
C_INFO = ansi_hex(CatppuccinMocha.SKY, bold=True)
C_MUTED = ansi_hex(CatppuccinMocha.OVERLAY0)
C_ACCENT = ansi_hex(CatppuccinMocha.LAVENDER, bold=True)

# Normal (sin negrita) para textos secundarios
C_TEXT = ansi_hex(CatppuccinMocha.TEXT)
C_INFO_NORMAL = ansi_hex(CatppuccinMocha.SKY)
C_SUCCESS_NORMAL = ansi_hex(CatppuccinMocha.GREEN)
C_WARNING_NORMAL = ansi_hex(CatppuccinMocha.YELLOW)
C_ERROR_NORMAL = ansi_hex(CatppuccinMocha.RED)


# Estilo para Questionary (prompts de terminal y autocompletado)
QUESTIONARY_MOCHA_STYLE = QuestionaryStyle(
    [
        ("qmark", f"fg:{CatppuccinMocha.SAPPHIRE} bold"),
        ("question", f"fg:{CatppuccinMocha.BLUE} bold"),
        ("answer", f"fg:{CatppuccinMocha.GREEN} bold"),
        ("pointer", f"fg:{CatppuccinMocha.MAUVE} bold"),
        ("highlighted", f"fg:{CatppuccinMocha.RED} bold"),
        ("selected", f"fg:{CatppuccinMocha.TEAL} bold"),
        ("separator", f"fg:{CatppuccinMocha.SURFACE2}"),
        ("instruction", f"fg:{CatppuccinMocha.OVERLAY0}"),
        ("completion-menu", f"bg:{CatppuccinMocha.BASE} fg:{CatppuccinMocha.TEXT}"),
        ("completion-menu.completion", f"bg:{CatppuccinMocha.BASE} fg:{CatppuccinMocha.TEXT}"),
        (
            "completion-menu.completion.current",
            f"bg:{CatppuccinMocha.SURFACE1} fg:{CatppuccinMocha.PINK} bold",
        ),
    ]
)


def get_questionary_style() -> QuestionaryStyle:
    """Retorna el estilo de Questionary configurado con Catppuccin Mocha."""
    return QUESTIONARY_MOCHA_STYLE


# Tema de Pygments para resaltado de sintaxis de código en Rich
class CatppuccinMochaPygmentsStyle(PygmentsStyle):
    """Estilo Pygments basado en Catppuccin Mocha."""

    background_color = CatppuccinMocha.BASE
    default_style = CatppuccinMocha.TEXT

    styles = {
        Comment: f"{CatppuccinMocha.OVERLAY0} italic",
        Comment.Preproc: f"{CatppuccinMocha.MAUVE}",
        Keyword: f"{CatppuccinMocha.MAUVE} bold",
        Keyword.Type: f"{CatppuccinMocha.YELLOW}",
        Keyword.Constant: f"{CatppuccinMocha.PEACH}",
        Name: f"{CatppuccinMocha.TEXT}",
        Name.Builtin: f"{CatppuccinMocha.RED}",
        Name.Function: f"{CatppuccinMocha.BLUE}",
        Name.Class: f"{CatppuccinMocha.YELLOW} bold",
        Name.Decorator: f"{CatppuccinMocha.BLUE}",
        Name.Tag: f"{CatppuccinMocha.MAUVE}",
        Name.Attribute: f"{CatppuccinMocha.TEAL}",
        String: f"{CatppuccinMocha.GREEN}",
        String.Doc: f"{CatppuccinMocha.OVERLAY1} italic",
        Number: f"{CatppuccinMocha.PEACH}",
        Operator: f"{CatppuccinMocha.SKY}",
        Punctuation: f"{CatppuccinMocha.OVERLAY2}",
        Generic.Heading: f"{CatppuccinMocha.BLUE} bold",
        Generic.Subheading: f"{CatppuccinMocha.SKY} bold",
        Generic.Error: f"{CatppuccinMocha.RED}",
        Error: f"{CatppuccinMocha.RED} bold",
    }


# Tema para la consola de Rich
CATPPUCCIN_RICH_THEME = Theme(
    {
        "user": f"bold {CatppuccinMocha.BLUE}",
        "assistant": f"bold {CatppuccinMocha.MAUVE}",
        "tool": f"bold {CatppuccinMocha.TEAL}",
        "system": f"bold {CatppuccinMocha.PEACH}",
        "success": f"bold {CatppuccinMocha.GREEN}",
        "error": f"bold {CatppuccinMocha.RED}",
        "warning": f"bold {CatppuccinMocha.YELLOW}",
        "info": f"{CatppuccinMocha.SKY}",
        "muted": f"{CatppuccinMocha.OVERLAY0}",
        "accent": f"bold {CatppuccinMocha.LAVENDER}",
        "panel.border": f"{CatppuccinMocha.SURFACE2}",
        "table.border": f"{CatppuccinMocha.SURFACE1}",
        "table.header": f"bold {CatppuccinMocha.MAUVE}",
    }
)

# Consola singleton de Rich con tema Catppuccin Mocha
console = Console(theme=CATPPUCCIN_RICH_THEME, force_terminal=True)
