from slowhand.errors import SlowhandException

from .abort import Abort
from .base import Action, ActionParams
from .git import GitClone
from .github import GithubCreatePr
from .jira import JiraCreateMoTicket
from .revault import RevaultFindDeployVersions, RevaultUpdateDeployVersions
from .shell import Shell

__all__ = ("Action", "ActionParams", "create_action")

_BUILTIN_ACTIONS: dict[str, type[Action]] = {
    f"actions/{action_class.name}": action_class
    for action_class in (
        Abort,
        GitClone,
        GithubCreatePr,
        JiraCreateMoTicket,
        Shell,
        RevaultFindDeployVersions,
        RevaultUpdateDeployVersions,
    )
}


def create_action(name: str) -> Action:
    action_class = _BUILTIN_ACTIONS.get(name)
    if action_class is None:
        raise SlowhandException(f"Cannot find action {name}")
    return action_class()
