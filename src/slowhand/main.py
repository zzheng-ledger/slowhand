from textwrap import indent

import typer
from rich import print as rprint

from slowhand.config import config
from slowhand.logging import configure_logging
from slowhand.models import load_job, load_jobs
from slowhand.runner import run_job
from slowhand.tools import get_gh_info, get_git_info
from slowhand.version import VERSION

configure_logging()

app = typer.Typer()


@app.command("config")
def manage_config(create: bool = False):
    print(config.model_dump_json(indent=2))
    if create:
        pass


@app.command()
def info():
    def print_info(title: str, content: str) -> None:
        rprint(f"[bold green]{title}[/bold green]")
        print(indent(content, "    "))
        print()

    print_info("slowhand", f"version {VERSION}")
    print_info("git", get_git_info())
    print_info("gh", get_gh_info())


@app.command()
def jobs():
    jobs = load_jobs()
    rprint(f"Found [bold]{len(jobs)}[/bold] jobs")
    for job in jobs:
        rprint(
            f"  - [bold green]{job.job_id}[/bold green] : "
            f"{job.name} "
            f"[grey50]@ {job.source}[/grey50]"
        )


@app.command()
def job(name: str, clean: bool = True):
    job = load_job(name)
    run_job(job, clean=clean)


def main():
    app()

if __name__ == "__main__":
    main()
