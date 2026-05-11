from dataclasses import dataclass
from datetime import date


def parse_birthday(value: str | None) -> date | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return date.fromisoformat(value)


def format_birthday(value: date | None) -> str:
    return value.isoformat() if value is not None else ""


@dataclass(slots=True, frozen=True)
class Address:
    id: int | None
    name: str
    email: str
    birthday: date | None
    address: str
    phone: str
    mobile: str
    custom: str
    notes: str
