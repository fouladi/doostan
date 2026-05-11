import json
from pathlib import Path

from doost import db
from doost.address import Address, format_birthday, parse_birthday
from doost.plugins.io import ProgressCallback, report_progress
from doost.plugins.registry import register


class JSONPlugin:
    format = "json"

    def import_data(self, path: Path, session_factory, progress_callback: ProgressCallback | None = None) -> None:
        """Read address entries from a JSON file and insert them into the database.
        """
        data = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(data, list):
            raise ValueError("Invalid JSON format")

        total = len(data)
        report_progress(progress_callback, 0, total)

        with session_factory() as session:
            for index, item in enumerate(data, start=1):
                try:
                    address = Address(
                        id=None,
                        name=item["name"].strip(),
                        email=item["email"].strip(),
                        birthday=parse_birthday(item.get("birthday", "")),
                        address=item.get("address", "").strip(),
                        phone=item.get("phone", "").strip(),
                        mobile=item.get("mobile", "").strip(),
                        custom=item.get("custom", "").strip(),
                        notes=item.get("notes", "").strip(),
                    )
                    if not address.name or not address.email:
                        continue
                    db.insert_address(
                        session,
                        address,
                    )
                except (KeyError, ValueError):
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
