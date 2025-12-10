from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

_BASE_DIR = Path(__file__).parent.parent.parent.absolute()


class Config(BaseSettings):
    debug: bool = False
    user_jobs_dirs: list[Path] = []

    model_config = SettingsConfigDict(
        json_file=str(Path.home() / ".slowhand.json"),
        json_file_encoding="utf-8",
        env_prefix="SLOWHAND_",
        env_nested_delimiter="__",
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
            JsonConfigSettingsSource(settings_cls),
            dotenv_settings,
            env_settings,
        )

    @property
    def jobs_dirs(self) -> list[Path]:
        return self.user_jobs_dirs + [_BASE_DIR / "jobs"]


config = Config()
