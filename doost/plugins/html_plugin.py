from html import escape
from html.parser import HTMLParser
from pathlib import Path

from doost import db
from doost.address import Address, format_birthday, parse_birthday
from doost.plugins.io import ProgressCallback, report_progress
from doost.plugins.registry import register


class _AddressHTMLParser(HTMLParser):
    """Parse address entries from an HTML file.

    Expected format per entry:

        <li data-name="Jane" data-email="jane@example.com" ...>42 Main Street</li>
    """

    def __init__(self) -> None:
        super().__init__()
        self.entries: list[Address] = []
        self._current: dict[str, str] | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "li":
            return
        attrs_dict = dict(attrs)
        self._current = {
            "name": attrs_dict.get("data-name") or "",
            "email": attrs_dict.get("data-email") or "",
            "birthday": attrs_dict.get("data-birthday") or "",
            "phone": attrs_dict.get("data-phone") or "",
            "mobile": attrs_dict.get("data-mobile") or "",
            "custom": attrs_dict.get("data-custom") or "",
            "notes": attrs_dict.get("data-notes") or "",
        }
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "li" or self._current is None:
            return

        try:
            birthday = parse_birthday(self._current["birthday"])
        except ValueError:
            self._current = None
            self._text_parts = []
            return

        self.entries.append(
            Address(
                id=None,
                name=self._current["name"].strip(),
                email=self._current["email"].strip(),
                birthday=birthday,
                address="".join(self._text_parts).strip(),
                phone=self._current["phone"].strip(),
                mobile=self._current["mobile"].strip(),
                custom=self._current["custom"].strip(),
                notes=self._current["notes"].strip(),
            )
        )
        self._current = None
        self._text_parts = []


class HTMLPlugin:
    """Import/export addresses in HTML format.

    The HTML format uses one ``<li>`` element per address:

        <li data-name="Jane" data-email="jane@example.com" ...>42 Main Street</li>
    """

    format = "html"

    def import_data(self, path: Path, session_factory, progress_callback: ProgressCallback | None = None) -> None:
        """Import addresses from an HTML file.

        Args:
            path: Path to the HTML input file.
            session_factory: Callable returning a DB session.

        Notes:
            - Invalid or incomplete entries are skipped silently.
            - Duplicate addresses are ignored.
        """
        parser = _AddressHTMLParser()
        parser.feed(path.read_text(encoding="utf-8"))

        total = len(parser.entries)
        report_progress(progress_callback, 0, total)

        with session_factory() as session:
            for index, address in enumerate(parser.entries, start=1):
                try:
                    if not address.name or not address.email:
                        continue
                    db.insert_address(session, address)
                except ValueError:
                    # Duplicate address — skip silently
                    pass
                finally:
                    report_progress(progress_callback, index, total)

    def export_data(
        self,
        path: Path,
        addresses: list[Address],
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Export addresses to an HTML file.

        Args:
            path: Destination file path.
            addresses: List of addresses to export.

        Notes:
            - Existing files are overwritten.
            - UTF-8 encoding is always used.
        """
        total = len(addresses)
        report_progress(progress_callback, 0, total)

        with path.open("w", encoding="utf-8") as fh:
            for index, address in enumerate(addresses, start=1):
                fh.write(
                    (
                        f'<li data-name="{escape(address.name, quote=True)}" '
                        f'data-email="{escape(address.email, quote=True)}" '
                        f'data-birthday="{escape(format_birthday(address.birthday), quote=True)}" '
                        f'data-phone="{escape(address.phone, quote=True)}" '
                        f'data-mobile="{escape(address.mobile, quote=True)}" '
                        f'data-custom="{escape(address.custom, quote=True)}" '
                        f'data-notes="{escape(address.notes, quote=True)}">'
                        f"{escape(address.address)}</li>\n"
                    )
                )
                report_progress(progress_callback, index, total)


register(HTMLPlugin())
