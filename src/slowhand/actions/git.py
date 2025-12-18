from functools import partial
from typing import override

from pydantic import BaseModel, Field

from slowhand.errors import SlowhandException
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
    def run(self, params, *, context, dry_run):
        params = self.Params(**params)
        repo_dir = str(context.run_dir / random_name(params.bare_name))
        run_command("git", "clone", params.github_url, repo_dir, *params.clone_opts)
        head_hash = run_command("git", "rev-parse", "HEAD", cwd=repo_dir)
        if params.new_branch:
            run_command("git", "checkout", "-b", params.new_branch, cwd=repo_dir)
        return {
            "repo_dir": repo_dir,
            "head_hash": head_hash,
            "head_hash_short": head_hash[:7],
            "new_branch": params.new_branch,
        }


class GitCommitPushBranch(Action):
    name = "git-commit-push-branch"

    class Params(BaseModel):
        repo_dir: str = Field(alias="repo-dir")
        message: str
        branch: str

    @override
    def run(self, params, *, context, dry_run):
        params = self.Params(**params)
        if params.branch in ("main", "master"):
            raise SlowhandException(f"Pushing to {params.branch} branch is disallowed")

        run_in_repo = partial(run_command, cwd=params.repo_dir)

        try:
            run_in_repo("git", "diff", "--quiet")
            run_in_repo("git", "diff", "--cached", "--quiet")
            has_changes = False
        except Exception:
            has_changes = True
        if not has_changes:
            raise SlowhandException(f"No changes to commit in: {params.repo_dir}")

        current_branch = run_in_repo("git", "rev-parse", "--abbrev-ref", "HEAD")
        if current_branch.strip() != params.branch:
            logger.info("Checking out new branch: %s", params.branch)
            run_in_repo("git", "checkout", "-b", params.branch)

        run_in_repo("git", "add", "-A")
        run_in_repo("git", "commit", "-m", params.message)
        if not dry_run:
            run_in_repo("git", "push", "--set-upstream", "origin", params.branch)
        else:
            logger.warning("Dry-run: git push ...")
        return {}
