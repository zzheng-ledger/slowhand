from abc import ABC, abstractmethod
from slowhand.context import Context
from slowhand.utils import random_name

ActionParams = dict[str, None | str | int | bool]

class Action(ABC):
    name: str = "unknown"  # subclass must override this

    @abstractmethod
    def run(self, params: ActionParams, *, context: Context) -> dict[str, str]:
        pass
