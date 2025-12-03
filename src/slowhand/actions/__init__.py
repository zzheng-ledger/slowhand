from slowhand.actions.shell import Shell
from slowhand.errors import SlowhandException
from .github import GithubCreatePr
from .git import GitClone
from .base import Action, ActionParams

__all__ = (
    "Action",
    "ActionParams",
    "create_action",
)

_BUILTIN_ACTIONS = {
    "actions/git-clone": GitClone,
    "actions/github-create-pr": GithubCreatePr,
    "actions/shell": Shell,
}


def create_action(name: str, id: str | None) -> Action:
    action_class = _BUILTIN_ACTIONS.get(name)
    if action_class is None:
        raise SlowhandException(f"Cannot find action {name}")
    return action_class(id)
