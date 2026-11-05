"""Focused unit tests for small, pure code paths that lacked coverage.

Targets:
- doost.address.parse_birthday empty/whitespace branch
- doost.metadata pyproject-missing fallback and installed-metadata parsing
- doost.plugins.io.report_progress with a real callback
- doost.plugins.json_plugin._string_value non-mapping / required branches
"""

from __future__ import annotations

from datetime import date

import pytest

from doost import metadata
from doost.address import parse_birthday
from doost.metadata import ProjectMetadata, _read_installed_metadata, _read_pyproject_metadata, read_project_metadata
from doost.plugins.io import report_progress
from doost.plugins.json_plugin import _string_value


def test_parse_birthday_none_returns_none() -> None:
    assert parse_birthday(None) is None


def test_parse_birthday_whitespace_returns_none() -> None:
    assert parse_birthday("   ") is None


def test_parse_birthday_valid() -> None:
    assert parse_birthday("1990-01-02") == date(1990, 1, 2)


def test_report_progress_invokes_callback() -> None:
    events: list[tuple[int, int | None]] = []
    report_progress(lambda completed, total: events.append((completed, total)), 2, 5)
    assert events == [(2, 5)]


def test_report_progress_noop_without_callback() -> None:
    # Should simply return without raising.
    report_progress(None, 1, 1)


def test_string_value_non_mapping_optional_returns_empty() -> None:
    assert _string_value(["not", "a", "mapping"], "name") == ""


def test_string_value_non_mapping_required_raises() -> None:
    with pytest.raises(ValueError, match="Invalid value for name"):
        _string_value("not-a-mapping", "name", required=True)


def test_string_value_non_string_required_raises() -> None:
    with pytest.raises(ValueError, match="Invalid value for age"):
        _string_value({"age": 42}, "age", required=True)


def test_string_value_non_string_optional_returns_empty() -> None:
    assert _string_value({"age": 42}, "age") == ""


def test_string_value_returns_matching_string() -> None:
    assert _string_value({"name": "Ada"}, "name") == "Ada"


def test_read_pyproject_metadata_missing_file_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("doost.metadata.Path.is_file", lambda self: False)
    assert _read_pyproject_metadata() is None


def test_read_project_metadata_falls_back_to_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = ProjectMetadata(version="9.9.9", author_names=("Installed Author",))
    monkeypatch.setattr(metadata, "_read_pyproject_metadata", lambda: None)
    monkeypatch.setattr(metadata, "_read_installed_metadata", lambda: sentinel)
    assert read_project_metadata() is sentinel


def test_read_installed_metadata_package_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_not_found(_name: str) -> str:
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(metadata, "version", raise_not_found)
    result = _read_installed_metadata()
    assert result == ProjectMetadata(version="0.0.0", author_names=())


def test_read_installed_metadata_uses_author_email(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeMetadata:
        def __init__(self, mapping: dict[str, list[str]]) -> None:
            self._mapping = mapping

        def get_all(self, key: str, default: list[str] | None = None) -> list[str]:
            return self._mapping.get(key, default or [])

    monkeypatch.setattr(metadata, "version", lambda _name: "2.3.4")
    monkeypatch.setattr(
        metadata,
        "metadata",
        lambda _name: FakeMetadata({"Author-email": ["Grace Hopper <grace@example.com>"]}),
    )
    result = _read_installed_metadata()
    assert result.version == "2.3.4"
    assert result.author_names == ("Grace Hopper",)


def test_read_installed_metadata_falls_back_to_author_field(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeMetadata:
        def __init__(self, mapping: dict[str, list[str]]) -> None:
            self._mapping = mapping

        def get_all(self, key: str, default: list[str] | None = None) -> list[str]:
            return self._mapping.get(key, default or [])

    monkeypatch.setattr(metadata, "version", lambda _name: "2.3.4")
    monkeypatch.setattr(
        metadata,
        "metadata",
        lambda _name: FakeMetadata({"Author": ["Katherine Johnson"]}),
    )
    result = _read_installed_metadata()
    assert result.author_names == ("Katherine Johnson",)
