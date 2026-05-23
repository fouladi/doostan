from datetime import date

from doost.address import Address
from doost.plugins.vcard_plugin import VCardPlugin, _card_to_address


def test_vcard_parser_extracts_fields() -> None:
    entry = _card_to_address(
        [
            "FN:Alice Example",
            "N:Example;Alice;;;",
            "BDAY:19900102",
            "ADR:;;Main Street 1;;Frankfurt;;60322;",
            "TEL;WORK:999",
            "TEL;HOME:111",
            "TEL;CELL:211",
            "EMAIL;INTERNET:alice@example.com",
            "EMAIL;INTERNET:alias@example.com",
            "X-DOOST-CUSTOM:family",
            r"NOTE:Primary\nContact",
        ]
    )

    assert entry.name == "Alice Example"
    assert entry.email == "alice@example.com"
    assert entry.birthday == date(1990, 1, 2)
    assert entry.address == "Main Street 1, Frankfurt, 60322"
    assert entry.phone == "111"
    assert entry.mobile == "211"
    assert entry.custom == "family"
    assert entry.notes == "Primary\nContact"


def test_vcard_parser_unescapes_semicolons_in_address() -> None:
    entry = _card_to_address(
        [
            r"ADR:;;Main\; Street 1;;;;",
            "EMAIL;INTERNET:alice@example.com",
            "FN:Alice Example",
        ]
    )

    assert entry.address == "Main; Street 1"


def test_vcard_parser_uses_structured_name_when_fn_missing() -> None:
    entry = _card_to_address(
        [
            "N:Example;Alice;;;",
            "EMAIL;INTERNET:alice@example.com",
        ]
    )

    assert entry.name == "Alice Example"
    assert entry.email == "alice@example.com"


def test_vcard_import_addressbook_style(tmp_path, session_factory, monkeypatch):
    plugin = VCardPlugin()

    input_file = tmp_path / "addressbook.vcard"
    input_file.write_text(
        (
            "BEGIN:VCARD\n"
            "FN:Alice Example\n"
            "N:Example;Alice\n"
            "ADR:;;Main Street 1;;Frankfurt;;60322;\n"
            "TEL;HOME:111\n"
            "TEL;WORK:999\n"
            "TEL;CELL:211\n"
            "EMAIL;INTERNET:alice@example.com\n"
            "EMAIL;INTERNET:alias@example.com\n"
            "NOTE:Primary\n"
            "END:VCARD\n\n"
            "BEGIN:VCARD\n"
            "FN:No Email\n"
            "N:Email;No\n"
            "END:VCARD\n"
        ),
        encoding="utf-8",
    )

    inserted = []

    def fake_insert(session, address):
        inserted.append(address)

    monkeypatch.setattr("doost.plugins.vcard_plugin.db.insert_address", fake_insert)

    plugin.import_data(input_file, session_factory)

    assert len(inserted) == 1
    assert inserted[0].name == "Alice Example"
    assert inserted[0].email == "alice@example.com"
    assert inserted[0].phone == "111"
    assert inserted[0].mobile == "211"
    assert inserted[0].address == "Main Street 1, Frankfurt, 60322"


def test_vcard_import_skips_duplicate(tmp_path, session_factory, monkeypatch):
    plugin = VCardPlugin()

    input_file = tmp_path / "dup.vcard"
    input_file.write_text(
        (
            "BEGIN:VCARD\n"
            "FN:Alice Example\n"
            "EMAIL;INTERNET:alice@example.com\n"
            "END:VCARD\n\n"
            "BEGIN:VCARD\n"
            "FN:Alice Example\n"
            "EMAIL;INTERNET:alice@example.com\n"
            "END:VCARD\n"
        ),
        encoding="utf-8",
    )

    call_count = 0

    def fake_insert(session, address):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise ValueError("duplicate")

    monkeypatch.setattr("doost.plugins.vcard_plugin.db.insert_address", fake_insert)

    plugin.import_data(input_file, session_factory)

    assert call_count == 2


def test_vcard_import_skips_invalid_birthday(tmp_path, session_factory, monkeypatch):
    plugin = VCardPlugin()

    input_file = tmp_path / "bad.vcard"
    input_file.write_text(
        (
            "BEGIN:VCARD\n"
            "FN:Alice Example\n"
            "EMAIL;INTERNET:alice@example.com\n"
            "BDAY:1990-99-99\n"
            "END:VCARD\n"
        ),
        encoding="utf-8",
    )

    inserted = []

    def fake_insert(session, address):
        inserted.append(address)  # pragma: no cover

    monkeypatch.setattr("doost.plugins.vcard_plugin.db.insert_address", fake_insert)

    plugin.import_data(input_file, session_factory)

    assert inserted == []


def test_vcard_export(tmp_path):
    plugin = VCardPlugin()
    addresses = [
        Address(
            id=1,
            name="Alice Example",
            email="alice@example.com",
            birthday=date(1990, 1, 2),
            address="Main Street 1",
            phone="111",
            mobile="211",
            custom="family",
            notes="Primary",
        ),
        Address(
            id=2,
            name="Bob",
            email="bob@example.com",
            birthday=None,
            address="",
            phone="",
            mobile="",
            custom="",
            notes="",
        ),
    ]

    out = tmp_path / "addresses.vcard"
    plugin.export_data(out, addresses)

    assert out.read_text(encoding="utf-8") == (
        "BEGIN:VCARD\n"
        "VERSION:3.0\n"
        "FN:Alice Example\n"
        "N:Example;Alice;;;\n"
        "EMAIL;INTERNET:alice@example.com\n"
        "BDAY:1990-01-02\n"
        "ADR:;;Main Street 1;;;;\n"
        "TEL;HOME:111\n"
        "TEL;CELL:211\n"
        "X-DOOST-CUSTOM:family\n"
        "NOTE:Primary\n"
        "END:VCARD\n\n"
        "BEGIN:VCARD\n"
        "VERSION:3.0\n"
        "FN:Bob\n"
        "N:;Bob;;;\n"
        "EMAIL;INTERNET:bob@example.com\n"
        "END:VCARD\n"
    )


def test_vcard_export_empty(tmp_path):
    plugin = VCardPlugin()
    out = tmp_path / "empty.vcard"
    plugin.export_data(out, [])

    assert out.read_text(encoding="utf-8") == ""
