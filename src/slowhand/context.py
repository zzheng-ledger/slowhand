from datetime import datetime
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any

from slowhand.errors import SlowhandException
from slowhand.logging import get_logger
from slowhand.utils import random_name

logger = get_logger(__name__)

VARIABLE_REGEX = re.compile(r"\${([\w\-\.]+)}")


class Context:
    def __init__(self) -> None:
        self._run_id = random_name("run")
        self._run_dir = Path(tempfile.mkdtemp(prefix="slowhand_"))
        self._start_time = datetime.now()
        self._outputs: dict[str, dict[str, Any]] = {}

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def run_dir(self) -> Path:
        return self._run_dir

    @property
    def start_time(self) -> datetime:
        return self._start_time

    def save_output(self, action_id: str, output: dict[str, Any]) -> None:
        logger.debug("Saving output of %s", action_id, extra=output)
        self._outputs[action_id] = output

    def resolve(self, input: Any) -> Any:
        if isinstance(input, str):
            repl = lambda m: self.resolve_variable(m.group(1))
            return VARIABLE_REGEX.sub(repl, input)
        if isinstance(input, dict):
            return dict((key, self.resolve(value)) for key, value in input.items())
        if isinstance(input, list):
            return [self.resolve(item) for item in input]
        return input

    def resolve_variable(self, var_name: str) -> str:
        current = self._outputs
        for token in var_name.split("."):
            if not isinstance(current, dict):
                raise SlowhandException(f"Variable canont be resolved: {var_name}")
            current = current.get(token)
            if current is None:
                break
        if not isinstance(current, (str, bool, int, type(None))):
            raise SlowhandException(
                f"Variable resolves to invalid type ({type(current).__name__}): {var_name}"
            )
        return str(current) if current is not None else ""

    def teardown(self):
        if self._run_dir.exists():
            shutil.rmtree(self._run_dir)
            logger.debug("Deleted run directory: %s", self._run_dir)
