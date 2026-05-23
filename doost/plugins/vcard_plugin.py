from datetime import date
from pathlib import Path

from doost import db
from doost.address import Address, format_birthday, parse_birthday
from doost.plugins.io import ProgressCallback, report_progress
from doost.plugins.registry import register


def _unfold_lines(text: str) -> list[str]:
    unfolded: list[str] = []
    for raw_line in text.splitlines():
        if raw_line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += raw_line[1:]
            continue
        unfolded.append(raw_line)
    return unfolded


def _split_property(line: str) -> tuple[str, set[str], str]:
    name_and_params, separator, value = line.partition(":")
    if not separator:
        return line.upper(), set(), ""

    parts = name_and_params.split(";")
    property_name = parts[0].upper()
    if "." in property_name:
        property_name = property_name.rsplit(".", 1)[-1]

    parameters: set[str] = set()
    for part in parts[1:]:
        upper_part = part.upper()
        if "=" in upper_part:
            _, parameter_values = upper_part.split("=", 1)
            parameters.update(value for value in parameter_values.split(",") if value)
            continue
        if upper_part:
            parameters.add(upper_part)

    return property_name, parameters, value


def _unescape_value(value: str) -> str:
    chars: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            escaped = value[index + 1]
            chars.append("\n" if escaped in {"n", "N"} else escaped)
            index += 2
            continue
        chars.append(value[index])
        index += 1
    return "".join(chars)


def _escape_value(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(";", r"\;")
        .replace(",", r"\,")
    )


def _split_escaped(value: str, separator: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value):
            current.append(char)
            current.append(value[index + 1])
            index += 2
            continue
        if char == separator:
            parts.append("".join(current))
            current = []
            index += 1
            continue
        current.append(char)
        index += 1

    parts.append("".join(current))
    return parts


def _parse_birthday_value(value: str) -> date | None:
    text = _unescape_value(value).strip()
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        text = f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return parse_birthday(text)


def _structured_name_to_full_name(value: str) -> str:
    parts = [_unescape_value(part).strip() for part in _split_escaped(value, ";")]
    while len(parts) < 5:
        parts.append("")

    family_name, given_name, additional_name, honorific_prefix, honorific_suffix = parts[:5]
    ordered_parts = [honorific_prefix, given_name, additional_name, family_name, honorific_suffix]
    return " ".join(part for part in ordered_parts if part).strip()


def _full_name_to_structured_name(value: str) -> str:
    parts = value.split()
    if len(parts) <= 1:
        family_name = ""
        given_name = value
    else:
        family_name = parts[-1]
        given_name = " ".join(parts[:-1])

    return ";".join(
        [
            _escape_value(family_name),
            _escape_value(given_name),
            "",
            "",
            "",
        ]
    )


def _parse_address_value(value: str) -> str:
    components = [_unescape_value(part).strip() for part in _split_escaped(value, ";")]
    joined = ", ".join(component for component in components[2:] if component)
    return joined or _unescape_value(value).strip()


def _iter_cards(text: str) -> list[list[str]]:
    cards: list[list[str]] = []
    current_card: list[str] | None = None

    for line in _unfold_lines(text):
        normalized = line.strip().upper()
        if normalized == "BEGIN:VCARD":
            current_card = []
            continue
        if normalized == "END:VCARD":
            if current_card is not None:
                cards.append(current_card)
                current_card = None
            continue
        if current_card is not None and line.strip():
            current_card.append(line)

    return cards


def _card_to_address(lines: list[str]) -> Address:
    name = ""
    structured_name = ""
    email = ""
    birthday = None
    address = ""
    phone = ""
    phone_priority = 0
    mobile = ""
    custom = ""
    note_parts: list[str] = []

    for line in lines:
        property_name, parameters, raw_value = _split_property(line)
        value = _unescape_value(raw_value).strip()

        if property_name == "FN" and value and not name:
            name = value
            continue
        if property_name == "N" and value and not structured_name:
            structured_name = value
            continue
        if property_name == "EMAIL" and value and not email:
            email = value
            continue
        if property_name == "BDAY":
            birthday = _parse_birthday_value(raw_value)
            continue
        if property_name == "ADR" and value and not address:
            address = _parse_address_value(raw_value)
            continue
        if property_name == "TEL" and value:
            if {"CELL", "MOBILE"} & parameters:
                if not mobile:
                    mobile = value
                continue
            if "HOME" in parameters:
                if phone_priority < 2:
                    phone = value
                    phone_priority = 2
                continue
            if phone_priority < 1:
                phone = value
                phone_priority = 1
            continue
        if property_name == "NOTE" and value:
            note_parts.append(value)
            continue
        if property_name == "X-DOOST-CUSTOM" and value and not custom:
            custom = value

    if not name and structured_name:
        name = _structured_name_to_full_name(structured_name)

    return Address(
        id=None,
        name=name.strip(),
        email=email.strip(),
        birthday=birthday,
        address=address.strip(),
        phone=phone.strip(),
        mobile=mobile.strip(),
        custom=custom.strip(),
        notes="\n".join(note_parts).strip(),
    )


class VCardPlugin:
    """Import/export addresses in vCard format."""

    format = "vcard"

    def import_data(self, path: Path, session_factory, progress_callback: ProgressCallback | None = None) -> None:
        cards = _iter_cards(path.read_text(encoding="utf-8"))
        total = len(cards)
        report_progress(progress_callback, 0, total)

        with session_factory() as session:
            for index, card in enumerate(cards, start=1):
                try:
                    address = _card_to_address(card)
                    if not address.name or not address.email:
                        continue
                    db.insert_address(session, address)
                except ValueError:
                    # Invalid birthday or duplicate entry
                    pass
                finally:
                    report_progress(progress_callback, index, total)

    def export_data(
        self,
        path: Path,
        addresses: list[Address],
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        total = len(addresses)
        report_progress(progress_callback, 0, total)

        cards: list[str] = []
        for index, address in enumerate(addresses, start=1):
            lines = [
                "BEGIN:VCARD",
                "VERSION:3.0",
                f"FN:{_escape_value(address.name)}",
                f"N:{_full_name_to_structured_name(address.name)}",
                f"EMAIL;INTERNET:{_escape_value(address.email)}",
            ]

            birthday = format_birthday(address.birthday)
            if birthday:
                lines.append(f"BDAY:{birthday}")
            if address.address:
                lines.append(f"ADR:;;{_escape_value(address.address)};;;;")
            if address.phone:
                lines.append(f"TEL;HOME:{_escape_value(address.phone)}")
            if address.mobile:
                lines.append(f"TEL;CELL:{_escape_value(address.mobile)}")
            if address.custom:
                lines.append(f"X-DOOST-CUSTOM:{_escape_value(address.custom)}")
            if address.notes:
                lines.append(f"NOTE:{_escape_value(address.notes)}")

            lines.append("END:VCARD")
            cards.append("\n".join(lines))
            report_progress(progress_callback, index, total)

        path.write_text("\n\n".join(cards) + ("\n" if cards else ""), encoding="utf-8")


register(VCardPlugin())
