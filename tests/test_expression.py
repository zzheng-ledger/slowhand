from slowhand.expression.lexer import tokenize
from slowhand.expression.parser import parse_to_ast


def test_eq_expression():
    tokens = tokenize('foo.bar == "dummy"')
    ast = parse_to_ast(tokens)
    assert ast.to_dict() == {
        "type": "EqNeqNode",
        "op": "==",
        "left": {
            "type": "VariableNode",
            "name": "foo.bar",
        },
        "right": {
            "type": "StringNode",
            "value": "dummy",
        },
    }


def test_and_expression():
    tokens = tokenize('foo.bar == "dummy" && "abc" != a.b.c')
    ast = parse_to_ast(tokens)
    assert ast.to_dict() == {
        "type": "AndOrNode",
        "op": "&&",
        "left": {
            "type": "EqNeqNode",
            "op": "==",
            "left": {
                "type": "VariableNode",
                "name": "foo.bar",
            },
            "right": {
                "type": "StringNode",
                "value": "dummy",
            },
        },
        "right": {
            "type": "EqNeqNode",
            "op": "!=",
            "left": {
                "type": "StringNode",
                "value": "abc",
            },
            "right": {
                "type": "VariableNode",
                "name": "a.b.c",
            },
        },
    }


def test_and_or_expression():
    tokens = tokenize('foo.bar == "dummy" && "abc" != a.b.c || x.y == "xy"')
    ast = parse_to_ast(tokens)
    assert ast.to_dict() == {
        "type": "AndOrNode",
        "op": "||",
        "left": {
            "type": "AndOrNode",
            "op": "&&",
            "left": {
                "type": "EqNeqNode",
                "op": "==",
                "left": {
                    "type": "VariableNode",
                    "name": "foo.bar",
                },
                "right": {
                    "type": "StringNode",
                    "value": "dummy",
                },
            },
            "right": {
                "type": "EqNeqNode",
                "op": "!=",
                "left": {
                    "type": "StringNode",
                    "value": "abc",
                },
                "right": {
                    "type": "VariableNode",
                    "name": "a.b.c",
                },
            },
        },
        "right": {
            "type": "EqNeqNode",
            "op": "==",
            "left": {
                "type": "VariableNode",
                "name": "x.y",
            },
            "right": {
                "type": "StringNode",
                "value": "xy",
            },
        },
    }


def test_complex_expression():
    tokens = tokenize(
        'foo.bar == "dummy" && "xyz" != x.y.z || '
        'a.b.c == "abc" || person.name != "James Bond"'
    )
    ast = parse_to_ast(tokens)
    assert ast.to_dict() == {
        "type": "AndOrNode",
        "op": "||",
        "left": {
            "type": "AndOrNode",
            "op": "||",
            "left": {
                "type": "AndOrNode",
                "op": "&&",
                "left": {
                    "type": "EqNeqNode",
                    "op": "==",
                    "left": {
                        "type": "VariableNode",
                        "name": "foo.bar",
                    },
                    "right": {
                        "type": "StringNode",
                        "value": "dummy",
                    },
                },
                "right": {
                    "type": "EqNeqNode",
                    "op": "!=",
                    "left": {
                        "type": "StringNode",
                        "value": "xyz",
                    },
                    "right": {
                        "type": "VariableNode",
                        "name": "x.y.z",
                    },
                },
            },
            "right": {
                "type": "EqNeqNode",
                "op": "==",
                "left": {
                    "type": "VariableNode",
                    "name": "a.b.c",
                },
                "right": {
                    "type": "StringNode",
                    "value": "abc",
                },
            },
        },
        "right": {
            "type": "EqNeqNode",
            "op": "!=",
            "left": {
                "type": "VariableNode",
                "name": "person.name",
            },
            "right": {
                "type": "StringNode",
                "value": "James Bond",
            },
        },
    }
