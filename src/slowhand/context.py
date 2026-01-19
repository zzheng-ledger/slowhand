import json
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Self

from slowhand.config import ensure_app_user_dir
from slowhand.errors import SlowhandException
from slowhand.logging import get_logger
from slowhand.utils import random_name

logger = get_logger(__name__)

# Format is `${{ foo.bar }}` to be distinguished from a normal shell variable (`$foobar`).
VARIABLE_REGEX = re.compile(r"\${{\s*([\w\-]+(?:\.[\w\-]+)+)\s*}}")

_META_JOB_ID = "meta.job_id"
_META_RUN_ID = "meta.run_id"
_META_RUN_DIR = "meta.run_dir"
_META_START_TIME = "meta.start_time"


def _split_var_name(var_name: str) -> tuple[list[str], str]:
    tokens = var_name.split(".")
    if not tokens:
        raise SlowhandException(f"Invalid variable name: {var_name}")
    return tokens[:-1], tokens[-1]


def _set_variable(store: dict, var_name: str, value: Any) -> None:
    parent_keys, leaf_key = _split_var_name(var_name)
    current = store
    for key in parent_keys:
        current = current.setdefault(key, {})
        if not isinstance(current, dict):
            raise SlowhandException(
                f"Invalid value type at {key}: {type(current).__name__}"
            )
    current[leaf_key] = value


def _get_variable(store: dict, var_name: str) -> dict | str | bool | int | None:
    parent_keys, leaf_key = _split_var_name(var_name)
    current: dict = store
    for key in parent_keys:
        next_value = current.get(key)
        if next_value is None:
            return None
        if not isinstance(next_value, dict):
            raise SlowhandException(
                f"Invalid value type at {key}: {type(current).__name__}"
            )
        current = next_value
    value = current.get(leaf_key)
    if not isinstance(value, (dict, str, bool, int, type(None))):
        raise SlowhandException(
            f"Variable resolves to invalid type ({type(value).__name__}): {var_name}"
        )
    return value


def _get_checkpoint_file() -> Path:
    return ensure_app_user_dir() / "checkpoint.json"


class Context:
    def __init__(self, job_id: str, *, state: dict[str, Any] | None = None) -> None:
        if state is None:
            state = {}
            _set_variable(state, _META_JOB_ID, job_id)
            _set_variable(state, _META_RUN_ID, random_name("run"))
            _set_variable(state, _META_RUN_DIR, tempfile.mkdtemp(prefix="slowhand_"))
            _set_variable(state, _META_START_TIME, datetime.now().isoformat())
        for var_name in (_META_JOB_ID, _META_RUN_ID, _META_RUN_DIR, _META_START_TIME):
            if _get_variable(state, var_name) is None:
                raise SlowhandException("Invalid state: missing required variable(s)")
        self._state = state

    @property
    def job_id(self) -> str:
        return self.resolve_variable(_META_JOB_ID)

    @property
    def run_id(self) -> str:
        return self.resolve_variable(_META_RUN_ID)

    @property
    def run_dir(self) -> Path:
        return Path(self.resolve_variable(_META_RUN_DIR))

    @property
    def start_time(self) -> datetime:
        value = self.resolve_variable(_META_START_TIME)
        return datetime.fromisoformat(value)

    def has_step_outputs(self, step_id: str) -> bool:
        outputs = _get_variable(self._state, f"steps.{step_id}.outputs")
        return outputs is not None

    def save_inputs(self, inputs: dict[str, Any]) -> None:
        logger.debug("Saving inputs", extra=inputs)
        _set_variable(self._state, "inputs", inputs)

    def save_step_outputs(self, step_id: str, outputs: dict[str, Any]) -> None:
        logger.debug("Saving step outputs of %s", step_id, extra=outputs)
        _set_variable(self._state, f"steps.{step_id}.outputs", outputs)

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
        value = _get_variable(self._state, var_name)
        return str(value) if value is not None else ""

    def dump_state_json(self) -> str:
        return json.dumps(self._state, indent=2)

    def teardown(self):
        run_dir = self.run_dir
        if run_dir.is_dir():
            logger.info("Deleting run directory: %s", run_dir)
            shutil.rmtree(run_dir)

    def save_checkpoint(self) -> str:
        checkpoint_file = _get_checkpoint_file()
        checkpoint_file.write_text(json.dumps(self._state, indent=2))
        return str(checkpoint_file)

    def delete_checkpoint(self) -> None:
        checkpoint_file = _get_checkpoint_file()
        if checkpoint_file.is_file():
            checkpoint_file.unlink()

    @classmethod
    def load_checkpoint(cls) -> Self:
        checkpoint_file = _get_checkpoint_file()
        if not checkpoint_file.is_file():
            raise SlowhandException(f"{checkpoint_file} is not a file")
        with checkpoint_file.open("r") as f:
            context_state = json.load(f)
        context = cls("<unused-job-id>", state=context_state)
        return context
