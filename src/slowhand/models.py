from typing import Literal, Union

import yaml
from pydantic import BaseModel, Field

from slowhand.config import config
from slowhand.errors import SlowhandException


class BaseJobStep(BaseModel):
    id: str | None = None
    name: str
    condition: str | None = Field(None, alias="if")


class RunShell(BaseJobStep):
    kind: Literal["RunShell"] = "RunShell"
    run: str
    working_dir: str | None = Field(None, alias="working-dir")


class UseAction(BaseJobStep):
    kind: Literal["UseAction"] = "UseAction"
    uses: str
    params: dict = Field(default_factory=dict, alias="with")


JobStep = Union[UseAction, RunShell]


class Job(BaseModel):
    name: str
    steps: list[JobStep]


def load_job(name: str) -> Job:
    for jobs_dir in config.jobs_dirs:
        job_file = jobs_dir / f"{name}.yaml"
        if job_file.is_file():
            with job_file.open("r") as f:
                job_data = yaml.safe_load(f)
            return Job(**job_data)
    raise SlowhandException(f"No job file found for: {name}")
