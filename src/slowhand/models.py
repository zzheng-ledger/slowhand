from typing import Literal, Union

import yaml
from pydantic import BaseModel, Field

from slowhand.config import settings
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
    job_id: str
    source: str
    name: str
    steps: list[JobStep]


def load_job(job_id: str) -> Job:
    for jobs_dir in settings.jobs_dirs:
        job_file = jobs_dir / f"{job_id}.yaml"
        if job_file.is_file():
            with job_file.open("r") as f:
                job_data = yaml.safe_load(f)
            return Job(
                job_id=job_file.stem,
                source=str(job_file),
                **job_data,
            )
    raise SlowhandException(f"No job file found for: {job_id}")


def load_jobs() -> list[Job]:
    jobs: list[Job] = []
    for jobs_dir in settings.jobs_dirs:
        # List all files with name `*.yaml`
        if not jobs_dir.is_dir():
            continue
        for job_file in jobs_dir.glob("*.yaml"):
            if job_file.is_file():
                with job_file.open("r") as f:
                    job_data = yaml.safe_load(f)
            job = Job(
                job_id=job_file.stem,
                source=str(job_file),
                **job_data,
            )
            jobs.append(job)
    return jobs
