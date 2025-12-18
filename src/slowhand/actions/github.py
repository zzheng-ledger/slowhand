from typing import override

from pydantic import BaseModel, Field

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
            run_command("gh", "pr", "create", *opts)
        else:
            logger.warning("Dry-run: gh pr create ...")
        return {}
