import json
import re
from pathlib import Path
from typing import Literal, cast, override

import yaml
from jsonpath_ng import parse  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

from slowhand.errors import SlowhandException
from slowhand.logging import get_logger

from .base import Action

logger = get_logger(__name__)


TargetEnv = Literal["stg", "ppr", "prd"]
REVAULT_PACKAGES = ("api", "backoffice", "onboarding", "notifier", "web")
RELEASE_VERSION_PATTERN = r"^\d+\.\d+$"
TARGET_REVISION_RE = re.compile(
    r"targetRevision: ([a-zA-Z]+)@([0-9]+\.[0-9]+\.[0-9]+)"
)

QUOTED_REVAULT_VALUE_FILE_REGEX = re.compile(
    '"'
    + re.escape("$values/deploy/platform-2220-cluster/applications/vault/releases/")
    + r"revault-(?P<version>\d+\.\d+)\.yaml"
    + '"'
)


def get_releases_dir(sre_argocd_dir: str) -> Path:
    return (
        Path(sre_argocd_dir)
        / "deploy"
        / "platform-2220-cluster"
        / "applications"
        / "vault"
        / "releases"
    )


def parse_version(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def get_prd_version(sre_argocd_dir: str) -> str:
    prd_yaml = get_deploy_yaml_files(sre_argocd_dir, "prd")["prd"]
    return find_revault_version(prd_yaml)


def assert_release_not_in_prod(release_version: str, prd_version: str) -> None:
    if parse_version(release_version) <= parse_version(prd_version):
        raise SlowhandException(
            f"Release {release_version} is already in prod (prd={prd_version})"
        )


def _patch_package_in_preset(content: str, pkg: str, version: str) -> str:
    service: str | None = None
    lines_out: list[str] = []
    for line in content.splitlines(keepends=True):
        tr_match = TARGET_REVISION_RE.search(line)
        if tr_match:
            service = f"{tr_match.group(1)}@{tr_match.group(2)}"
            if service.startswith(f"{pkg}@"):
                line = TARGET_REVISION_RE.sub(
                    rf"targetRevision: {tr_match.group(1)}@{version}",
                    line,
                    count=1,
                )
            lines_out.append(line)
            continue
        if re.search(r"tag: ([0-9]+\.[0-9]+\.[0-9]+)", line) and service:
            if service.startswith(f"{pkg}@"):
                line = re.sub(
                    r"tag: ([0-9]+\.[0-9]+\.[0-9]+)",
                    f"tag: {version}",
                    line,
                    count=1,
                )
                service = None
        lines_out.append(line)
    return "".join(lines_out)


def patch_release_file(
    preset_path: Path, revault_dir: Path, *, release_version: str
) -> None:
    if not preset_path.is_file():
        raise SlowhandException(f"Release file not found: {preset_path}")

    content = preset_path.read_text()
    for pkg in REVAULT_PACKAGES:
        package_json = revault_dir / "packages" / pkg / "package.json"
        if not package_json.is_file():
            raise SlowhandException(f"Package not found: {package_json}")
        pkg_version = json.loads(package_json.read_text())["version"]
        content = _patch_package_in_preset(content, pkg, pkg_version)
        logger.info("Patched package '%s' to version '%s'", pkg, pkg_version)
    preset_path.write_text(content)
    logger.info("Patched release file: revault-%s.yaml", release_version)


def get_deploy_yaml_files(
    sre_argocd_dir: str, target_env: TargetEnv
) -> dict[str, Path]:
    vault_dir = (
        Path(sre_argocd_dir)
        / "deploy"
        / "platform-2220-cluster"
        / "applications"
        / "vault"
    )
    non_prod_dir = vault_dir / "core" / "non-prod"

    yaml_files: dict[str, Path]
    if target_env == "stg":
        yaml_files = {
            "next": non_prod_dir / "next.yaml",
            "load": non_prod_dir / "load.yaml",
            "ppr2": non_prod_dir / "ppr2.yaml",
        }
    elif target_env == "ppr":
        yaml_files = {"ppr": non_prod_dir / "ppr.yaml"}
    elif target_env == "prd":
        yaml_files = {"prd": vault_dir / "prd.yaml"}
    else:
        raise SlowhandException(f"Invalid target env: {target_env}")
    return yaml_files


def find_revault_version(yaml_file: Path) -> str:
    if not yaml_file.is_file():
        raise SlowhandException(
            f"Cannot find revault version in {yaml_file}: not a file"
        )
    with yaml_file.open("r") as f:
        data = yaml.safe_load(f)

    versions = []
    for match in parse("spec.sources[*].helm.valueFiles[*]").find(data):
        value = cast(str, match.value)
        match = QUOTED_REVAULT_VALUE_FILE_REGEX.match(f'"{value}"')
        if match:
            versions.append(match.group("version"))

    if len(versions) != 1:
        raise SlowhandException(
            f"Found {len(versions)} revault version(s) in {yaml_file}"
        )
    return versions[0]


def update_revault_version(yaml_file: Path, from_version: str, to_version: str) -> None:
    def replace_version(m: re.Match[str]) -> str:
        matched_version = m.group("version")
        if matched_version != from_version:
            raise SlowhandException(
                f"Unexpected revault version in {yaml_file}: {matched_version}"
            )
        return m.group(0).replace(f"revault-{from_version}", f"revault-{to_version}")

    content = yaml_file.read_text()
    content, num_replaced = QUOTED_REVAULT_VALUE_FILE_REGEX.subn(
        replace_version, content
    )
    if num_replaced != 1:
        raise SlowhandException(f"Expected 1 occurrence but got {num_replaced}")
    yaml_file.write_text(content)


class RevaultFindDeployVersions(Action):
    name = "revault-find-deploy-versions"

    class Params(BaseModel):
        sre_argocd_dir: str = Field(alias="sre-argocd-dir")

    @override
    def run(self, params, *, context, dry_run):
        params = self.Params(**params)
        stg_yaml_files = get_deploy_yaml_files(params.sre_argocd_dir, "stg")
        ppr_yaml_files = get_deploy_yaml_files(params.sre_argocd_dir, "ppr")
        prd_yaml_files = get_deploy_yaml_files(params.sre_argocd_dir, "prd")

        def find_single_version(yaml_files: dict[str, Path]) -> str:
            versions = {k: find_revault_version(v) for k, v in yaml_files.items()}
            if len(set(versions.values())) != 1:
                raise SlowhandException(
                    "Inconsistent revault versions: "
                    + ", ".join([f"{k}={v}" for k, v in versions.items()])
                )
            return next(iter(versions.values()))

        return {
            "stg": find_single_version(stg_yaml_files),
            "ppr": find_single_version(ppr_yaml_files),
            "prd": find_single_version(prd_yaml_files),
        }


class RevaultUpdateDeployVersions(Action):
    name = "revault-update-deploy-versions"

    class Params(BaseModel):
        sre_argocd_dir: str = Field(alias="sre-argocd-dir")
        target_env: TargetEnv = Field(alias="target-env")
        from_version: str = Field(alias="from-version")
        to_version: str = Field(alias="to-version")

    @override
    def run(self, params, *, context, dry_run):
        params = self.Params(**params)
        yaml_files = get_deploy_yaml_files(params.sre_argocd_dir, params.target_env)
        logger.info(
            "Updating revault version: %s -> %s", params.from_version, params.to_version
        )
        for yaml_file in yaml_files.values():
            update_revault_version(
                yaml_file,
                from_version=params.from_version,
                to_version=params.to_version,
            )
        return {}


class RevaultPatchReleaseFile(Action):
    name = "revault-patch-release-file"

    class Params(BaseModel):
        sre_argocd_dir: str = Field(alias="sre-argocd-dir")
        revault_dir: str = Field(alias="revault-dir")
        version: str = Field(pattern=RELEASE_VERSION_PATTERN)

    @override
    def run(self, params, *, context, dry_run):
        params = self.Params(**params)
        prd_version = get_prd_version(params.sre_argocd_dir)
        assert_release_not_in_prod(params.version, prd_version)
        preset_path = get_releases_dir(params.sre_argocd_dir) / (
            f"revault-{params.version}.yaml"
        )
        patch_release_file(
            preset_path,
            Path(params.revault_dir),
            release_version=params.version,
        )
        return {"version": params.version, "prd": prd_version}
