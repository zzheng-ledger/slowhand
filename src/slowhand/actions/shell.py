from pathlib import Path
from typing import override

from pydantic import BaseModel, Field, field_validator

from slowhand.logging import get_logger
from slowhand.utils import random_name, run_shell_script

from .base import Action

logger = get_logger(__name__)


def _load_output_file(output_filepath: Path) -> dict[str, str]:
    if not output_filepath.is_file():
        return {}

    output: dict[str, str] = {}
    with output_filepath.open("r") as f:
        for line in f.readlines():
            tokens = line.split("=", 1)
            if len(tokens) == 2:
                key = tokens[0].strip()
                value = tokens[1].strip()
                output[key] = value
    return output


class ShellParams(BaseModel):
    script: str = Field(min_length=1)
    working_dir: str | None = Field(None, alias="working-dir")

    @field_validator("working_dir")
    @classmethod
    def validate_working_dir(cls, value: str | None) -> str | None:
        if value is not None:
            path = Path(value)
            if not path.exists():
                raise ValueError(f"Directory does not exist: {value}")
            if not path.is_dir():
                raise ValueError(f"Path is not a directory: {value}")
        return value


class Shell(Action):
    name = "shell"

    @override
    def run(self, params, *, context):
        params = ShellParams(**params)
        cwd = params.working_dir or context.run_dir
        output_filepath = context.run_dir / random_name("output")
        extra_env = {"OUTPUT": str(output_filepath)}
        run_shell_script(params.script, cwd=cwd, extra_env=extra_env)
        return _load_output_file(output_filepath)
