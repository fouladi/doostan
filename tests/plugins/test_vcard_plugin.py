from datetime import date

from doost.address import Address
from doost.plugins.vcard_plugin import VCardPlugin, _card_to_address


def test_vcard_parser_extracts_rfc_6350_fields() -> None:
    entry = _card_to_address(
        [
            "VERSION:4.0",
            "FN:Alice Example",
            "N:Example;Alice;;;",
            "BDAY:19900102",
            "ADR;TYPE=home:;;Main Street 1;Frankfurt;;60322;Germany",
            'TEL;VALUE=uri;TYPE="voice,home":tel:+49-111',
            "TEL;VALUE=text;TYPE=cell:211",
            "EMAIL;PREF=1:alice@example.com",
            "EMAIL:alias@example.com",
            "CATEGORIES:family,client",
            r"NOTE:Primary\nContact",
        ]
    )

    assert entry.name == "Alice Example"
    assert entry.email == "alice@example.com"
    assert entry.birthday == date(1990, 1, 2)
    assert entry.address == "Main Street 1, Frankfurt, 60322, Germany"
    assert entry.phone == "+49-111"
    assert entry.mobile == "211"
    assert entry.custom == "family;client"
    assert entry.notes == "Primary\nContact"


def test_vcard_parser_unescapes_semicolons_in_address() -> None:
    entry = _card_to_address(
        [
            r"ADR;TYPE=home:;;Main\; Street 1;;;;",
            "EMAIL:alice@example.com",
            "FN:Alice Example",
        ]
    )

    assert entry.address == "Main; Street 1"


def test_vcard_parser_uses_structured_name_when_fn_missing() -> None:
    entry = _card_to_address(
        [
            "N:Example;Alice;;;",
            "EMAIL:alice@example.com",
        ]
    )

    assert entry.name == "Alice Example"
    assert entry.email == "alice@example.com"


def test_vcard_import_rfc_6350(tmp_path, session_factory, monkeypatch):
    plugin = VCardPlugin()

    input_file = tmp_path / "addresses.vcf"
    input_file.write_text(
        (
            "BEGIN:VCARD\r\n"
            "VERSION:4.0\r\n"
            "FN:Alice Example\r\n"
            "N:Example;Alice;;;\r\n"
            "ADR;TYPE=home:;;Main Street 1;Frankfurt;;60322;Germany\r\n"
            "TEL;VALUE=text;TYPE=home:111\r\n"
            "TEL;VALUE=text;TYPE=cell:211\r\n"
            "EMAIL:alice@example.com\r\n"
            "CATEGORIES:family,client\r\n"
            "NOTE:Primary\r\n"
            "END:VCARD\r\n"
            "BEGIN:VCARD\r\n"
            "VERSION:4.0\r\n"
            "FN:No Email\r\n"
            "N:Email;No;;;\r\n"
            "END:VCARD\r\n"
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
    assert inserted[0].custom == "family;client"
    assert inserted[0].address == "Main Street 1, Frankfurt, 60322, Germany"


def test_vcard_import_accepts_legacy_sample_style(tmp_path, session_factory, monkeypatch):
    plugin = VCardPlugin()

    input_file = tmp_path / "addressbook.vcard"
    input_file.write_text(
        (
            "BEGIN:VCARD\r\n"
            "FN:Alice Example\r\n"
            "N:Example;Alice\r\n"
            "ADR:;;Main Street 1;;Frankfurt;;60322;\r\n"
            "TEL;HOME:111\r\n"
            "TEL;CELL:211\r\n"
            "EMAIL;INTERNET:alice@example.com\r\n"
            "X-DOOST-CUSTOM:family\r\n"
            "END:VCARD\r\n"
        ),
        encoding="utf-8",
    )

    inserted = []

    def fake_insert(session, address):
        inserted.append(address)

    monkeypatch.setattr("doost.plugins.vcard_plugin.db.insert_address", fake_insert)

    plugin.import_data(input_file, session_factory)

    assert len(inserted) == 1
    assert inserted[0].phone == "111"
    assert inserted[0].mobile == "211"
    assert inserted[0].custom == "family"


def test_vcard_import_accepts_text_birthday_as_missing(tmp_path, session_factory, monkeypatch):
    plugin = VCardPlugin()

    input_file = tmp_path / "birthday-text.vcf"
    input_file.write_text(
        (
            "BEGIN:VCARD\r\n"
            "VERSION:4.0\r\n"
            "FN:Alice Example\r\n"
            "EMAIL:alice@example.com\r\n"
            "BDAY;VALUE=text:circa 1990\r\n"
            "END:VCARD\r\n"
        ),
        encoding="utf-8",
    )

    inserted = []

    def fake_insert(session, address):
        inserted.append(address)

    monkeypatch.setattr("doost.plugins.vcard_plugin.db.insert_address", fake_insert)

    plugin.import_data(input_file, session_factory)

    assert len(inserted) == 1
    assert inserted[0].birthday is None


def test_vcard_import_skips_duplicate(tmp_path, session_factory, monkeypatch):
    plugin = VCardPlugin()

    input_file = tmp_path / "dup.vcf"
    input_file.write_text(
        (
            "BEGIN:VCARD\r\n"
            "VERSION:4.0\r\n"
            "FN:Alice Example\r\n"
            "EMAIL:alice@example.com\r\n"
            "END:VCARD\r\n"
            "BEGIN:VCARD\r\n"
            "VERSION:4.0\r\n"
            "FN:Alice Example\r\n"
            "EMAIL:alice@example.com\r\n"
            "END:VCARD\r\n"
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

    input_file = tmp_path / "bad-bday.vcf"
    input_file.write_text(
        ("BEGIN:VCARD\r\nVERSION:4.0\r\nFN:Alice Example\r\nEMAIL:alice@example.com\r\nBDAY:19909999\r\nEND:VCARD\r\n"),
        encoding="utf-8",
    )

    inserted = []

    def fake_insert(session, address):
        inserted.append(address)  # pragma: no cover

    monkeypatch.setattr("doost.plugins.vcard_plugin.db.insert_address", fake_insert)

    plugin.import_data(input_file, session_factory)

    assert inserted == []


def test_vcard_export_rfc_6350(tmp_path):
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
            custom="family;client",
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

    out = tmp_path / "addresses.vcf"
    plugin.export_data(out, addresses)

    assert out.read_bytes() == (
        b"BEGIN:VCARD\r\n"
        b"VERSION:4.0\r\n"
        b"KIND:individual\r\n"
        b"FN:Alice Example\r\n"
        b"N:Example;Alice;;;\r\n"
        b"EMAIL:alice@example.com\r\n"
        b"BDAY:19900102\r\n"
        b"ADR;TYPE=home:;;Main Street 1;;;;\r\n"
        b"TEL;VALUE=text;TYPE=home:111\r\n"
        b"TEL;VALUE=text;TYPE=cell:211\r\n"
        b"CATEGORIES:family,client\r\n"
        b"NOTE:Primary\r\n"
        b"END:VCARD\r\n"
        b"BEGIN:VCARD\r\n"
        b"VERSION:4.0\r\n"
        b"KIND:individual\r\n"
        b"FN:Bob\r\n"
        b"N:;Bob;;;\r\n"
        b"EMAIL:bob@example.com\r\n"
        b"END:VCARD\r\n"
    )


def test_vcard_export_folds_long_lines_and_round_trips(tmp_path, session_factory, monkeypatch):
    plugin = VCardPlugin()
    note = "x" * 90
    addresses = [
        Address(
            id=1,
            name="Alice Example",
            email="alice@example.com",
            birthday=None,
            address="",
            phone="",
            mobile="",
            custom="",
            notes=note,
        )
    ]

    out = tmp_path / "folded.vcf"
    plugin.export_data(out, addresses)

    raw = out.read_bytes().decode("utf-8")
    assert "\r\n " in raw

    inserted = []

    def fake_insert(session, address):
        inserted.append(address)

    monkeypatch.setattr("doost.plugins.vcard_plugin.db.insert_address", fake_insert)

    plugin.import_data(out, session_factory)

    assert len(inserted) == 1
    assert inserted[0].notes == note


def test_vcard_export_empty(tmp_path):
    plugin = VCardPlugin()
    out = tmp_path / "empty.vcf"
    plugin.export_data(out, [])

    assert out.read_bytes() == b""
