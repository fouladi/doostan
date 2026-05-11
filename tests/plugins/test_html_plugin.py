from datetime import date

from doost.address import Address
from doost.plugins.html_plugin import HTMLPlugin, _AddressHTMLParser


def test_parser_extracts_fields() -> None:
    parser = _AddressHTMLParser()
    parser.feed(
        '<li data-name="Alice" data-email="alice@example.com" data-birthday="1990-01-02" '
        'data-phone="111" data-mobile="211" data-custom="family" data-notes="Primary">Main Street 1</li>'
    )

    assert len(parser.entries) == 1
    entry = parser.entries[0]
    assert entry.name == "Alice"
    assert entry.email == "alice@example.com"
    assert entry.birthday == date(1990, 1, 2)
    assert entry.address == "Main Street 1"
    assert entry.custom == "family"


def test_parser_handles_missing_optional_attributes() -> None:
    parser = _AddressHTMLParser()
    parser.feed('<li data-name="Alice" data-email="alice@example.com">Main Street 1</li>')

    assert len(parser.entries) == 1
    entry = parser.entries[0]
    assert entry.birthday is None
    assert entry.phone == ""
    assert entry.notes == ""


def test_parser_multiple_entries() -> None:
    parser = _AddressHTMLParser()
    html = (
        '<li data-name="Alice" data-email="alice@example.com">One</li>\n'
        '<li data-name="Bob" data-email="bob@example.com">Two</li>\n'
    )
    parser.feed(html)

    assert len(parser.entries) == 2
    assert parser.entries[0].name == "Alice"
    assert parser.entries[1].name == "Bob"


def test_html_import(tmp_path, session_factory, monkeypatch):
    plugin = HTMLPlugin()

    html = (
        '<li data-name="Alice" data-email="alice@example.com" '
        'data-birthday="1990-01-02" data-custom="family">Main Street 1</li>\n'
    )
    input_file = tmp_path / "addresses.html"
    input_file.write_text(html)

    inserted = []

    def fake_insert(session, address):
        inserted.append(address)

    monkeypatch.setattr("doost.plugins.html_plugin.db.insert_address", fake_insert)

    plugin.import_data(input_file, session_factory)

    assert len(inserted) == 1
    assert inserted[0].name == "Alice"
    assert inserted[0].birthday == date(1990, 1, 2)
    assert inserted[0].address == "Main Street 1"


def test_html_import_skips_entry_with_empty_required_field(tmp_path, session_factory, monkeypatch):
    plugin = HTMLPlugin()

    html = '<li data-name="Alice">Main Street 1</li>\n'
    input_file = tmp_path / "bad.html"
    input_file.write_text(html)

    inserted = []

    def fake_insert(session, address):
        inserted.append(address)  # pragma: no cover

    monkeypatch.setattr("doost.plugins.html_plugin.db.insert_address", fake_insert)

    plugin.import_data(input_file, session_factory)

    assert inserted == []


def test_html_import_skips_duplicate(tmp_path, session_factory, monkeypatch):
    plugin = HTMLPlugin()

    html = (
        '<li data-name="Alice" data-email="alice@example.com">One</li>\n'
        '<li data-name="Alice" data-email="alice@example.com">One</li>\n'
    )
    input_file = tmp_path / "dup.html"
    input_file.write_text(html)

    call_count = 0

    def fake_insert(session, address):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise ValueError("duplicate")

    monkeypatch.setattr("doost.plugins.html_plugin.db.insert_address", fake_insert)

    plugin.import_data(input_file, session_factory)

    assert call_count == 2


def test_html_import_skips_invalid_birthday(tmp_path, session_factory, monkeypatch):
    plugin = HTMLPlugin()

    html = '<li data-name="Alice" data-email="alice@example.com" data-birthday="1990-99-99">One</li>\n'
    input_file = tmp_path / "bad-birthday.html"
    input_file.write_text(html)

    inserted = []

    def fake_insert(session, address):
        inserted.append(address)  # pragma: no cover

    monkeypatch.setattr("doost.plugins.html_plugin.db.insert_address", fake_insert)

    plugin.import_data(input_file, session_factory)

    assert inserted == []


def test_html_export(tmp_path):
    plugin = HTMLPlugin()
    addresses = [
        Address(
            id=1,
            name="Alice",
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
            address="Second Street 2",
            phone="",
            mobile="",
            custom="",
            notes="",
        ),
    ]

    out = tmp_path / "addresses.html"
    plugin.export_data(out, addresses)

    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert (
        '<li data-name="Alice" data-email="alice@example.com" data-birthday="1990-01-02" data-phone="111" '
        'data-mobile="211" data-custom="family" data-notes="Primary">Main Street 1</li>'
    ) == lines[0]
    assert (
        '<li data-name="Bob" data-email="bob@example.com" data-birthday="" data-phone="" '
        'data-mobile="" data-custom="" data-notes="">Second Street 2</li>'
    ) == lines[1]


def test_html_export_empty(tmp_path):
    plugin = HTMLPlugin()
    out = tmp_path / "empty.html"
    plugin.export_data(out, [])

    assert out.read_text(encoding="utf-8") == ""
