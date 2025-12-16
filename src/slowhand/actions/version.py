import re
from typing import override

from pydantic import BaseModel, Field

from slowhand.errors import SlowhandException

from .base import Action

VERSION_REGEX = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?$")


def check_non_negative(component: str, value: int) -> int:
    if value < 0:
        raise SlowhandException(f"Invalid {component} version number: {value}")
    return value


class ComputeVersion(Action):
    name = "compute-version"

    class Params(BaseModel):
        input: str = Field(pattern=VERSION_REGEX.pattern)
        add_major: int = Field(0, alias="add-major")
        add_minor: int = Field(0, alias="add-minor")
        add_patch: int = Field(0, alias="add-patch")

    @override
    def run(self, params, *, context):
        params = self.Params(**params)
        match_obj = VERSION_REGEX.match(params.input)
        major = int(match_obj.group("major"))
        minor = int(match_obj.group("minor"))
        patch_raw = match_obj.group("patch")
        patch = int(patch_raw) if patch_raw is not None else None

        major = check_non_negative("major", major + params.add_major)
        minor = check_non_negative("minor", minor + params.add_minor)
        if patch is None:
            if params.add_patch > 0:
                patch = params.add_patch
            elif params.add_patch == 0:
                pass  # keep the `None` value
            else:
                raise SlowhandException(
                    f"Cannot substract patch {patch} from {params.input}"
                )
        else:
            patch = check_non_negative("patch", patch + params.add_patch)

        patch_suffix = f".{patch}" if patch is not None else ""
        result = f"{major}.{minor}{patch_suffix}"
        return {"result": result}
