import os
from pathlib import Path
from typing import Generator
import pytest

_BASE_DIR = Path(__file__).parent.parent.absolute()

@pytest.fixture
def project_dir() -> Generator[Path]:
    yield _BASE_DIR
