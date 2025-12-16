from typing import Literal

from pydantic import BaseModel, Field


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


JobStep = UseAction | RunShell


class Job(BaseModel):
    job_id: str
    source: str
    name: str
    steps: list[JobStep]
