from collections.abc import Iterable

import colored

from doost.address import Address, format_birthday
from doost.util import DEFAULT_BG_COLOR

ALT_BGROUND = colored.back(DEFAULT_BG_COLOR)
BOLD = colored.style("bold")
UNDERLINE = colored.style("underline")
RESET = colored.style("reset")

MIN_COL_WIDTH = 16


class TableFormatter:
    """Formats tabular address data for terminal output."""

    def __init__(self, *, min_column_width: int = MIN_COL_WIDTH, alternate_row_color: str) -> None:
        self._min_column_width = min_column_width
        self._use_color = alternate_row_color != "no"
        self._alternate_row_style = ALT_BGROUND if alternate_row_color == "no" else colored.back(alternate_row_color)
        self._column_sizes: tuple[int, int, int, int, int, int, int, int] | None = None

    def _column_width(self, values: Iterable[str]) -> int:
        width = max((len(value) for value in values), default=0)
        return max(width, self._min_column_width)

    def _compute_column_sizes(
        self,
        addresses: list[Address],
    ) -> tuple[int, int, int, int, int, int, int, int]:
        if self._column_sizes is None:
            len_id = self._column_width(str(address.id or "") for address in addresses)
            len_name = self._column_width(address.name for address in addresses)
            len_email = self._column_width(address.email for address in addresses)
            len_birthday = self._column_width(format_birthday(address.birthday) for address in addresses)
            len_phone = self._column_width(address.phone or "" for address in addresses)
            len_mobile = self._column_width(address.mobile or "" for address in addresses)
            len_custom = self._column_width(address.custom or "" for address in addresses)
            len_address = self._column_width(address.address or "" for address in addresses)
            self._column_sizes = (
                len_id,
                len_name,
                len_email,
                len_birthday,
                len_phone,
                len_mobile,
                len_custom,
                len_address,
            )
        return self._column_sizes

    def header(self, addresses: list[Address]) -> str | None:
        if not addresses:
            return None

        len_id, len_name, len_email, len_birthday, len_phone, len_mobile, len_custom, len_address = (
            self._compute_column_sizes(addresses)
        )

        header = (
            f"{'Name'.ljust(len_name)} "
            f"{'Email'.ljust(len_email)} "
            f"{'Birthday'.ljust(len_birthday)} "
            f"{'Phone'.ljust(len_phone)} "
            f"{'Mobile'.ljust(len_mobile)} "
            f"{'Custom'.ljust(len_custom)} "
            f"{'Address'.ljust(len_address)}   "
            f"[ {'ID'.rjust(len_id)} ]"
        )
        return f"{UNDERLINE}{BOLD}{header}{RESET}" if self._alternate_row_style else header

    def rows(self, addresses: list[Address]) -> list[str]:
        if not addresses:
            return []

        len_id, len_name, len_email, len_birthday, len_phone, len_mobile, len_custom, len_address = (
            self._compute_column_sizes(addresses)
        )
        lines: list[str] = []

        for index, address in enumerate(addresses):
            line = (
                f"{address.name.ljust(len_name)} "
                f"{address.email.ljust(len_email)} "
                f"{format_birthday(address.birthday).ljust(len_birthday)} "
                f"{(address.phone or '').ljust(len_phone)} "
                f"{(address.mobile or '').ljust(len_mobile)} "
                f"{(address.custom or '').ljust(len_custom)} "
                f"{(address.address or '').ljust(len_address)} "
                f" - [ {str(address.id).rjust(len_id)} ]"
            )

            if self._use_color and index % 2 == 0:
                lines.append(f"{self._alternate_row_style}{line}{RESET}")
            else:
                lines.append(line)

        return lines


def print_search_result(search_result: list[Address], alternate_row_color: str = DEFAULT_BG_COLOR) -> None:
    """Print address search results in a formatted table."""
    if not search_result:
        return

    formatter = TableFormatter(alternate_row_color=alternate_row_color)

    header = formatter.header(search_result)
    if header:
        print(header)
        print()

    for line in formatter.rows(search_result):
        print(line)
