import tomllib
from dataclasses import dataclass
from email.utils import getaddresses
from importlib.metadata import PackageNotFoundError, metadata, version
from pathlib import Path


@dataclass(frozen=True)
class ProjectMetadata:
    version: str
    author_names: tuple[str, ...]


def _dedupe_names(names: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(name for name in names if name))


def _read_pyproject_metadata() -> ProjectMetadata | None:
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if not pyproject_path.is_file():
        return None

    with pyproject_path.open("rb") as pyproject_file:
        project = tomllib.load(pyproject_file)["project"]

    author_names = _dedupe_names([str(author["name"]) for author in project.get("authors", []) if "name" in author])
    return ProjectMetadata(
        version=str(project["version"]),
        author_names=author_names,
    )


def _read_installed_metadata() -> ProjectMetadata:
    try:
        installed_version = version("Doostan")
        package_metadata = metadata("Doostan")
    except PackageNotFoundError:
        return ProjectMetadata(version="0.0.0", author_names=())

    author_names = _dedupe_names([name for name, _email in getaddresses(package_metadata.get_all("Author-email", []))])
    if not author_names:
        author_names = _dedupe_names(package_metadata.get_all("Author", []))

    return ProjectMetadata(
        version=installed_version,
        author_names=author_names,
    )


def read_project_metadata() -> ProjectMetadata:
    if project_metadata := _read_pyproject_metadata():
        return project_metadata
    return _read_installed_metadata()
