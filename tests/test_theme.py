import unittest
import re
from gui.theme import (
    CatppuccinMocha,
    ansi_hex,
    C_RESET,
    C_USER,
    C_ASSISTANT,
    C_TOOL,
    C_SUCCESS,
    C_ERROR,
    C_WARNING,
    C_INFO,
    QUESTIONARY_MOCHA_STYLE,
    get_questionary_style,
    CatppuccinMochaPygmentsStyle,
    console,
)


class TestTheme(unittest.TestCase):

    def test_catppuccin_mocha_hex_values(self):
        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        colors = [
            CatppuccinMocha.BASE,
            CatppuccinMocha.MANTLE,
            CatppuccinMocha.CRUST,
            CatppuccinMocha.SURFACE0,
            CatppuccinMocha.SURFACE1,
            CatppuccinMocha.SURFACE2,
            CatppuccinMocha.OVERLAY0,
            CatppuccinMocha.OVERLAY1,
            CatppuccinMocha.OVERLAY2,
            CatppuccinMocha.SUBTEXT0,
            CatppuccinMocha.SUBTEXT1,
            CatppuccinMocha.TEXT,
            CatppuccinMocha.LAVENDER,
            CatppuccinMocha.BLUE,
            CatppuccinMocha.SAPPHIRE,
            CatppuccinMocha.SKY,
            CatppuccinMocha.TEAL,
            CatppuccinMocha.GREEN,
            CatppuccinMocha.YELLOW,
            CatppuccinMocha.PEACH,
            CatppuccinMocha.MAROON,
            CatppuccinMocha.RED,
            CatppuccinMocha.MAUVE,
            CatppuccinMocha.PINK,
            CatppuccinMocha.FLAMINGO,
            CatppuccinMocha.ROSEWATER,
        ]
        for c in colors:
            self.assertTrue(hex_pattern.match(c), f"Color inválido: {c}")

    def test_ansi_hex(self):
        # #89b4fa -> R: 137, G: 180, B: 250
        seq = ansi_hex(CatppuccinMocha.BLUE, bold=False)
        self.assertEqual(seq, "\033[38;2;137;180;250m")

        seq_bold = ansi_hex(CatppuccinMocha.BLUE, bold=True)
        self.assertEqual(seq_bold, "\033[1;38;2;137;180;250m")

    def test_semantic_ansi_constants(self):
        self.assertTrue(C_USER.startswith("\033["))
        self.assertTrue(C_ASSISTANT.startswith("\033["))
        self.assertTrue(C_TOOL.startswith("\033["))
        self.assertTrue(C_SUCCESS.startswith("\033["))
        self.assertTrue(C_ERROR.startswith("\033["))
        self.assertTrue(C_WARNING.startswith("\033["))
        self.assertTrue(C_INFO.startswith("\033["))
        self.assertEqual(C_RESET, "\033[0m")

    def test_questionary_mocha_style(self):
        style = get_questionary_style()
        self.assertIsNotNone(style)
        self.assertIs(style, QUESTIONARY_MOCHA_STYLE)

    def test_pygments_style(self):
        style = CatppuccinMochaPygmentsStyle
        self.assertEqual(style.background_color, CatppuccinMocha.BASE)
        self.assertEqual(style.default_style, CatppuccinMocha.TEXT)

    def test_pygments_style_tokens_not_black(self):
        from rich.syntax import PygmentsSyntaxTheme
        from pygments.token import Token, Text
        pst = PygmentsSyntaxTheme(CatppuccinMochaPygmentsStyle)
        text_style = pst.get_style_for_token(Token.Text)
        self.assertIsNotNone(text_style.color)
        self.assertNotEqual(text_style.color.name, "#000000")
        self.assertEqual(text_style.color.name, CatppuccinMocha.TEXT)

    def test_console_theme(self):
        self.assertIsNotNone(console)
        self.assertTrue(hasattr(console, "_theme_stack"))


if __name__ == "__main__":
    unittest.main()
