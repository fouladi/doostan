import json
from collections.abc import Mapping
from pathlib import Path

from doost import db
from doost.address import Address, format_birthday, parse_birthday
from doost.plugins.io import ProgressCallback, report_progress
from doost.plugins.registry import register


def _string_value(item: object, key: str, *, required: bool = False) -> str:
    if not isinstance(item, Mapping):
        if required:
            raise ValueError(f"Invalid value for {key}")
        return ""

    value: object = ""
    for item_key, item_value in item.items():
        if item_key == key:
            value = item_value
            break

    if isinstance(value, str):
        return value
    if required:
        raise ValueError(f"Invalid value for {key}")
    return ""


class JSONPlugin:
    format = "json"

    def import_data(self, path: Path, session_factory, progress_callback: ProgressCallback | None = None) -> None:
        """Read address entries from a JSON file and insert them into the database."""
        data = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(data, list):
            raise ValueError("Invalid JSON format")

        total = len(data)
        report_progress(progress_callback, 0, total)

        with session_factory() as session:
            for index, item in enumerate(data, start=1):
                try:
                    if not isinstance(item, Mapping):
                        continue

                    address = Address(
                        id=None,
                        name=_string_value(item, "name", required=True).strip(),
                        email=_string_value(item, "email", required=True).strip(),
                        birthday=parse_birthday(_string_value(item, "birthday")),
                        address=_string_value(item, "address").strip(),
                        phone=_string_value(item, "phone").strip(),
                        mobile=_string_value(item, "mobile").strip(),
                        custom=_string_value(item, "custom").strip(),
                        notes=_string_value(item, "notes").strip(),
                    )
                    if not address.name or not address.email:
                        continue
                    db.insert_address(
                        session,
                        address,
                    )
                except ValueError:
                    # Missing fields or duplicate entry
                    pass
                finally:
                    report_progress(progress_callback, index, total)

    def export_data(
        self,
        path: Path,
        addresses: list[Address],
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Export addresses to a JSON file.

        Args:
            path: Destination file path.
            addresses: List of addresses to export.

        Notes:
            - Existing files are overwritten.
            - UTF-8 encoding is always used.
        """
        total = len(addresses)
        report_progress(progress_callback, 0, total)

        payload = []
        for index, address in enumerate(addresses, start=1):
            payload.append(
                {
                    "name": address.name,
                    "email": address.email,
                    "birthday": format_birthday(address.birthday),
                    "address": address.address,
                    "phone": address.phone,
                    "mobile": address.mobile,
                    "custom": address.custom,
                    "notes": address.notes,
                }
            )
            report_progress(progress_callback, index, total)

        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


register(JSONPlugin())
