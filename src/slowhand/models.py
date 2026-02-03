import hashlib
import re
import unicodedata
from typing import Literal, cast

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from slowhand.errors import SlowhandException

InputValue = str | bool | int


def _str_to_bool(s: str) -> bool:
    s = s.lower()
    if s in ("y", "yes", "true", "1"):
        return True
    if s in ("n", "no", "false", "0"):
        return False
    raise ValueError(f"Invalid bool value: {s}")


def _str_to_int(s: str) -> int:
    try:
        return int(s)
    except ValueError:
        raise ValueError(f"Invalid int value: {s}")


def _slugify(text: str) -> str:
    value = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[-\s]+", "-", value)
    return value.strip("-_")


class JobInput(BaseModel):
    description: str | None = None
    type: Literal["string", "bool", "int"]
    required: bool = False
    default: InputValue | None = None

    @field_validator("default")
    @classmethod
    def validate_default(
        cls, value: InputValue | None, info: ValidationInfo
    ) -> InputValue | None:
        if value is None:
            return value

        input_type = info.data.get("type")
        if not isinstance(input_type, str):
            raise ValueError(
                f"Input type should be a string but got: {type(input_type).__name__}"
            )

        expected_default_value_type: type | None = {
            "string": str,
            "bool": bool,
            "int": int,
        }.get(input_type)
        if expected_default_value_type is None:
            raise ValueError(f"Invalid input type: {input_type}")
        if not isinstance(value, expected_default_value_type):
            raise ValueError(f"Default value must be of {input_type} type")
        return cast(InputValue, value)

    def parse_value(self, raw_value: str | None) -> InputValue | None:
        if raw_value is None:
            value = self.default
        else:
            match self.type:
                case "string":
                    value = raw_value.strip()
                case "bool":
                    value = _str_to_bool(raw_value)
                case "int":
                    value = _str_to_int(raw_value)
                case _:
                    raise ValueError(f"Invalid input type: {self.type}")
        if self.required and value is None:
            raise ValueError("Input is required but not provided")
        return value


class BaseJobStep(BaseModel):
    provided_id: str | None = Field(None, alias="id")
    name: str
    condition: str | None = Field(None, alias="if")

    @property
    def id(self) -> str:
        if self.provided_id:
            return self.provided_id
        # Build a deterministic and non-empty ID from step name.
        prefix = "auto"
        slug = _slugify(self.name)
        suffix = hashlib.sha256(self.name.encode("utf-8")).hexdigest()[:8]
        return "__".join([prefix, slug, suffix])


class UseAction(BaseJobStep):
    kind: Literal["UseAction"] = "UseAction"
    uses: str
    params: dict = Field(default_factory=dict, alias="with")


class RunShell(BaseJobStep):
    kind: Literal["RunShell"] = "RunShell"
    run: str
    working_dir: str | None = Field(None, alias="working-dir")

    def as_use_action_step(self) -> UseAction:
        step_data = {
            "id": self.provided_id,
            "name": self.name,
            "condition": self.condition,
            "uses": "actions/shell",
            "with": {
                "script": self.run,
                "working-dir": self.working_dir,
            },
        }
        return UseAction(**step_data)


class StepsAction(BaseJobStep):
    kind: Literal["StepsAction"] = "StepsAction"
    steps: list["JobStep"]


JobStep = UseAction | RunShell | StepsAction


class Job(BaseModel):
    job_id: str
    source: str
    name: str
    inputs: dict[str, JobInput] = Field(default_factory=dict)
    steps: list[JobStep]

    def validate_steps(self):
        seen_step_ids = set()
        for step in self.steps:
            step_id = step.id
            if step_id in seen_step_ids:
                raise SlowhandException(f"Duplicated step ID: {step_id}")
            seen_step_ids.add(step_id)

    def parse_inputs(self, input_data: dict[str, str]) -> dict[str, InputValue | None]:
        # First, make sure all provided inputs are known to the job.
        for name in input_data.keys():
            if name not in self.inputs:
                raise SlowhandException(f"{name}: Unknown input name")

        result = {}
        for name, input in self.inputs.items():
            try:
                value = input.parse_value(input_data.get(name))
            except ValueError as exc:
                raise SlowhandException(f"{name}: {exc}")
            result[name] = value
        return result
