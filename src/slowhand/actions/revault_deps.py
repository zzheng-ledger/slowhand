import difflib
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import override

from pydantic import BaseModel, Field

from slowhand.errors import SlowhandException
from slowhand.utils import run_command

from .base import Action

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


def load_non_mobile_deps(revault_dir: Path) -> dict[str, str]:
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


def upgrade_deps_selectively(
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


class RevaultRevertMobileDeps(Action):
    name = "revault-revert-mobile-deps"

    class Params(BaseModel):
        revault_dir: str = Field(alias="revault-dir")

    @override
    def run(self, params, *, context):
        params = self.Params(**params)
        revault_dir = Path(params.revault_dir)

        non_mobile_deps = load_non_mobile_deps(revault_dir)

        mobile_package_json = revault_dir / "packages" / "mobile" / "package.json"
        old_text = run_command(
            "git",
            "show",
            f"HEAD:{mobile_package_json.relative_to(revault_dir)}",
            cwd=revault_dir,
        )
        new_text = mobile_package_json.read_text()

        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()
        diff = difflib.SequenceMatcher(None, old_lines, new_lines)
        for tag, i1, i2, j1, j2 in diff.get_opcodes():
            if tag == "equal":
                continue
            elif tag == "replace":
                lines = upgrade_deps_selectively(
                    old_lines[i1:i2],
                    new_lines[j1:j2],
                    set(non_mobile_deps.keys()),
                )
                # Update the new lines in-place
                new_lines[i1:i2] = lines
                """
                old_deps = parse_deps(old_lines[i1:i2])
                new_deps = parse_deps(new_lines[j1:j2])

                updated_libs = set(old_deps.keys())
                if updated_libs != set(new_deps.keys()):
                    raise Exception(
                        "Updated libs do not match: "
                        + ", ".join(updated_libs)
                        + " vs. "
                        + ", ".join(new_deps.keys())
                    )

                deps = {
                    # Take the new version if the lib is also used in other non-mobile packages.
                    # If the lib is only used by mobile, keep the old version.
                    lib: new_deps[lib] if lib in non_mobile_deps else old_deps[lib]
                    for lib in updated_libs
                }
                for i in range(j1, j2):
                    new_lines[i] = apply_dep(new_lines[i], deps)
                """
            else:
                raise SlowhandException(f"Unexpected diff tag: {tag}")

        mobile_package_json.write_text("\n".join(new_lines))
