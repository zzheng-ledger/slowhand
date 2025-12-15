from typing import override

from pydantic import BaseModel, Field

from slowhand.logging import get_logger
from slowhand.utils import random_name, run_command

from .base import Action

logger = get_logger(__name__)


class GitClone(Action):
    name = "git-clone"

    class Params(BaseModel):
        repo: str = Field(pattern=r"^[\w\-]+/[\w\-]+$")
        fetch_depth: int | None = Field(None, alias="fetch-depth", gt=0)
        new_branch: str | None = Field(None, alias="new-branch")

        @property
        def bare_name(self) -> str:
            return self.repo.split("/")[-1]

        @property
        def github_url(self) -> str:
            return f"git@github.com:{self.repo}.git"

        @property
        def clone_opts(self) -> list[str]:
            opts = []
            if self.fetch_depth is not None:
                opts.extend(["--depth", str(self.fetch_depth)])
            return opts

    @override
    def run(self, params, *, context):
        params = self.Params(**params)
        local_dir = str(context.run_dir / random_name(params.bare_name))
        run_command("git", "clone", params.github_url, local_dir, *params.clone_opts)
        head_hash = run_command("git", "rev-parse", "HEAD", cwd=local_dir)
        if params.new_branch:
            run_command("git", "checkout", "-b", params.new_branch, cwd=local_dir)
        return {
            "repo": {
                "local_dir": local_dir,
                "head_hash": head_hash,
                "head_hash_short": head_hash[:7],
                "new_branch": params.new_branch,
            }
        }
