from pathlib import Path

version_file = Path(__file__).parent / "VERSION"

VERSION = version_file.read_text().strip() if version_file.is_file() else "0.0.0.dev"
