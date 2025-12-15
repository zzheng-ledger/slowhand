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

QUOTED_REVAULT_VALUE_FILE_REGEX = re.compile(
    '"'
    + re.escape("$values/deploy/platform-2220-cluster/applications/vault/releases/")
    + r"revault-(?P<version>\d+\.\d+)\.yaml"
    + '"'
)


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
            "qa": non_prod_dir / "qa.yaml",
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
    def run(self, params, *, context):
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
    def run(self, params, *, context):
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
