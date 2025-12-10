from collections.abc import Generator
from pathlib import Path

import pytest

_BASE_DIR = Path(__file__).parent.parent.absolute()


@pytest.fixture
def project_dir() -> Generator[Path]:
    yield _BASE_DIR
