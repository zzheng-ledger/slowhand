import os
from pathlib import Path

from pydantic import BaseModel, SecretStr
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

_BASE_DIR = Path(__file__).parent.parent.parent.absolute()


class GithubSettings(BaseModel):
    token: SecretStr | None = None


class JiraSettings(BaseModel):
    server: str | None = None
    email: str | None = None
    api_token: SecretStr | None = None


class Settings(BaseSettings):
    debug: bool = False
    user_jobs_dirs: list[Path] = []
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
                json_file=Path.home() / ".slowhand.json",
            ),
        )

    @property
    def jobs_dirs(self) -> list[Path]:
        return self.user_jobs_dirs + [_BASE_DIR / "jobs"]


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
