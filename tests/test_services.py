from datetime import date
from pathlib import Path

from doost.address import Address
from doost.services import AddressFilters, AddressService


def test_service_crud_and_filtering(tmp_path: Path) -> None:
    service = AddressService(tmp_path / "peywand.db")
    try:
        service.initialize_database()

        first = service.add_address(
            name="Hacker News",
            email="hn@example.com",
            birthday=date(1985, 1, 15),
            address="Internet",
            phone="111",
            mobile="222",
            custom="news;tech",
            notes="Daily reading",
        )
        service.add_address(
            name="Python",
            email="python@example.com",
            birthday=date(1991, 2, 20),
            address="Docs Plaza",
            phone="333",
            mobile="444",
            custom="language;docs",
            notes="Reference",
        )

        rows = service.list_addresses(AddressFilters(custom="news"))
        assert [item.id for item in rows] == [first.id]

        updated = service.update_address(
            first.id or 0,
            name="HN",
            email="hn@example.com",
            birthday=date(1985, 1, 15),
            address="Internet",
            phone="111",
            mobile="222",
            custom="news;reading",
            notes="Updated note",
        )
        assert updated.name == "HN"

        fetched = service.get_address(first.id or 0)
        assert fetched.notes == "Updated note"

        service.delete_address(first.id or 0)
        assert [item.name for item in service.list_addresses()] == ["Python"]
    finally:
        service.close()


def test_service_export_and_import_json(tmp_path: Path) -> None:
    source = AddressService(tmp_path / "source.db")
    target = AddressService(tmp_path / "target.db")
    try:
        source.initialize_database()
        source.add_address(
            name="Example",
            email="example@example.com",
            birthday=date(1992, 6, 3),
            address="42 Main St",
            phone="123",
            mobile="456",
            custom="demo",
            notes="Imported later",
        )

        export_path = tmp_path / "addresses.json"
        source.export_addresses(path=export_path, file_format="json")
        assert export_path.exists()

        target.initialize_database()
        target.import_addresses(path=export_path, file_format="json")

        imported = target.list_addresses()
        assert len(imported) == 1
        assert imported[0].email == "example@example.com"
    finally:
        source.close()
        target.close()


def test_service_passes_progress_callback_to_plugins(tmp_path: Path, monkeypatch) -> None:
    service = AddressService(tmp_path / "peywand.db")
    import_events: list[tuple[int, int | None]] = []
    export_events: list[tuple[int, int | None]] = []

    class RecordingPlugin:
        def import_data(self, path, session_factory, progress_callback=None) -> None:
            if progress_callback is not None:
                progress_callback(1, 3)

        def export_data(self, path, addresses, progress_callback=None) -> None:
            assert addresses == [
                Address(
                    id=1,
                    name="Example",
                    email="example@example.com",
                    birthday=date(1992, 6, 3),
                    address="42 Main St",
                    phone="123",
                    mobile="456",
                    custom="demo",
                    notes="Note",
                )
            ]
            if progress_callback is not None:
                progress_callback(2, 4)

    try:
        monkeypatch.setattr("doost.services.get_plugin", lambda file_format: RecordingPlugin())
        monkeypatch.setattr(
            service,
            "list_addresses",
            lambda filters=None: [
                Address(
                    id=1,
                    name="Example",
                    email="example@example.com",
                    birthday=date(1992, 6, 3),
                    address="42 Main St",
                    phone="123",
                    mobile="456",
                    custom="demo",
                    notes="Note",
                )
            ],
        )

        service.import_addresses(
            path=tmp_path / "addresses.json",
            file_format="json",
            progress_callback=lambda completed, total: import_events.append((completed, total)),
        )
        service.export_addresses(
            path=tmp_path / "addresses.json",
            file_format="json",
            progress_callback=lambda completed, total: export_events.append((completed, total)),
        )
    finally:
        service.close()

    assert import_events == [(1, 3)]
    assert export_events == [(2, 4)]


def test_address_filters_has_filters_false_when_empty() -> None:
    assert AddressFilters().has_filters() is False


def test_address_filters_has_filters_true_when_set() -> None:
    assert AddressFilters(email="alice@example.com").has_filters() is True


def test_list_addresses_with_no_filters_returns_all(tmp_path: Path) -> None:
    service = AddressService(tmp_path / "peywand.db")
    try:
        service.initialize_database()
        service.add_address(
            name="Alpha",
            email="alpha@example.com",
            birthday=None,
            address="A",
            phone="",
            mobile="",
            custom="",
            notes="",
        )
        service.add_address(
            name="Beta",
            email="beta@example.com",
            birthday=None,
            address="B",
            phone="",
            mobile="",
            custom="",
            notes="",
        )

        rows = service.list_addresses()
        assert len(rows) == 2
        assert [item.name for item in rows] == ["Alpha", "Beta"]
    finally:
        service.close()


def test_list_addresses_with_filters_no_match_returns_empty(tmp_path: Path) -> None:
    service = AddressService(tmp_path / "peywand.db")
    try:
        service.initialize_database()
        service.add_address(
            name="Alpha",
            email="alpha@example.com",
            birthday=None,
            address="A",
            phone="",
            mobile="",
            custom="family",
            notes="",
        )

        rows = service.list_addresses(AddressFilters(name="zzz"))
        assert rows == []
    finally:
        service.close()
