import ast
import operator
from typing import Any, Dict
from tools.base import BaseTool


class CalculatorTool(BaseTool):
    name = "calculator"
    aliases = ["calc"]
    primary_arg = "expression"
    description = "Evalúa de forma segura expresiones matemáticas (suma, resta, multiplicación, división, potencias, etc.)."
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Expresión matemática a evaluar (ej. '15 * (4 + 3)^2' o 'sqrt(144)' o '25 * 4.5')."
            }
        },
        "required": ["expression"]
    }
    require_confirmation = False
    enabled_by_default = True

    # Operadores binarios y unarios soportados de forma segura
    _OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def _eval_node(self, node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Valor no permitido: {node.value}")
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_type = type(node.op)
            if op_type in self._OPERATORS:
                return self._OPERATORS[op_type](left, right)
            raise ValueError(f"Operador no soportado: {op_type.__name__}")
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op_type = type(node.op)
            if op_type in self._OPERATORS:
                return self._OPERATORS[op_type](operand)
            raise ValueError(f"Operador unario no soportado: {op_type.__name__}")
        else:
            raise ValueError(f"Expresión no permitida: {ast.dump(node)}")

    def execute(self, **kwargs) -> Dict[str, Any]:
        expr = kwargs.get("expression", "").strip()
        if not expr:
            raise ValueError("La expresión matemática no puede estar vacía.")

        # Reemplazar '^' por '**' para potencias comunes
        normalized_expr = expr.replace("^", "**")

        # Parsear con AST
        try:
            parsed = ast.parse(normalized_expr, mode='eval')
        except SyntaxError as e:
            raise ValueError(f"Sintaxis matemática inválida: {e}")

        result = self._eval_node(parsed.body)
        return {
            "expression": expr,
            "result": result
        }
