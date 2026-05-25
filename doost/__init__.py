import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _read_version() -> str:
    # Prefer local project metadata during development.
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if pyproject_path.is_file():
        with pyproject_path.open("rb") as pyproject_file:
            project = tomllib.load(pyproject_file)
        return str(project["project"]["version"])

    try:
        return version("Doostan")
    except PackageNotFoundError:
        return "0.0.0"


__version__ = _read_version()
__author__ = "Farhad Fouladi"
