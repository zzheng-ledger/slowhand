from typing import override

from pydantic import BaseModel, Field

from slowhand.logging import get_logger
from slowhand.utils import run_command

from .base import Action

logger = get_logger(__name__)


class GithubCreatePrParams(BaseModel):
    repo: str = Field(pattern=r"^[\w\-]+/[\w\-]+$")
    head: str
    base: str = "main"
    title: str
    body: str = ""


class GithubCreatePr(Action):
    name = "github-create-pr"

    @override
    def run(self, params, *, context):
        params = GithubCreatePrParams(**params)
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
        run_command("gh", "pr", "create", *opts)
        return {}
