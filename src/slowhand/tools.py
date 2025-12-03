from slowhand.utils import run_command


def _safe_run_command(*args: str) -> str:
    try:
        return run_command(*args)
    except Exception as exc:
        command = " ".join(args)
        return f"`{command}` failed: {exc}"


def get_git_info() -> str:
    return _safe_run_command("git", "version")


def get_gh_info() -> str:
    version = _safe_run_command("gh", "version")
    auth_status = _safe_run_command("gh", "auth", "status")
    return "\n".join([version, auth_status])
