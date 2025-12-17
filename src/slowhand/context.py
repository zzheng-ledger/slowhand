import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from slowhand.errors import SlowhandException
from slowhand.logging import get_logger
from slowhand.utils import random_name

logger = get_logger(__name__)

# Format is `${{ foo.bar }}` to be distinguished from a normal shell variable (`$foobar`).
VARIABLE_REGEX = re.compile(r"\${{\s*([\w\-]+(?:\.[\w\-]+)+)\s*}}")


class Context:
    def __init__(self) -> None:
        self._run_id = random_name("run")
        self._run_dir = Path(tempfile.mkdtemp(prefix="slowhand_"))
        self._start_time = datetime.now()
        self._store: dict[str, Any] = {}

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def run_dir(self) -> Path:
        return self._run_dir

    @property
    def start_time(self) -> datetime:
        return self._start_time

    def _save_in_store(self, path: list[str], value: Any) -> None:
        current = self._store
        for key in path[:-1]:
            current = current.setdefault(key, {})
            if not isinstance(current, dict):
                raise SlowhandException(
                    f"Invalid value type at {key}: {type(current).__name__}"
                )
        current[path[-1]] = value

    def save_step_outputs(self, step_id: str, outputs: dict[str, Any]) -> None:
        logger.debug("Saving step outputs of %s", step_id, extra=outputs)
        self._save_in_store(["steps", step_id, "outputs"], outputs)

    def resolve(self, input: Any) -> Any:
        if isinstance(input, str):
            return VARIABLE_REGEX.sub(
                lambda m: self.resolve_variable(m.group(1)),
                input,
            )
        if isinstance(input, dict):
            return dict((key, self.resolve(value)) for key, value in input.items())
        if isinstance(input, list):
            return [self.resolve(item) for item in input]
        return input

    def resolve_variable(self, var_name: str) -> str:
        current: dict | str | None = self._store
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
