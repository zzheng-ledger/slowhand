from abc import ABC
from dataclasses import dataclass
from re import Pattern, Match
import re
from typing import Callable, ClassVar, Literal


@dataclass
class VariableToken:
    name: str


@dataclass
class StringToken:
    value: str


@dataclass
class EqNeqToken:
    op: Literal["==", "!="]


@dataclass
class AndOrToken:
    op: Literal["&&", "||"]


Token = VariableToken | StringToken | EqNeqToken | AndOrToken

TokenFactory = Callable[[Match[str]], Token]


_TOKEN_MATCHERS: list[tuple[Pattern, TokenFactory]] = [
    (
        re.compile(r"(?P<name>\w+(?:\.\w+)*)"),  # foo.bar
        lambda m: VariableToken(name=m.group("name")),
    ),
    (
        re.compile(r'"(?P<value>[^"]*)"'),  # "foo bar"
        lambda m: StringToken(value=m.group("value")),
    ),
    (
        re.compile(
            r"(?P<op>"
            + "|".join([re.escape(op) for op in ("==", "!=")])
            + ")"
        ),
        lambda m: EqNeqToken(op=m.group("op")),
    ),
    (
        re.compile(
            r"(?P<op>"
            + "|".join([re.escape(op) for op in ("&&", "||")])
            + ")"
        ),
        lambda m: AndOrToken(op=m.group("op")),
    ),
]


def tokenize(expression: str) -> list[Token]:
    tokens: list[Token] = []
    expression = expression.strip()
    pos = 0
    while pos < len(expression):
        matched = False
        for regex, make_token in _TOKEN_MATCHERS:
            match = regex.match(expression, pos)
            if match:
                tokens.append(make_token(match))
                pos = match.end()
                while pos < len(expression) and expression[pos].isspace():
                    pos += 1
                matched = True
                break
        if not matched:
            raise ValueError(f"Invalid token in: {expression} ({expression[pos:]})")
    return tokens
