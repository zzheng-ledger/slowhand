from pydantic import BaseModel, Field
from slowhand.logging import get_logger
from typing import override
import shlex

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
    def __init__(self, id: str | None) -> None:
        super().__init__(id)

    @override
    def run(self, params, *, context):
        params = GithubCreatePrParams(**params)
        opts = " ".join([
            f"--repo {params.repo}",
            f"--head {params.head}",
            f"--base {params.base}",
            f"--title {shlex.quote(params.title)}",
            f"--body {shlex.quote(params.body)}",
        ])
        script = f"gh pr create {opts}"

        # gh pr create --repo ORG_NAME/REPO_NAME --title "My PR title" --body "Description of my PR" --base main --head my-feature-branch
        logger.warning("TODO: [%s] %s", self.name, script, extra={"params": params})
