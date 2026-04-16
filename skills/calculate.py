"""
Calculate Skill — Performs calculations
"""
from typing import Dict, Any
import ast
import operator

async def run(context: Dict, args: Dict) -> Dict[str, Any]:
    expression = args.get("expression", "")
    
    if not expression:
        return {"error": "expression required"}
    
    # Safe math evaluation
    safe_math_ops = {
        'add': operator.add,
        'sub': operator.sub,
        'mul': operator.mul,
        'truediv': operator.truediv,
        'pow': operator.pow,
        'abs': abs,
        'round': round,
    }
    
    try:
        # Direct eval for simple expressions (limited)
        result = eval(expression, {"__builtins__": {}}, safe_math_ops)
        return {
            "expression": expression,
            "result": result,
            "type": type(result).__name__
        }
    except Exception as e:
        return {
            "expression": expression,
            "error": str(e),
            "result": None
        }

meta = {
    "name": "calculate",
    "description": "Performs basic calculations",
    "args": {"expression": "math expression (e.g., 2+2, 10*5)"},
    "triggers": ["calculate", "compute", "math", "plus", "minus", "times"]
}