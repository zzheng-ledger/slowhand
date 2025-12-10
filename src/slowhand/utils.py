import os
import random
import subprocess
import time
from textwrap import dedent
from typing import Any

from slowhand.logging import get_logger

logger = get_logger(__name__)


def random_name(prefix: str | None = None) -> str:
    """
    Generate a lexicographically sortable random name. Earlier names are smaller.
    """
    prefix = (prefix or "").strip()
    timestamp = int(time.time() * 1000)  # timestamp in miniseconds
    suffix = random.randint(0, 0xFFFFFF)  # 6 hex digits
    return f"{prefix}_{timestamp:012x}{suffix:06x}"


def _get_subprocess_kwargs(
    cwd: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if cwd:
        kwargs["cwd"] = cwd
    if extra_env:
        kwargs["env"] = os.environ | extra_env
    return kwargs


def run_command(
    *args: str,
    cwd: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> str:
    kwargs = _get_subprocess_kwargs(cwd=cwd, extra_env=extra_env)
    logger.debug(
        "Running command",
        extra={
            "command": " ".join(args),
            "cwd": cwd,
            "extra_env": extra_env,
        },
    )
    result = subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        check=True,
        **kwargs,
    )
    return result.stdout.strip()


def run_shell_script(
    script: str,
    *,
    cwd: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> None:
    script = "\n".join(
        [
            "set -e",  # to exit (with non-zero code) on first error
            dedent(script).strip(),
        ]
    )
    kwargs = _get_subprocess_kwargs(cwd=cwd, extra_env=extra_env)
    logger.debug(
        "Running shell script",
        extra={
            "script": script,
            "cwd": cwd,
            "extra_env": extra_env,
        },
    )
    subprocess.run(
        script,
        shell=True,
        check=True,  # raise if script exits with non-zero code
        executable="/bin/bash",
        **kwargs,
    )
