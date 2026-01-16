from textwrap import indent

import typer
from rich import print as rprint
import yaml

from slowhand.config import settings
from slowhand.loader import load_builtin_jobs, load_job, load_user_jobs
from slowhand.logging import configure_logging, muted, primary, secondary
from slowhand.models import Job
from slowhand.runner import resume_job, run_job
from slowhand.tools import get_gh_info, get_git_info
from slowhand.version import VERSION

configure_logging()

app = typer.Typer(no_args_is_help=True)


@app.command()
def config():
    """Print config"""
    print(settings.model_dump_json(indent=2))


@app.command()
def version():
    """Print version"""

    print(f"slowhand version {VERSION}")


@app.command()
def info():
    """Print version and tools info"""

    def print_info(title: str, content: str) -> None:
        rprint(f"[bold green]{title}[/bold green]")
        print(indent(content, "    "))
        print()

    print_info("slowhand", f"version {VERSION}")
    print_info("git", get_git_info())
    print_info("gh", get_gh_info())


@app.command()
def jobs():
    """List available jobs"""
    user_jobs = load_user_jobs()
    builtin_jobs = load_builtin_jobs()

    def print_jobs(kind: str, jobs: list[Job]):
        rprint(primary(f"{kind} jobs") + muted(f" (x{len(jobs)})"))
        for job in jobs:
            rprint(f"  - {secondary(job.job_id)} : {job.name} {muted(job.source)}")

    print_jobs("user", user_jobs)
    print_jobs("builtin", builtin_jobs)


@app.command()
def show(job_id: str, brief: bool = False):
    """Show detail of a job"""
    job = load_job(job_id)
    if brief:
        job_data = {
            "job_id": job.job_id,
            "source": job.source,
            "name": job.name,
            "steps": [step.name for step in job.steps],
        }
    else:
        job_data = job.model_dump()
    print(yaml.dump(job_data))


@app.command()
def run(job_id: str, dry_run: bool = False, clean: bool = True):
    """Load and run a job"""
    job = load_job(job_id)
    run_job(job, dry_run=dry_run, clean=clean)


@app.command()
def resume(job_id: str, dry_run: bool = False, clean: bool = True):
    """Resume a previously failed job from its checkpoint"""
    job = load_job(job_id)
    resume_job(job, dry_run=dry_run, clean=clean)


def main():
    app()


if __name__ == "__main__":
    main()
