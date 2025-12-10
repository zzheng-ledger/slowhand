from dataclasses import dataclass
from typing import Literal

from slowhand.context import Context
from slowhand.expression.lexer import Token, StringToken, VariableToken, EqNeqToken, AndOrToken


@dataclass
class VariableNode:
    name: str

    def evaluate(self, context: Context) -> str:
        return context.resolve_variable(self.name)

@dataclass
class StringNode:
    value: str

    def evaluate(self, context: Context) -> str:
        return self.value


@dataclass
class EqNeqNode:
    left: "ASTNode"
    op: Literal["==", "!="]
    right: "ASTNode"

    def evaluate(self, context: Context) -> str:
        left = self.left.evaluate(context)
        right = self.right.evaluate(context)
        if self.op == "==":
            return left == right
        else:
            return left != right



@dataclass
class AndOrNode:
    left: "ASTNode"
    op: Literal["&&", "||"]
    right: "ASTNode"

    def evaluate(self, context: Context) -> str:
        left = self.left.evaluate(context)
        right = self.right.evaluate(context)
        if self.op == "&&":
            return bool(left and right)
        else:
            return bool(left or right)


ASTNode = VariableNode | StringNode | EqNeqNode | AndOrNode


class TokenList:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._index = 0

    def peek(self) -> Token | None:
        if self._index < len(self._tokens):
            return self._tokens[self._index]
        return None

    def consume(self) -> Token:
        if self._index >= len(self._tokens):
            raise ValueError(f"No token to consume at index {self._index}")
        token = self._tokens[self._index]
        self._index += 1
        return token


def _parse_atom(tokens: TokenList) -> ASTNode:
    token = tokens.consume()
    match token:
        case VariableToken(name):
            return VariableNode(name)
        case StringToken(value):
            return StringNode(value)
        case _:
            raise ValueError(f"Unexpected token: {token}")


def _parse_eq_neq(tokens: TokenList) -> ASTNode:
    node = _parse_atom(tokens)
    if (token := tokens.peek()) and isinstance(token, EqNeqToken):
        tokens.consume()  # pop out the peeked operator
        right = _parse_atom(tokens)
        node = EqNeqNode(left=node, op=token.op, right=right)
    return node


def _parse_and(tokens: TokenList) -> ASTNode:
    node = _parse_eq_neq(tokens)
    while (token := tokens.peek()) and isinstance(token, AndOrToken) and token.op == "&&":
        tokens.consume()  # pop out the peeked operator
        right = _parse_eq_neq(tokens)
        node = AndOrNode(left=node, op=token.op, right=right)
    return node



def _parse_or(tokens: TokenList) -> ASTNode:
    node = _parse_and(tokens)
    while (token := tokens.peek()) and isinstance(token, AndOrToken) and token.op == "||":
        tokens.consume()  # pop out the peeked operator
        right = _parse_and(tokens)
        node = AndOrNode(left=node, op=token.op, right=right)
    return node


def parse_to_ast(tokens: list[Token]) -> ASTNode:
    return _parse_or(TokenList(tokens))
