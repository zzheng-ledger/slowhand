import os
from pathlib import Path

from pydantic import BaseModel, SecretStr
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

_SETTINGS_FILE = Path.home() / ".slowhand.json"

class GithubSettings(BaseModel):
    token: SecretStr | None = None

    @property
    def exclude(self) -> dict[str, bool]:
        return {"token": True}


class JiraSettings(BaseModel):
    server: str | None = None
    email: str | None = None
    api_token: SecretStr | None = None

    @property
    def exclude(self) -> dict[str, bool]:
        return {"api_token": True}


class Settings(BaseSettings):
    debug: bool = False
    jobs_dirs: list[Path] = []
    github: GithubSettings = GithubSettings()
    jira: JiraSettings = JiraSettings()

    model_config = SettingsConfigDict(
        env_prefix="SLOWHAND_",
        env_nested_delimiter="_",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            JsonConfigSettingsSource(
                settings_cls,
                json_file=_SETTINGS_FILE,
            ),
        )

    def save(self) -> str:
        text = self.model_dump_json(
            exclude={
                "debug": True,
                "github": self.github.exclude,
                "jira": self.jira.exclude,
            },
            indent=2,
        )
        _SETTINGS_FILE.write_text(text)
        return str(_SETTINGS_FILE)


def _load_settings() -> Settings:
    settings = Settings()

    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        settings.github.token = SecretStr(github_token)

    jira_api_token = os.environ.get("JIRA_API_TOKEN")
    if jira_api_token:
        settings.jira.api_token = SecretStr(jira_api_token)

    return settings


settings = _load_settings()
