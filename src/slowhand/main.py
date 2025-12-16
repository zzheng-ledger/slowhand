from textwrap import indent

import typer
from rich import print as rprint

from slowhand.config import settings
from slowhand.loader import load_builtin_jobs, load_job, load_user_jobs
from slowhand.logging import configure_logging, muted, primary, secondary
from slowhand.models import Job
from slowhand.runner import run_job
from slowhand.tools import get_gh_info, get_git_info
from slowhand.version import VERSION

configure_logging()

app = typer.Typer(no_args_is_help=True)


@app.command()
def config():
    """Print config"""
    print(settings.model_dump_json(indent=2))


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
def run(name: str, clean: bool = True):
    """Load and run a job"""
    job = load_job(name)
    run_job(job, clean=clean)


def main():
    app()


if __name__ == "__main__":
    main()
