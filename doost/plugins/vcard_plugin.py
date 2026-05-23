from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from urllib.parse import unquote

from doost import db
from doost.address import Address, parse_birthday
from doost.plugins.io import ProgressCallback, report_progress
from doost.plugins.registry import register

_BASIC_DATE_RE = re.compile(r"^\d{8}$")
_EXTENDED_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BASIC_DATETIME_RE = re.compile(r"^(?P<date>\d{8})T\d{2}(\d{2}(\d{2})?)?([Z]|[+-]\d{2}(\d{2})?)?$")
_EXTENDED_DATETIME_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})T\d{2}(:\d{2}(:\d{2})?)?([Z]|[+-]\d{2}(:?\d{2})?)?$")
_PARTIAL_DATE_RE = re.compile(r"^(\d{4}|\d{4}-\d{2}|--\d{2}\d{2}|--\d{2}-\d{2}|---\d{2}|T.+)$")


def _split_outside_quotes(value: str, separator: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    in_quotes = False

    for char in value:
        if char == '"':
            in_quotes = not in_quotes
            current.append(char)
            continue
        if char == separator and not in_quotes:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)

    parts.append("".join(current))
    return parts


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


def _unfold_lines(text: str) -> list[str]:
    """Join folded vCard content lines into their logical lines."""
    unfolded: list[str] = []
    for raw_line in text.splitlines():
        if raw_line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += raw_line[1:]
            continue
        unfolded.append(raw_line)
    return unfolded


def _split_contentline(line: str) -> tuple[str, dict[str, list[str]], str]:
    """Parse one content line into property name, parameters, and raw value."""
    left_side: list[str] = []
    in_quotes = False
    value_start = len(line)

    for index, char in enumerate(line):
        if char == '"':
            in_quotes = not in_quotes
        elif char == ":" and not in_quotes:
            value_start = index
            break
        left_side.append(char)

    name_and_params = "".join(left_side)
    value = line[value_start + 1 :] if value_start < len(line) else ""
    parts = _split_outside_quotes(name_and_params, ";")
    property_name = parts[0].upper()
    if "." in property_name:
        property_name = property_name.rsplit(".", 1)[-1]

    parameters: dict[str, list[str]] = {}
    for part in parts[1:]:
        if not part:
            continue
        if "=" in part:
            key, raw_values = part.split("=", 1)
            key = key.upper()
            raw_values = raw_values.strip()
            if raw_values.startswith('"') and raw_values.endswith('"') and len(raw_values) >= 2:
                raw_values = raw_values[1:-1]
            values = [item.strip() for item in _split_outside_quotes(raw_values, ",") if item.strip()]
        else:
            key = "TYPE"
            values = [part.strip()]
        parameters.setdefault(key, []).extend(values)

    return property_name, parameters, value


def _unescape_text(value: str) -> str:
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


def _escape_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace(",", r"\,")


def _escape_component(value: str) -> str:
    return _escape_text(value).replace(";", r"\;")


def _fold_contentline(line: str) -> str:
    """Fold a content line to the RFC 6350 75-octet limit."""
    limit = 75
    parts: list[str] = []
    current = ""
    prefix = ""

    for char in line:
        candidate = current + char
        if len((prefix + candidate).encode("utf-8")) <= limit:
            current = candidate
            continue

        if current:
            parts.append(prefix + current)
            prefix = " "
            current = char
            continue

        parts.append(prefix)
        prefix = " "
        current = char

    parts.append(prefix + current)
    return "\r\n".join(parts)


def _render_lines(lines: list[str]) -> str:
    return "\r\n".join(_fold_contentline(line) for line in lines) + "\r\n"


def _basic_date(value: date) -> str:
    return f"{value:%Y%m%d}"


def _parse_birthday_value(raw_value: str, parameters: dict[str, list[str]]) -> date | None:
    """Parse BDAY values that map cleanly to a Python ``date``."""
    if any(item.casefold() == "text" for item in parameters.get("VALUE", [])):
        return None

    text = _unescape_text(raw_value).strip()
    if not text:
        return None
    if _BASIC_DATE_RE.fullmatch(text):
        return parse_birthday(f"{text[:4]}-{text[4:6]}-{text[6:]}")
    if _EXTENDED_DATE_RE.fullmatch(text):
        return parse_birthday(text)

    basic_match = _BASIC_DATETIME_RE.fullmatch(text)
    if basic_match is not None:
        compact = basic_match.group("date")
        return parse_birthday(f"{compact[:4]}-{compact[4:6]}-{compact[6:]}")

    extended_match = _EXTENDED_DATETIME_RE.fullmatch(text)
    if extended_match is not None:
        return parse_birthday(extended_match.group("date"))

    if _PARTIAL_DATE_RE.fullmatch(text):
        return None

    raise ValueError("Invalid BDAY value")


def _decode_component_values(component: str) -> list[str]:
    return [_unescape_text(part).strip() for part in _split_escaped(component, ",") if _unescape_text(part).strip()]


def _structured_name_to_full_name(value: str) -> str:
    parts = _split_escaped(value, ";")
    while len(parts) < 5:
        parts.append("")

    family_name = " ".join(_decode_component_values(parts[0]))
    given_name = " ".join(_decode_component_values(parts[1]))
    additional_name = " ".join(_decode_component_values(parts[2]))
    honorific_prefix = " ".join(_decode_component_values(parts[3]))
    honorific_suffix = ", ".join(_decode_component_values(parts[4]))

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

    return ";".join([_escape_component(family_name), _escape_component(given_name), "", "", ""])


def _parse_address_value(raw_value: str) -> str:
    components = _split_escaped(raw_value, ";")
    while len(components) < 7:
        components.append("")

    rendered_components = [", ".join(_decode_component_values(component)) for component in components[:7]]
    return ", ".join(component for component in rendered_components if component)


def _parse_categories(raw_value: str) -> list[str]:
    return [_unescape_text(part).strip() for part in _split_escaped(raw_value, ",") if _unescape_text(part).strip()]


def _split_custom_categories(value: str) -> list[str]:
    categories: list[str] = []
    for item in re.split(r"[;\n]+", value):
        stripped = item.strip()
        if stripped:
            categories.append(stripped)
    return categories


def _normalize_tel_value(raw_value: str, parameters: dict[str, list[str]]) -> str:
    """Return a plain phone string from either text or ``tel:`` URI values."""
    value = raw_value.strip()
    parameter_values = {item.casefold() for item in parameters.get("VALUE", [])}
    if "uri" in parameter_values or value.casefold().startswith("tel:"):
        if value.casefold().startswith("tel:"):
            return unquote(value[4:])
        return unquote(value)
    return _unescape_text(value).strip()


def _pref_rank(parameters: dict[str, list[str]], *, default: int = 100) -> int:
    for raw_value in parameters.get("PREF", []):
        try:
            parsed = int(raw_value)
        except ValueError:
            continue
        if parsed > 0:
            return parsed
    return default


def _type_values(parameters: dict[str, list[str]]) -> set[str]:
    return {value.casefold() for value in parameters.get("TYPE", [])}


def _select_better_candidate[T](
    current: tuple[tuple[int, ...], T] | None, rank: tuple[int, ...], value: T
) -> tuple[tuple[int, ...], T]:
    if current is None or rank < current[0]:
        return (rank, value)
    return current


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
    """Convert one vCard object into the app's single-address model."""
    name = ""
    structured_name = ""
    birthday = None
    note_parts: list[str] = []
    categories: list[str] = []
    legacy_custom = ""

    email_choice: tuple[tuple[int, ...], str] | None = None
    address_choice: tuple[tuple[int, ...], str] | None = None
    phone_choice: tuple[tuple[int, ...], str] | None = None
    mobile_choice: tuple[tuple[int, ...], str] | None = None

    for index, line in enumerate(lines):
        property_name, parameters, raw_value = _split_contentline(line)
        value = _unescape_text(raw_value).strip()

        if property_name == "VERSION":
            continue
        if property_name == "FN" and value and not name:
            name = value
            continue
        if property_name == "N" and raw_value and not structured_name:
            structured_name = raw_value
            continue
        if property_name == "BDAY":
            birthday = _parse_birthday_value(raw_value, parameters)
            continue
        if property_name == "EMAIL" and value:
            rank = (_pref_rank(parameters), index)
            email_choice = _select_better_candidate(email_choice, rank, value)
            continue
        if property_name == "ADR" and raw_value.strip():
            rank = (_pref_rank(parameters), 0 if "home" in _type_values(parameters) else 1, index)
            address_choice = _select_better_candidate(address_choice, rank, _parse_address_value(raw_value))
            continue
        if property_name == "TEL" and raw_value.strip():
            tel_value = _normalize_tel_value(raw_value, parameters)
            if not tel_value:
                continue

            type_values = _type_values(parameters)
            rank = (_pref_rank(parameters), 0 if "home" in type_values else 1, index)
            if {"cell", "mobile"} & type_values:
                mobile_choice = _select_better_candidate(mobile_choice, rank, tel_value)
            else:
                phone_choice = _select_better_candidate(phone_choice, rank, tel_value)
            continue
        if property_name == "NOTE" and value:
            note_parts.append(value)
            continue
        if property_name == "CATEGORIES" and raw_value.strip():
            categories.extend(_parse_categories(raw_value))
            continue
        if property_name == "X-DOOST-CUSTOM" and value and not legacy_custom:
            legacy_custom = value

    if not name and structured_name:
        name = _structured_name_to_full_name(structured_name)

    custom_values = categories or _split_custom_categories(legacy_custom)
    custom = ";".join(dict.fromkeys(custom_values))

    return Address(
        id=None,
        name=name.strip(),
        email=(email_choice[1] if email_choice is not None else "").strip(),
        birthday=birthday,
        address=(address_choice[1] if address_choice is not None else "").strip(),
        phone=(phone_choice[1] if phone_choice is not None else "").strip(),
        mobile=(mobile_choice[1] if mobile_choice is not None else "").strip(),
        custom=custom,
        notes="\n".join(note_parts).strip(),
    )


class VCardPlugin:
    """Import/export addresses in RFC 6350 vCard 4.0 format."""

    format = "vcard"

    def import_data(self, path: Path, session_factory, progress_callback: ProgressCallback | None = None) -> None:
        """Import all vCards found in ``path`` into the database."""
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
                    # Invalid property content or duplicate entry
                    pass
                finally:
                    report_progress(progress_callback, index, total)

    def export_data(
        self,
        path: Path,
        addresses: list[Address],
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Export addresses as RFC 6350 vCard 4.0 records."""
        total = len(addresses)
        report_progress(progress_callback, 0, total)

        cards: list[str] = []
        for index, address in enumerate(addresses, start=1):
            lines = [
                "BEGIN:VCARD",
                "VERSION:4.0",
                "KIND:individual",
                f"FN:{_escape_text(address.name)}",
                f"N:{_full_name_to_structured_name(address.name)}",
                f"EMAIL:{_escape_text(address.email)}",
            ]

            if address.birthday is not None:
                lines.append(f"BDAY:{_basic_date(address.birthday)}")
            if address.address:
                lines.append(f"ADR;TYPE=home:;;{_escape_component(address.address)};;;;")
            if address.phone:
                lines.append(f"TEL;VALUE=text;TYPE=home:{_escape_text(address.phone)}")
            if address.mobile:
                lines.append(f"TEL;VALUE=text;TYPE=cell:{_escape_text(address.mobile)}")
            if address.custom:
                category_values = _split_custom_categories(address.custom)
                if category_values:
                    lines.append(f"CATEGORIES:{','.join(_escape_text(item) for item in category_values)}")
            if address.notes:
                lines.append(f"NOTE:{_escape_text(address.notes)}")

            lines.append("END:VCARD")
            cards.append(_render_lines(lines))
            report_progress(progress_callback, index, total)

        path.write_text("".join(cards), encoding="utf-8")


register(VCardPlugin())
