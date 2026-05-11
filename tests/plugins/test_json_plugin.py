import json
from datetime import date

import pytest

from doost.plugins.json_plugin import JSONPlugin


def test_json_export(tmp_path):
    plugin = JSONPlugin()

    addresses: list = [
        type(
            "A",
            (),
            {
                "name": "Alice",
                "email": "alice@example.com",
                "birthday": date(1990, 1, 2),
                "address": "Main Street 1",
                "phone": "111",
                "mobile": "211",
                "custom": "family",
                "notes": "Primary",
            },
        )()
    ]

    out = tmp_path / "addresses.json"
    plugin.export_data(out, addresses)

    data = json.loads(out.read_text())
    assert data == [
        {
            "name": "Alice",
            "email": "alice@example.com",
            "birthday": "1990-01-02",
            "address": "Main Street 1",
            "phone": "111",
            "mobile": "211",
            "custom": "family",
            "notes": "Primary",
        }
    ]


def test_json_import(tmp_path, session_factory, monkeypatch):
    plugin = JSONPlugin()

    input_file = tmp_path / "in.json"
    input_file.write_text(
        json.dumps(
            [
                {
                    "name": "Alice",
                    "email": "alice@example.com",
                    "birthday": "1990-01-02",
                    "address": "Main Street 1",
                    "phone": "111",
                    "mobile": "211",
                    "custom": "family",
                    "notes": "Primary",
                }
            ]
        )
    )

    inserted = []

    def fake_insert(session, address):
        inserted.append(address)

    monkeypatch.setattr("doost.plugins.json_plugin.db.insert_address", fake_insert)

    plugin.import_data(input_file, session_factory)

    assert len(inserted) == 1
    assert inserted[0].name == "Alice"
    assert inserted[0].birthday == date(1990, 1, 2)


def test_json_import_raises_on_non_list(tmp_path, session_factory):
    plugin = JSONPlugin()

    input_file = tmp_path / "bad.json"
    input_file.write_text('{"name": "Not a list"}')

    with pytest.raises(ValueError, match="Invalid JSON format"):
        plugin.import_data(input_file, session_factory)


def test_json_import_skips_entry_with_missing_key(tmp_path, session_factory, monkeypatch):
    plugin = JSONPlugin()

    input_file = tmp_path / "missing.json"
    input_file.write_text(
        json.dumps(
            [
                {"name": "Valid", "email": "valid@example.com"},
                {"name": "No Email"},
            ]
        )
    )

    inserted = []

    def fake_insert(session, address):
        inserted.append(address)

    monkeypatch.setattr("doost.plugins.json_plugin.db.insert_address", fake_insert)

    plugin.import_data(input_file, session_factory)

    assert len(inserted) == 1
    assert inserted[0].name == "Valid"


def test_json_import_skips_duplicate(tmp_path, session_factory, monkeypatch):
    plugin = JSONPlugin()

    input_file = tmp_path / "dup.json"
    input_file.write_text(
        json.dumps(
            [
                {"name": "First", "email": "person@example.com"},
                {"name": "Duplicate", "email": "person@example.com"},
            ]
        )
    )

    call_count = 0

    def fake_insert(session, address):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise ValueError("duplicate")

    monkeypatch.setattr("doost.plugins.json_plugin.db.insert_address", fake_insert)

    plugin.import_data(input_file, session_factory)

    assert call_count == 2


def test_json_export_empty(tmp_path):
    plugin = JSONPlugin()
    out = tmp_path / "empty.json"
    plugin.export_data(out, [])

    data = json.loads(out.read_text())
    assert data == []
