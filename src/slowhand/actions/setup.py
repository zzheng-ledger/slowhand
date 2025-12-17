from pathlib import Path
import re
from textwrap import dedent
from typing import override

from rich.prompt import Prompt
from jira import JIRA

from slowhand.config import Settings, settings
from slowhand.errors import SlowhandException
from slowhand.logging import get_logger, ok, primary
from slowhand.utils import run_command

from .base import Action

logger = get_logger(__name__)


def checked_run_command(*args: str, prompt_on_error: str) -> str:
    try:
        return run_command(*args)
    except Exception as exc:
        command = " ".join(args)
        message = f"Fail to run `{command}`: {exc}"
        logger.error(message)
        logger.info(dedent(prompt_on_error))
        raise SlowhandException(message)


def save_user_settings(settings: Settings):
    settings_file = settings.save()
    logger.info("%s Saved settings in: %s", ok(), primary(settings_file))


class SetupGit(Action):
    name = "setup-git"

    @override
    def run(self, params, *, context):
        output = checked_run_command(
            "git",
            "--version",
            prompt_on_error="""
                To install git, run:

                    sudo apt update
                    sudo apt install -y git
            """,
        )
        match_obj = re.search(r"git version (?P<version>[\d\-\.]+)", output)
        if not match_obj:
            raise SlowhandException(f"Unknown output: {output}")
        git_version = match_obj.group("version")
        logger.info("%s git version: %s", ok(), primary(git_version))
        return {"git_version": git_version}


class SetupGh(Action):
    name = "setup-gh"

    @override
    def run(self, params, *, context):
        gh_version_output = checked_run_command(
            "gh",
            "--version",
            prompt_on_error="To install gh, see: https://cli.github.com",
        )
        match_obj = re.search(r"gh version (?P<version>[\d\-\.]+)", gh_version_output)
        if not match_obj:
            raise SlowhandException(f"Unknown output: {gh_version_output}")
        gh_version = match_obj.group("version")
        logger.info("%s gh version: %s", ok(), primary(gh_version))

        checked_run_command(
            "gh",
            "auth",
            "status",
            prompt_on_error="""
                You are not authenticated in Github.com with a PAT (personal access token).
                Go create one and save it in `GH_TOKEN` or `GITHUB_TOKEN`:
                https://github.com/settings/tokens
            """,
        )
        logger.info("%s You are authenticated in Github.com", ok())

        return {"gh_version": gh_version}


class SetupJira(Action):
    name = "setup-jira"

    @override
    def run(self, params, *, context):
        jira_server = settings.jira.server
        jira_email = settings.jira.email
        if not jira_server:
            jira_server = Prompt.ask(
                "Enter Jira server", default="https://ledgerhq.atlassian.net"
            )
        if not jira_email:
            jira_email = Prompt.ask("Enter your email in Jira")
        settings.jira.server = jira_server
        settings.jira.email = jira_email
        save_user_settings(settings)

        jira_api_token = settings.jira.api_token
        if not jira_api_token:
            logger.info(
                dedent(
                    """
                    Jira API token is not configured.
                    See: https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/

                    - Authenticate in https://id.atlassian.com
                    - Create API token (don't use scopes)
                    - Specify API token name and expiration
                    - Create token, and save it in env var: `JIRA_API_TOKEN`
                    """
                )
            )
            raise SlowhandException("Jira API token is not configured")

        jira = JIRA(
            server=jira_server,
            basic_auth=(jira_email, jira_api_token.get_secret_value()),
        )
        myself = jira.myself()
        display_name = myself.get("displayName")
        is_active = myself.get("active")
        if not is_active:
            raise SlowhandException("Fail to authenticate in Jira")
        logger.info(
            "%s You are authenticated in Jira as: %s",
            ok(),
            primary(display_name),
        )
        return {"jira_display_name": display_name}


class SetupJobsDirs(Action):
    name = "setup-jobs-dirs"

    @override
    def run(self, params, *, context):
        if not settings.jobs_dirs:
            jobs_dir = Path.home() / "slowhand"
            settings.jobs_dirs = [str(jobs_dir)]
            save_user_settings(settings)
        jobs_dirs = ", ".join([primary(d) for d in settings.jobs_dirs])
        logger.info("%s Using user jobs dirs: %s", ok(), jobs_dirs)
        return {}
