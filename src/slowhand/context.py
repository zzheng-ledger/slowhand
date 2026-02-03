import json
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Self, TypeAlias

from slowhand.config import ensure_app_user_dir
from slowhand.errors import SlowhandException
from slowhand.logging import get_logger
from slowhand.utils import random_name

logger = get_logger(__name__)

# Format is `${{ foo.bar }}` to be distinguished from a normal shell variable (`$foobar`).
_VAR_REGEX = re.compile(r"\${{([^}]+)}}")

_VAR_NAME_REGEX = re.compile(
    r"^(?:"
    r"meta\.[\w-]+"
    r"|inputs\.[\w-]+"
    r"|steps\.[\w-]+\.outputs\.[\w-]+"
    r")$"
)

_META_JOB_ID = "meta.job_id"
_META_RUN_ID = "meta.run_id"
_META_RUN_DIR = "meta.run_dir"
_META_START_TIME = "meta.start_time"


def _split_name(var_name: str) -> tuple[list[str], str]:
    tokens = var_name.split(".")
    if not tokens:
        raise SlowhandException(f"Invalid variable name: {var_name}")
    return tokens[:-1], tokens[-1]


StateValue: TypeAlias = str | bool | int | None | dict[str, "StateValue"]
StateStore: TypeAlias = dict[str, StateValue]


def _set_state_value(state: StateStore, name: str, value: StateValue) -> None:
    parent_keys, leaf_key = _split_name(name)
    current: StateStore = state
    for key in parent_keys:
        node = current.setdefault(key, {})
        if not isinstance(node, dict):
            raise SlowhandException(
                f"Invalid value type at {key}: {type(current).__name__}"
            )
        current = node
    current[leaf_key] = value


def _get_state_value(state: StateStore, name: str) -> StateValue:
    parent_keys, leaf_key = _split_name(name)
    current: StateStore = state
    for key in parent_keys:
        node = current.get(key)
        if node is None:
            return None
        if not isinstance(node, dict):
            raise SlowhandException(
                f"Invalid value type at {key}: {type(current).__name__}"
            )
        current = node
    value = current.get(leaf_key)
    if not isinstance(value, (dict, str, bool, int, type(None))):
        raise SlowhandException(
            f"Variable resolves to invalid type ({type(value).__name__}): {name}"
        )
    return value


def _get_checkpoint_file() -> Path:
    return ensure_app_user_dir() / "checkpoint.json"


class Context:
    def __init__(self, job_id: str, *, state: StateStore | None = None) -> None:
        if state is None:
            state = {}
            _set_state_value(state, _META_JOB_ID, job_id)
            _set_state_value(state, _META_RUN_ID, random_name("run"))
            _set_state_value(state, _META_RUN_DIR, tempfile.mkdtemp(prefix="slowhand_"))
            _set_state_value(state, _META_START_TIME, datetime.now().isoformat())
        for meta_name in (_META_JOB_ID, _META_RUN_ID, _META_RUN_DIR, _META_START_TIME):
            meta_value = _get_state_value(state, meta_name)
            if not isinstance(meta_value, str) or not meta_value:
                raise SlowhandException(
                    f"Invalid state: missing required meta variable: {meta_name}"
                )
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
        outputs = _get_state_value(self._state, f"steps.{step_id}.outputs")
        return outputs is not None

    def save_inputs(self, inputs: dict[str, Any]) -> None:
        logger.debug("Saving inputs", extra=inputs)
        _set_state_value(self._state, "inputs", inputs)

    def save_step_outputs(self, step_id: str, outputs: dict[str, Any]) -> None:
        logger.debug("Saving step outputs of %s", step_id, extra=outputs)
        _set_state_value(self._state, f"steps.{step_id}.outputs", outputs)

    def resolve(self, input: Any) -> Any:
        if isinstance(input, str):
            return _VAR_REGEX.sub(lambda m: self.resolve_variable(m.group(1)), input)
        if isinstance(input, dict):
            return dict((key, self.resolve(value)) for key, value in input.items())
        if isinstance(input, list):
            return [self.resolve(item) for item in input]
        return input

    def resolve_variable(self, var_name: str) -> str:
        var_name = var_name.strip()
        if not _VAR_NAME_REGEX.match(var_name):
            raise SlowhandException(f"Invalid variable name: {var_name}")
        value = _get_state_value(self._state, var_name)
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
