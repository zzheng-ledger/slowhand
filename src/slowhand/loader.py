from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

import yaml

from slowhand.config import settings
from slowhand.errors import SlowhandException
from slowhand.models import Job

PACKAGE_NAME = "slowhand"


class JobSource:
    def __init__(self, file: Path | Traversable) -> None:
        self._file = file

    @property
    def job_id(self) -> str:
        if isinstance(self._file, Path):
            return self._file.stem
        name = self._file.name
        if "." in name:
            return name.rsplit(".", 1)[0]
        return name

    def create_job(self) -> Job:
        with self._file.open("r") as f:
            data = yaml.safe_load(f)
        return Job(
            job_id=self.job_id,
            source=str(self._file),
            **data,
        )


def find_job_source(job_id: str) -> JobSource:
    for jobs_dir in settings.jobs_dirs:
        user_job_file = jobs_dir / f"{job_id}.yaml"
        if user_job_file.is_file():
            return JobSource(user_job_file)

    builtin_job_file = files(PACKAGE_NAME).joinpath(f"jobs/{job_id}.yaml")
    if builtin_job_file.is_file():
        return JobSource(builtin_job_file)

    raise SlowhandException(f"Job file not found: {job_id}")


def load_job(job_id: str) -> Job:
    return find_job_source(job_id).create_job()


def load_user_jobs() -> list[Job]:
    jobs: list[Job] = []
    for jobs_dir in settings.jobs_dirs:
        if not jobs_dir.is_dir():
            continue
        for job_file in jobs_dir.glob("*.yaml"):
            if job_file.is_file():
                jobs.append(JobSource(job_file).create_job())
    return jobs


def load_builtin_jobs() -> list[Job]:
    jobs: list[Job] = []
    jobs_dir = files(PACKAGE_NAME).joinpath("jobs")
    if jobs_dir.is_dir():
        for job_file in jobs_dir.iterdir():
            if job_file.is_file() and job_file.name.endswith(".yaml"):
                jobs.append(JobSource(job_file).create_job())
    return jobs
