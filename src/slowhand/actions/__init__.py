from slowhand.errors import SlowhandException

from .abort import Abort
from .base import Action, ActionParams
from .git import GitClone, GitCommitPushBranch
from .github import GithubCreatePr, GithubEditPr
from .jira import JiraCreateMoTicket
from .revault_deploy import RevaultFindDeployVersions, RevaultUpdateDeployVersions
from .revault_deps import RevaultRevertMobileDeps
from .setup import SetupGh, SetupGit, SetupJira, SetupJobsDirs
from .shell import Shell
from .version import ComputeVersion

__all__ = ("Action", "ActionParams", "create_action")

_BUILTIN_ACTIONS: dict[str, type[Action]] = {
    f"actions/{action_class.name}": action_class
    for action_class in (
        Abort,
        ComputeVersion,
        GitClone,
        GitCommitPushBranch,
        GithubCreatePr,
        GithubEditPr,
        JiraCreateMoTicket,
        Shell,
        RevaultFindDeployVersions,
        RevaultUpdateDeployVersions,
        RevaultRevertMobileDeps,
        SetupGit,
        SetupGh,
        SetupJira,
        SetupJobsDirs,
    )
}


def create_action(name: str) -> Action:
    action_class = _BUILTIN_ACTIONS.get(name)
    if action_class is None:
        raise SlowhandException(f"Cannot find action {name}")
    return action_class()
