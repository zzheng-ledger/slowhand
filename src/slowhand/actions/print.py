from textwrap import dedent, indent
from typing import override

from pydantic import BaseModel

from slowhand.logging import get_logger

from .base import Action

logger = get_logger(__name__)


class Print(Action):
    name = "print"

    class Params(BaseModel):
        message: str

    @override
    def run(self, params, *, context, dry_run):
        params = self.Params(**params)
        message = dedent(params.message).strip()
        print()
        print(indent(message, "    "))
        print()
