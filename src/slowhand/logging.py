import datetime
import json
import logging
from collections.abc import Iterable, Mapping
from typing import Any

from rich.logging import RichHandler

from slowhand.config import settings


def _apply_style(text: Any, style: str) -> str:
    # See: https://rich.readthedocs.io/en/latest/appendix/colors.html
    return f"[{style}]{text}[/{style}]"


def primary(text: Any) -> str:
    return _apply_style(text, "bold cyan")


def secondary(text: Any) -> str:
    return _apply_style(text, "bright_blue")


def muted(text: Any) -> str:
    return _apply_style(text, "grey50")


def success(text: Any) -> str:
    return _apply_style(text, "green")


def danger(text: Any) -> str:
    return _apply_style(text, "red1")


def alert(text: Any) -> str:
    return _apply_style(text, "orange1")


def ok() -> str:
    return success("✓ ")


def _to_json_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return f"<bytes x {len(value)}>"
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, Exception):
        return f"{type(value).__name__}: {value}"
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return _to_json_value(value.model_dump())
    if isinstance(value, Mapping):
        return {k: _to_json_value(v) for k, v in value.items()}
    if isinstance(value, Iterable):
        return [_to_json_value(item) for item in value]
    return str(value)


def _safe_json_dump(value: Any) -> str:
    try:
        return json.dumps(_to_json_value(value), indent=2)
    except Exception as exc:
        return f"Fail to dump JSON: {exc}"


def _format(msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    extra = kwargs.get("extra") or {}
    if extra:
        msg = f"{msg}\n{_safe_json_dump(extra)}"
    extra["markup"] = True
    kwargs = kwargs | {"extra": extra}
    return msg, kwargs


class ConsoleLogger:
    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def debug(self, msg: str, *args, **kwargs):
        msg, kwargs = _format(msg, kwargs)
        self._logger.debug(muted(msg), *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        msg, kwargs = _format(msg, kwargs)
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        msg, kwargs = _format(msg, kwargs)
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        msg, kwargs = _format(msg, kwargs)
        self._logger.error(msg, *args, **kwargs)


def configure_logging() -> None:
    logging.basicConfig(
        level="DEBUG" if settings.debug else "INFO",
        format="%(message)s",
        datefmt="%H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)],
    )


def get_logger(name: str) -> ConsoleLogger:
    return ConsoleLogger(name)
