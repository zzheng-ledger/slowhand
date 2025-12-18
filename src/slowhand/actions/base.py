from abc import ABC, abstractmethod

from slowhand.context import Context

ActionParams = dict[str, None | str | int | bool]


class Action(ABC):
    name: str = "unknown"  # subclass must override this

    @abstractmethod
    def run(
        self, params: ActionParams, *, context: Context, dry_run: bool
    ) -> dict[str, str | None]:
        pass
