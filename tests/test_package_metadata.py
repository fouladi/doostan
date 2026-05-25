import tomllib
from pathlib import Path

import doost
from doost import __version__
from doost.metadata import read_project_metadata


def test_package_version_matches_pyproject() -> None:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with pyproject_path.open("rb") as pyproject_file:
        project = tomllib.load(pyproject_file)

    assert __version__ == project["project"]["version"]


def test_package_authors_match_pyproject() -> None:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with pyproject_path.open("rb") as pyproject_file:
        project = tomllib.load(pyproject_file)

    author_names = tuple(author["name"] for author in project["project"]["authors"])

    assert read_project_metadata().author_names == author_names


def test_package_no_longer_exports_author() -> None:
    assert not hasattr(doost, "__author__")
