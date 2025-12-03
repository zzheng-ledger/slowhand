from abc import ABC, abstractmethod
from slowhand.context import Context
from slowhand.utils import random_name

ActionParams = dict[str, None | str | int | bool]

class Action(ABC):
    name: str = "unknown"  # subclass must override this

    @abstractmethod
    def __init__(self, id: str | None) -> None:
        assert self.__class__.name != "unknown"
        self.id = id or random_name(self.__class__.name)

    @abstractmethod
    def run(self, params: ActionParams, *, context: Context):
        pass
