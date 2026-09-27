"""Safe arithmetic expression evaluator for the calculator app.

The calculator previously passed whatever the user typed into the display
box straight to Python's builtin ``eval()`` — that executes arbitrary code
(``__import__("os").system("...")`` works from a textbox). This module
provides an AST-based evaluator that only accepts arithmetic expressions:

``numbers``, ``+ - * / // % **`` and parentheses.
"""

import ast
import operator

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_MAX_EXPRESSION_LENGTH = 200


def evaluate(expression):
    """Evaluate an arithmetic *expression* and return its numeric result.

    Returns an ``int`` when the result is mathematically integral, otherwise
    a ``float``. Raises ``ValueError`` for anything that is not a plain
    arithmetic expression (names, calls, attribute access, imports, ...) and
    for division by zero.
    """
    if not isinstance(expression, str):
        raise ValueError("expression must be a string")
    if not expression.strip():
        raise ValueError("empty expression")
    if len(expression) > _MAX_EXPRESSION_LENGTH:
        raise ValueError("expression too long")

    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError:
        raise ValueError("invalid expression") from None
    value = _eval_node(tree.body)

    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        op = _BIN_OPS[type(node.op)]
        try:
            return op(_eval_node(node.left), _eval_node(node.right))
        except ZeroDivisionError:
            raise ValueError("division by zero") from None

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))

    raise ValueError("unsupported expression")