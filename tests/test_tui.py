import asyncio
from pathlib import Path

from textual.widgets import DataTable, Input, Select, Static

from doost.tui import AddressDetailScreen, DoostanApp, FileTransferProgressScreen


def test_tui_crud_and_filter_flow(tmp_path: Path) -> None:
    async def scenario() -> None:
        app = DoostanApp(tmp_path / "doostan.db")

        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause(0.05)

            await pilot.click("#add")
            await pilot.pause(0.05)
            app.screen.query_one("#address-name", Input).value = "Example Person"
            app.screen.query_one("#address-email", Input).value = "person@example.com"
            app.screen.query_one("#address-birthday", Input).value = "1990-01-02"
            app.screen.query_one("#address-phone", Input).value = "123"
            app.screen.query_one("#address-mobile", Input).value = "456"
            app.screen.query_one("#address-address", Input).value = "42 Example Street"
            app.screen.query_one("#address-custom", Input).value = "client"
            app.screen.query_one("#address-notes", Input).value = "Met at conference"
            await pilot.click("#save")
            await pilot.pause(0.05)

            table = app.query_one("#addresses-table", DataTable)
            assert table.row_count == 1
            assert [str(column.label) for column in table.ordered_columns] == [
                "Name",
                "Email",
                "Birthday",
                "Phone",
                "Mobile",
                "Custom",
                "ID",
            ]
            assert table.get_row("1") == [
                "Example Person",
                "person@example.com",
                "1990-01-02",
                "123",
                "456",
                "client",
                "1",
            ]
            details = str(app.query_one("#details", Static).renderable)
            assert "Example Person" in details
            assert "1990-01-02" in details
            assert "42 Example Street" in details
            assert app.query_one("#details", Static).region.y < app.query_one("#filter-value", Input).region.y

            await pilot.click("#edit")
            await pilot.pause(0.05)
            app.screen.query_one("#address-name", Input).value = "Changed Person"
            await pilot.click("#save")
            await pilot.pause(0.05)
            assert "Changed Person" in str(app.query_one("#details", Static).renderable)

            table.focus()
            await pilot.press("enter")
            await pilot.pause(0.05)
            assert isinstance(app.screen, AddressDetailScreen)
            assert "Changed Person" in str(app.screen.query_one("#detail-content", Static).renderable)
            await pilot.press("escape")
            await pilot.pause(0.05)
            assert not isinstance(app.screen, AddressDetailScreen)

            app.query_one("#filter-field", Select).value = "name"
            app.query_one("#filter-value", Input).value = "Changed"
            app.refresh_table()
            await pilot.pause(0.05)
            assert table.row_count == 1

            app.query_one("#filter-field", Select).value = "email"
            app.query_one("#filter-value", Input).value = "person@example.com"
            await pilot.click("#clear-filters")
            await pilot.pause(0.05)
            assert table.row_count == 1
            assert app.query_one("#filter-field", Select).value == "name"
            assert app.query_one("#filter-value", Input).value == ""

            await pilot.click("#delete")
            await pilot.pause(0.05)
            await pilot.click("#confirm")
            await pilot.pause(0.05)
            assert table.row_count == 0

    asyncio.run(scenario())


def test_tui_rejects_invalid_birthday(tmp_path: Path) -> None:
    async def scenario() -> None:
        app = DoostanApp(tmp_path / "doostan.db")

        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause(0.05)

            await pilot.click("#add")
            await pilot.pause(0.05)
            app.screen.query_one("#address-name", Input).value = "Example Person"
            app.screen.query_one("#address-email", Input).value = "person@example.com"
            app.screen.query_one("#address-birthday", Input).value = "1990-99-99"
            await pilot.click("#save")
            await pilot.pause(0.05)

            assert app.query_one("#addresses-table", DataTable).row_count == 0
            assert app.screen.query_one("#address-birthday", Input).value == "1990-99-99"

    asyncio.run(scenario())


def test_tui_default_size_keeps_import_export_accessible(tmp_path: Path) -> None:
    async def scenario() -> None:
        app = DoostanApp(tmp_path / "doostan.db")

        async with app.run_test() as pilot:
            await pilot.pause(0.05)

            app.query_one("#export-menu", Select).value = "json"
            await pilot.pause(0.05)
            assert app.screen.query_one("#file-path", Input).placeholder == "/path/to/file.json"
            await pilot.press("escape")
            await pilot.pause(0.05)

            app.query_one("#import-menu", Select).value = "csv"
            await pilot.pause(0.05)
            assert app.screen.query_one("#file-path", Input).placeholder == "/path/to/file.csv"

    asyncio.run(scenario())


def test_tui_format_menus_reset_and_drive_file_extension(tmp_path: Path) -> None:
    async def scenario() -> None:
        app = DoostanApp(tmp_path / "doostan.db")

        async with app.run_test() as pilot:
            await pilot.pause(0.05)

            export_menu = app.query_one("#export-menu", Select)
            export_menu.value = "csv"
            await pilot.pause(0.05)
            assert export_menu.value == Select.BLANK
            assert app.screen.query_one("#file-path", Input).placeholder == "/path/to/file.csv"
            await pilot.press("escape")
            await pilot.pause(0.05)

            import_menu = app.query_one("#import-menu", Select)
            import_menu.value = "html"
            await pilot.pause(0.05)
            assert import_menu.value == Select.BLANK
            assert app.screen.query_one("#file-path", Input).placeholder == "/path/to/file.html"

    asyncio.run(scenario())


def test_tui_toolbar_import_export_buttons_reuse_action_menus(tmp_path: Path) -> None:
    async def scenario() -> None:
        app = DoostanApp(tmp_path / "doostan.db")

        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause(0.05)

            await pilot.click("#toolbar-export")
            await pilot.pause(0.05)
            assert app.screen.query_one("#file-format", Select).value == "csv"
            await pilot.click("#cancel")
            await pilot.pause(0.05)

            await pilot.click("#toolbar-import")
            await pilot.pause(0.05)
            assert app.screen.query_one("#file-format", Select).value == "csv"

    asyncio.run(scenario())


async def _add_address(pilot, app, **fields: str) -> None:
    await pilot.click("#add")
    await pilot.pause(0.05)
    for field, value in fields.items():
        app.screen.query_one(f"#address-{field}", Input).value = value
    await pilot.click("#save")
    await pilot.pause(0.05)


def _wait_for_table(app):
    return app.query_one("#addresses-table", DataTable)


def test_tui_export_then_import_roundtrip(tmp_path: Path) -> None:
    """Drive a real export and import through the worker pipeline."""

    async def scenario() -> None:
        export_file = tmp_path / "people.json"

        source_app = DoostanApp(tmp_path / "source.db")
        async with source_app.run_test(size=(140, 40)) as pilot:
            await pilot.pause(0.05)
            await _add_address(
                pilot,
                source_app,
                name="Export Me",
                email="export@example.com",
                birthday="1990-01-02",
                phone="123",
            )
            assert _wait_for_table(source_app).row_count == 1

            # Export via the toolbar button, filling in the file path.
            await pilot.click("#toolbar-export")
            await pilot.pause(0.05)
            source_app.screen.query_one("#file-format", Select).value = "json"
            source_app.screen.query_one("#file-path", Input).value = str(export_file)
            await pilot.click("#submit")

            # Wait for the background worker to finish writing the file.
            for _ in range(100):
                await pilot.pause(0.05)
                if export_file.exists():
                    break
            assert export_file.exists()

        # Import that file into a fresh database through the UI.
        target_app = DoostanApp(tmp_path / "target.db")
        async with target_app.run_test(size=(140, 40)) as pilot:
            await pilot.pause(0.05)
            assert _wait_for_table(target_app).row_count == 0

            await pilot.click("#toolbar-import")
            await pilot.pause(0.05)
            target_app.screen.query_one("#file-format", Select).value = "json"
            target_app.screen.query_one("#file-path", Input).value = str(export_file)
            await pilot.click("#submit")

            table = _wait_for_table(target_app)
            for _ in range(100):
                await pilot.pause(0.05)
                if table.row_count == 1:
                    break
            assert table.row_count == 1
            assert table.get_row("1")[0] == "Export Me"

    asyncio.run(scenario())


def test_tui_import_missing_file_reports_error(tmp_path: Path) -> None:
    """A failing worker should surface an error and not crash the app."""

    async def scenario() -> None:
        app = DoostanApp(tmp_path / "doostan.db")
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause(0.05)

            await pilot.click("#toolbar-import")
            await pilot.pause(0.05)
            app.screen.query_one("#file-format", Select).value = "json"
            app.screen.query_one("#file-path", Input).value = str(tmp_path / "does-not-exist.json")
            await pilot.click("#submit")

            # Let the worker run and fail; the app should remain responsive.
            for _ in range(60):
                await pilot.pause(0.05)
            assert app.query_one("#addresses-table", DataTable).row_count == 0

    asyncio.run(scenario())


def test_tui_edit_and_delete_without_selection_warn(tmp_path: Path) -> None:
    async def scenario() -> None:
        app = DoostanApp(tmp_path / "doostan.db")
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause(0.05)

            # No rows exist, so edit/delete should no-op (warn) rather than raise.
            await pilot.click("#edit")
            await pilot.pause(0.05)
            await pilot.click("#delete")
            await pilot.pause(0.05)

            # Refresh action and binding should also be safe with no data.
            app.action_refresh()
            await pilot.pause(0.05)
            assert app.query_one("#addresses-table", DataTable).row_count == 0

    asyncio.run(scenario())


def test_progress_screen_status_text_handles_pending_and_counts() -> None:
    screen = FileTransferProgressScreen("Export", "/tmp/out.json", "Collecting current results...")

    assert screen._status_text(0, None) == "Collecting current results..."
    assert screen._status_text(1, 1) == "1 of 1 address"
    assert screen._status_text(2, 3) == "2 of 3 addresses"
