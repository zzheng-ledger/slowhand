from slowhand.context import Context
from slowhand.expression.lexer import tokenize
from slowhand.expression.parser import parse_to_ast


def evaluate_condition(condition: str, *, context: Context) -> bool:
    tokens = tokenize(condition)
    ast = parse_to_ast(tokens)
    result = ast.evaluate(context)
    return bool(result)
