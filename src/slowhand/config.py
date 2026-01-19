import os
from pathlib import Path

from pydantic import BaseModel, SecretStr
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

_APP_USER_DIR = Path.home() / ".slowhand"

_APP_CONFIG_FILE = _APP_USER_DIR / "config.json"


def ensure_app_user_dir() -> Path:
    _APP_USER_DIR.mkdir(parents=True, exist_ok=True)
    return _APP_USER_DIR


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


class SlackSettings(BaseModel):
    api_token: SecretStr | None = None
    my_member_id: str | None = None


class Settings(BaseSettings):
    debug: bool = False
    jobs_dirs: list[Path] = []
    github: GithubSettings = GithubSettings()
    jira: JiraSettings = JiraSettings()
    slack: SlackSettings = SlackSettings()

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
                json_file=_APP_CONFIG_FILE,
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
        _APP_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _APP_CONFIG_FILE.write_text(text)
        return str(_APP_CONFIG_FILE)


def _load_settings() -> Settings:
    settings = Settings()

    # Allow to enable DEBUG mode with a simple env var `DEBUG=1`
    debug = os.environ.get("DEBUG", "").lower()
    if debug in ("1", "true", "on", "yes"):
        settings.debug = True

    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        settings.github.token = SecretStr(github_token)

    jira_api_token = os.environ.get("JIRA_API_TOKEN")
    if jira_api_token:
        settings.jira.api_token = SecretStr(jira_api_token)

    slack_api_token = os.environ.get("SLACK_API_TOKEN")
    if slack_api_token:
        settings.slack.api_token = SecretStr(slack_api_token)

    slack_my_member_id = os.environ.get("SLACK_MY_MEMBER_ID")
    if slack_my_member_id:
        settings.slack.my_member_id = slack_my_member_id

    return settings


settings = _load_settings()
