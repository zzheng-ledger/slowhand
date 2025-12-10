from pprint import pprint

from slowhand.expression.lexer import tokenize
from slowhand.expression.parser import parse_to_ast


def test_tokenize():
    tokens = tokenize('foo.bar == "dummy" && "xy" != x.y || a.b == "ab" && u.v != "uv"')
    ast = parse_to_ast(tokens)
    print()
    pprint(ast)
