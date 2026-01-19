import difflib
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Callable, override

from pydantic import BaseModel, Field

from slowhand.errors import SlowhandException
from slowhand.logging import get_logger
from slowhand.utils import run_command

from .base import Action

logger = get_logger(__name__)

DEP_REGEX = re.compile(r'^\s*"(?P<lib>[^"]+)": "(?P<version>[^"]+)",?\s*$')


def parse_dep_lib_and_version(line: str) -> tuple[str, str]:
    match_obj = DEP_REGEX.match(line)
    if not match_obj:
        raise SlowhandException(f"Unknown dep line: {line}")
    lib = match_obj.group("lib")
    version = match_obj.group("version")
    return lib, version


def parse_deps(lines: list[str]) -> dict[str, str]:
    deps = {}
    for line in lines:
        lib, version = parse_dep_lib_and_version(line)
        deps[lib] = version
    return deps


def apply_dep(line: str, deps: dict[str, str]) -> str:
    lib, version = parse_dep_lib_and_version(line)
    target_version = deps[lib]
    if version != target_version:
        return line.replace(f'"{version}"', f'"{target_version}"')
    return line


def load_deps_in_packages(
    revault_dir: Path, excludes: Sequence[str] | None = None
) -> dict[str, str]:
    excludes = excludes or []
    deps: dict[str, str] = {}
    packages_dir = revault_dir / "packages"
    for package_json in packages_dir.glob("*/package.json"):
        # Skip excluded packages
        if package_json.parent.name in excludes:
            continue
        with package_json.open("r") as f:
            data = json.load(f)
        deps.update(data.get("dependencies") or {})
        deps.update(data.get("devDependencies") or {})
    return deps


def load_deps_in_non_mobile_packages(revault_dir: Path) -> dict[str, str]:
    deps: dict[str, str] = {}
    packages_dir = revault_dir / "packages"
    for package_json in packages_dir.glob("*/package.json"):
        # Skip mobile package
        if package_json.parent.name == "mobile":
            continue
        with package_json.open("r") as f:
            data = json.load(f)
        deps.update(data.get("dependencies") or {})
        deps.update(data.get("devDependencies") or {})
    return deps


def pick_upgrades(
    old_deps_lines: list[str],
    new_deps_lines: list[str],
    libs_to_upgrade: set[str],
) -> list[str]:
    old_deps = parse_deps(old_deps_lines)
    new_deps = parse_deps(new_deps_lines)

    libs_modified = set(old_deps.keys())
    if libs_modified != set(new_deps.keys()):
        raise SlowhandException(
            "Updated libs do not match: "
            + ", ".join(libs_modified)
            + " vs. "
            + ", ".join(new_deps.keys())
        )

    deps = {
        # Take the new version if the lib is also used in other non-mobile packages.
        # If the lib is only used by mobile, keep the old version.
        lib: new_deps[lib] if lib in libs_to_upgrade else old_deps[lib]
        for lib in libs_modified
    }
    return [apply_dep(line, deps) for line in old_deps_lines]


def pick_dep_upgrades(
    *,
    old_deps_lines: list[str],
    new_deps_lines: list[str],
    should_upgrade: Callable[[str], bool],
) -> list[str]:
    old_deps = parse_deps(old_deps_lines)
    new_deps = parse_deps(new_deps_lines)

    libs_modified = set(old_deps.keys())
    if libs_modified != set(new_deps.keys()):
        raise SlowhandException(
            "Updated libs do not match: "
            + ", ".join(libs_modified)
            + " vs. "
            + ", ".join(new_deps.keys())
        )

    deps = {
        lib: new_deps[lib] if should_upgrade(lib) else old_deps[lib]
        for lib in libs_modified
    }
    return [apply_dep(line, deps) for line in old_deps_lines]


def pick_dep_upgrades_in_package_json(
    revault_dir: Path,
    package_json: Path,
    should_upgrade: Callable[[str], bool],
) -> None:
    if not revault_dir.is_dir():
        raise ValueError(f"{revault_dir} is not a directory")
    if not package_json.is_file():
        raise ValueError(f"{package_json} is not a file")
    if not package_json.is_relative_to(revault_dir):
        raise ValueError(f"{package_json} is not relative to {revault_dir}")

    old_text = run_command(
        "git",
        "show",
        f"HEAD:{package_json.relative_to(revault_dir)}",
        cwd=revault_dir,
    )
    new_text = package_json.read_text()

    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    diff = difflib.SequenceMatcher(None, old_lines, new_lines)
    for tag, i1, i2, j1, j2 in diff.get_opcodes():
        if tag == "equal":
            continue
        elif tag == "replace":
            lines = pick_dep_upgrades(
                old_deps_lines=old_lines[i1:i2],
                new_deps_lines=new_lines[j1:j2],
                should_upgrade=should_upgrade,
            )
            # Update the new lines in-place
            new_lines[i1:i2] = lines
        else:
            raise SlowhandException(f"Unexpected diff tag: {tag}")

    package_json.write_text("\n".join(new_lines))


class RevaultRevertPinnedDeps(Action):
    name = "revault-revert-pinned-deps"

    class Params(BaseModel):
        revault_dir: str = Field(alias="revault-dir")
        pin: str

    @override
    def run(self, params, *, context, dry_run):
        params = self.Params(**params)
        revault_dir = Path(params.revault_dir)
        libs_to_pin = set(
            [item.strip() for item in params.pin.split(",") if item.strip()]
        )
        if not libs_to_pin:
            logger.warning("No libs to pin: doing nothing")
            return {}

        packages_dir = revault_dir / "packages"
        for package_json in packages_dir.glob("*/package.json"):
            pick_dep_upgrades_in_package_json(
                revault_dir,
                package_json,
                lambda lib: lib not in libs_to_pin,
            )
        return {}


class RevaultRevertMobileDeps(Action):
    name = "revault-revert-mobile-deps"

    class Params(BaseModel):
        revault_dir: str = Field(alias="revault-dir")

    @override
    def run(self, params, *, context, dry_run):
        params = self.Params(**params)
        revault_dir = Path(params.revault_dir)

        # We need to pay attention to mobile-exclusive dependencies, especially those
        # react-native related. Such libs are very fragile: they don't follow semver
        # and they could just break at any version upgrade.
        #
        # If a lib is also used in a non-mobile package, it is then NOT mobile-exlusive.
        # So it is relatively safe to upgrade.
        deps_in_non_mobile_packages = load_deps_in_non_mobile_packages(revault_dir)
        libs_safe_to_upgrade = set(deps_in_non_mobile_packages.keys())
        pick_dep_upgrades_in_package_json(
            revault_dir,
            revault_dir / "packages/mobile/package.json",
            lambda lib: lib in libs_safe_to_upgrade,
        )

        return {}
