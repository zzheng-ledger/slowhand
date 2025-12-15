from textwrap import dedent
from typing import override

from pydantic import BaseModel

from slowhand.errors import SlowhandException
from slowhand.logging import get_logger

from .base import Action

logger = get_logger(__name__)


class Abort(Action):
    name = "abort"

    class Params(BaseModel):
        message: str

    @override
    def run(self, params, *, context):
        params = self.Params(**params)
        message = dedent(params.message)
        raise SlowhandException(f"Aborted with message:\n{message}")
