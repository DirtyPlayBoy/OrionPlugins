"""Orion plugin: calculator tools for the assistant + UI page gate."""
from __future__ import annotations

import ast
import operator as op
import re

from orion_plugin_sdk import Plugin, run, tool

_BINOPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}
_UNARY = {ast.UAdd: op.pos, ast.USub: op.neg}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Num):  # py<3.8 compat
        return float(node.n)
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        return float(_BINOPS[type(node.op)](_eval_node(node.left), _eval_node(node.right)))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return float(_UNARY[type(node.op)](_eval_node(node.operand)))
    raise ValueError("unsupported expression")


def _normalize(expr: str) -> str:
    s = (expr or "").strip()
    s = s.replace("×", "*").replace("÷", "/").replace("−", "-").replace(",", ".")
    s = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", s)
    s = re.sub(r"\s+", "", s)
    return s


def safe_calc(expression: str) -> float:
    raw = _normalize(expression)
    if not raw or not re.fullmatch(r"[0-9+\-*/().]+", raw):
        raise ValueError("expression must be arithmetic only")
    tree = ast.parse(raw, mode="eval")
    return _eval_node(tree)


@tool(
    name="calculate",
    description="Evaluate a safe arithmetic expression ( +, -, *, /, %, parentheses ).",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Math expression, e.g. '12*8+5' or '25% of 480' as '480*25%'.",
            }
        },
        "required": ["expression"],
    },
)
def calculate(expression: str = ""):
    try:
        result = safe_calc(expression)
        return {"expression": expression, "normalized": _normalize(expression), "result": result, "ok": True}
    except Exception as exc:
        return {"expression": expression, "ok": False, "error": str(exc)}


@tool(
    name="percent_of",
    description="Compute percent of a value: percent% of total.",
    parameters={
        "type": "object",
        "properties": {
            "percent": {"type": "number", "description": "Percent value, e.g. 25"},
            "total": {"type": "number", "description": "Base amount"},
        },
        "required": ["percent", "total"],
    },
)
def percent_of(percent: float = 0, total: float = 0):
    p = float(percent or 0)
    t = float(total or 0)
    return {"percent": p, "total": t, "result": (p / 100.0) * t}


@tool(
    name="split_bill",
    description="Split a bill between people with optional tip percent.",
    parameters={
        "type": "object",
        "properties": {
            "amount": {"type": "number"},
            "people": {"type": "integer", "default": 2},
            "tip_percent": {"type": "number", "default": 0},
        },
        "required": ["amount"],
    },
)
def split_bill(amount: float = 0, people: int = 2, tip_percent: float = 0):
    n = max(1, int(people or 1))
    tip = max(0.0, float(tip_percent or 0))
    total = float(amount or 0) * (1.0 + tip / 100.0)
    each = total / n
    return {"amount": amount, "people": n, "tip_percent": tip, "total": round(total, 2), "each": round(each, 2)}


UI = [
    {
        "id": "calculator-page",
        "slot": "page.custom",
        "host_page": "pageCalculator",
        "label": "Калькулятор",
        "icon": "calc",
        "transparent": True,
    }
]


if __name__ == "__main__":
    run(Plugin(tools=[calculate, percent_of, split_bill], ui_contributions=UI))
