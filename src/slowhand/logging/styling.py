# See: https://rich.readthedocs.io/en/latest/appendix/colors.html


def _styled(text: str, style: str) -> str:
    return f"[{style}]{text}[/{style}]"


def primary(text: str) -> str:
    return _styled(text, "bold bright_cyan")


def secondary(text: str) -> str:
    return _styled(text, "bright_blue")


def muted(text: str) -> str:
    return _styled(text, "grey50")


def danger(text: str) -> str:
    return _styled(text, "red1")


def alert(text: str) -> str:
    return _styled(text, "orange1")
