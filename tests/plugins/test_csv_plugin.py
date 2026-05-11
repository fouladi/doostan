import csv
from datetime import date

from doost.plugins.csv_plugin import CSVPlugin


def test_csv_export(tmp_path):
    plugin = CSVPlugin()

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
        )(),
        type(
            "A",
            (),
            {
                "name": "Bob",
                "email": "bob@example.com",
                "birthday": None,
                "address": "",
                "phone": "",
                "mobile": "",
                "custom": "",
                "notes": "",
            },
        )(),
    ]

    out = tmp_path / "addresses.csv"
    plugin.export_data(out, addresses)

    with out.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert rows == [
        {
            "name": "Alice",
            "email": "alice@example.com",
            "birthday": "1990-01-02",
            "address": "Main Street 1",
            "phone": "111",
            "mobile": "211",
            "custom": "family",
            "notes": "Primary",
        },
        {
            "name": "Bob",
            "email": "bob@example.com",
            "birthday": "",
            "address": "",
            "phone": "",
            "mobile": "",
            "custom": "",
            "notes": "",
        },
    ]


def test_csv_import(tmp_path, session_factory, monkeypatch):
    plugin = CSVPlugin()

    csv_file = tmp_path / "addresses.csv"
    csv_file.write_text(
        (
            "name,email,birthday,address,phone,mobile,custom,notes\n"
            "Alice,alice@example.com,1990-01-02,Main Street 1,111,211,family,Primary\n"
            "Bob,bob@example.com,,,,222,work,\n"
        ),
        encoding="utf-8",
    )

    inserted = []

    def fake_insert(session, address):
        inserted.append(address)

    monkeypatch.setattr("doost.plugins.csv_plugin.db.insert_address", fake_insert)

    plugin.import_data(csv_file, session_factory)

    assert len(inserted) == 2
    assert inserted[0].name == "Alice"
    assert inserted[0].birthday == date(1990, 1, 2)
    assert inserted[1].mobile == "222"


def test_csv_import_skips_duplicate(tmp_path, session_factory, monkeypatch):
    plugin = CSVPlugin()

    csv_file = tmp_path / "addresses.csv"
    csv_file.write_text(
        (
            "name,email,birthday,address,phone,mobile,custom,notes\n"
            "Alice,alice@example.com,1990-01-02,Main Street 1,111,211,family,Primary\n"
            "Alice,alice@example.com,1990-01-02,Main Street 1,111,211,family,Primary\n"
        ),
        encoding="utf-8",
    )

    call_count = 0

    def fake_insert(session, address):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise ValueError("duplicate")

    monkeypatch.setattr("doost.plugins.csv_plugin.db.insert_address", fake_insert)

    plugin.import_data(csv_file, session_factory)
    assert call_count == 2


def test_csv_import_skips_row_with_missing_fields(tmp_path, session_factory, monkeypatch):
    plugin = CSVPlugin()

    csv_file = tmp_path / "bad.csv"
    csv_file.write_text("name,address\nOnly Name,Somewhere\n", encoding="utf-8")

    inserted = []

    def fake_insert(session, address):
        inserted.append(address)  # pragma: no cover

    monkeypatch.setattr("doost.plugins.csv_plugin.db.insert_address", fake_insert)

    plugin.import_data(csv_file, session_factory)

    assert inserted == []
