import re
from typing import override

from pydantic import BaseModel, Field

from slowhand.errors import SlowhandException
from slowhand.logging import get_logger
from slowhand.utils import run_command

from .base import Action

logger = get_logger(__name__)


class GithubCreatePr(Action):
    name = "github-create-pr"

    class Params(BaseModel):
        repo: str = Field(pattern=r"^[\w\-]+/[\w\-]+$")
        head: str
        base: str = "main"
        title: str
        body: str = ""

        @property
        def pr_link_prefix(self) -> str:
            return f"https://github.com/{self.repo}/pull/"

    @override
    def run(self, params, *, context, dry_run):
        params = self.Params(**params)
        opts = [
            "--repo",
            params.repo,
            "--head",
            params.head,
            "--base",
            params.base,
            "--title",
            params.title,
            "--body",
            params.body,
        ]
        if not dry_run:
            output = run_command("gh", "pr", "create", *opts)
            match_obj = re.search(
                re.escape(params.pr_link_prefix) + r"(?P<pr_number>\d+)",
                output,
            )
            if not match_obj:
                raise SlowhandException(f"Cannot find PR number in gh output: {output}")
            pr_number = match_obj.group("pr_number")
        else:
            logger.warning("Dry-run: gh pr create ...")
            pr_number = "<NUMBER>"
        return {
            "pr_number": pr_number,
            "pr_link": f"{params.pr_link_prefix}{pr_number}",
        }


class GithubEditPr(Action):
    name = "github-edit-pr"

    class Params(BaseModel):
        pr_link: str = Field(alias="pr-link")
        title: str | None = None
        body: str | None = None

    @override
    def run(self, params, *, context, dry_run):
        params = self.Params(**params)
        opts = []
        if params.title:
            opts.extend(["--title", params.title])
        if params.body:
            opts.extend(["--body", params.body])
        if not opts:
            raise SlowhandException(f"Nothing to edit for PR: {params.pr_link}")
        if not dry_run:
            run_command("gh", "pr", "edit", params.pr_link, *opts)
        else:
            logger.warning("Dry-run: gh pr edit ...")
        return {}
