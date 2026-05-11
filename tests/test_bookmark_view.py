"""Tests for pw/address_view.py."""

from datetime import date

from doost.address import Address
from doost.address_view import TableFormatter, print_search_result


def _make_addresses() -> list[Address]:
    return [
        Address(
            id=1,
            name="Alpha",
            email="alpha@example.com",
            birthday=date(1990, 1, 2),
            address="Alpha Street",
            phone="111",
            mobile="211",
            custom="family",
            notes="First",
        ),
        Address(
            id=2,
            name="Beta",
            email="beta@example.com",
            birthday=None,
            address="Beta Street",
            phone="222",
            mobile="322",
            custom="work",
            notes="Second",
        ),
        Address(
            id=3,
            name="Gamma",
            email="gamma@example.com",
            birthday=date(1992, 3, 4),
            address="Gamma Street",
            phone="333",
            mobile="433",
            custom="friend",
            notes="Third",
        ),
    ]


def test_header_returns_string_with_column_labels() -> None:
    for color in ("no", "green", "#303030"):
        formatter = TableFormatter(alternate_row_color=color)
        header = formatter.header(_make_addresses())

        assert header is not None
        for column_name in ("Name", "Email", "Birthday", "Phone", "Mobile", "Custom", "Address", "ID"):
            assert column_name in header
        assert (
            header.index("Name")
            < header.index("Email")
            < header.index("Birthday")
            < header.index("Phone")
            < header.index("Mobile")
            < header.index("Custom")
            < header.index("Address")
            < header.index("ID")
        )


def test_header_empty_results_returns_none() -> None:
    formatter = TableFormatter(alternate_row_color="no")
    assert formatter.header([]) is None


def test_header_columns_are_padded_to_min_width() -> None:
    formatter = TableFormatter(alternate_row_color="no")
    header = formatter.header(_make_addresses())

    assert header is not None
    assert "Phone" + " " * 11 in header


def test_rows_returns_one_entry_per_address() -> None:
    formatter = TableFormatter(alternate_row_color="no")
    rows = formatter.rows(_make_addresses())
    assert len(rows) == 3


def test_rows_contain_address_data() -> None:
    formatter = TableFormatter(alternate_row_color="no")
    rows = formatter.rows(_make_addresses())

    assert "Alpha" in rows[0]
    assert "alpha@example.com" in rows[0]
    assert "1990-01-02" in rows[0]
    assert "Alpha Street" in rows[0]
    assert "Beta" in rows[1]
    assert "Gamma" in rows[2]
    assert rows[0].index("Alpha") < rows[0].index("alpha@example.com") < rows[0].rindex(" - [")


def test_rows_empty_results_returns_empty_list() -> None:
    formatter = TableFormatter(alternate_row_color="no")
    assert formatter.rows([]) == []


def test_rows_with_color_disabled_are_plain_strings() -> None:
    formatter = TableFormatter(alternate_row_color="no")
    rows = formatter.rows(_make_addresses())

    for row in rows:
        assert row.endswith(" ]")
        assert " - [ " in row


def test_rows_with_color_enabled_even_rows_are_wrapped() -> None:
    formatter = TableFormatter(alternate_row_color="green")
    rows = formatter.rows(_make_addresses())

    assert len(rows) == 3
    assert "Alpha" in rows[0]
    assert "Beta" in rows[1]
    assert "Gamma" in rows[2]
    assert rows[1].index("beta@example.com") < rows[1].rindex(" - [")
    assert rows[1].endswith("]")


def test_column_sizes_cached_between_header_and_rows() -> None:
    formatter = TableFormatter(alternate_row_color="no")
    addresses = _make_addresses()

    formatter.header(addresses)
    sizes_after_header = formatter._column_sizes

    formatter.rows(addresses)
    sizes_after_rows = formatter._column_sizes

    assert sizes_after_header is sizes_after_rows


def test_column_sizes_none_before_first_call() -> None:
    formatter = TableFormatter(alternate_row_color="no")
    assert formatter._column_sizes is None


def test_print_search_result_empty_does_not_raise(capsys) -> None:
    print_search_result([])
    captured = capsys.readouterr()
    assert captured.out == ""


def test_print_search_result_prints_header_and_rows(capsys) -> None:
    print_search_result(_make_addresses(), alternate_row_color="no")

    captured = capsys.readouterr()
    assert "Name" in captured.out
    assert "Alpha" in captured.out
    assert "Beta" in captured.out
    assert "Gamma" in captured.out


def test_print_search_result_default_color_does_not_raise(capsys) -> None:
    print_search_result(_make_addresses())
    captured = capsys.readouterr()
    assert "Alpha" in captured.out
