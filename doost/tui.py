from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.color import Gradient
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, ProgressBar, Select, Static
from textual.worker import Worker, WorkerState

from doost.address import Address, format_birthday, parse_birthday
from doost.plugins.io import ProgressCallback
from doost.services import AddressFilters, AddressService

TRANSFER_PROGRESS_GRADIENT = Gradient.from_colors("#f2b84b", "#f07f4f", "#5fd0b3", quality=80)
FILTER_FIELD_OPTIONS = [
    ("Full name", "name"),
    ("Email", "email"),
    ("Birthday", "birthday"),
    ("Phone", "phone"),
    ("Mobile", "mobile"),
    ("Address", "address"),
    ("Custom", "custom"),
]
FILTER_FIELD_PLACEHOLDERS = {
    "name": "Full name contains...",
    "email": "Email contains...",
    "birthday": "Birthday: YYYY-MM-DD",
    "phone": "Phone contains...",
    "mobile": "Mobile contains...",
    "address": "Address contains...",
    "custom": "Custom contains...",
}


def format_address_details(entry: Address) -> str:
    return "\n".join(
        [
            f"ID: {entry.id}",
            f"Name: {entry.name}",
            f"Email: {entry.email}",
            f"Birthday: {format_birthday(entry.birthday) or '-'}",
            f"Phone: {entry.phone or '-'}",
            f"Mobile: {entry.mobile or '-'}",
            f"Address: {entry.address or '-'}",
            f"Custom: {entry.custom or '-'}",
            f"Notes: {entry.notes or '-'}",
        ]
    )


@dataclass(slots=True, frozen=True)
class AddressFormData:
    name: str
    email: str
    birthday: date | None
    address: str
    phone: str
    mobile: str
    custom: str
    notes: str


@dataclass(slots=True, frozen=True)
class FileActionData:
    file_format: str
    path: str


@dataclass(slots=True, frozen=True)
class FileActionOutcome:
    action: str
    path: Path
    file_format: str


class AddressDetailScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "cancel", "Close")]

    def __init__(self, entry: Address) -> None:
        super().__init__()
        self.entry = entry

    def compose(self) -> ComposeResult:
        with Grid(id="modal-dialog", classes="details-dialog"):
            yield Label(self.entry.name, id="modal-title")
            yield Static(format_address_details(self.entry), id="detail-content")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Close", id="close", variant="primary")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.dismiss(None)


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, question: str) -> None:
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Grid(id="modal-dialog", classes="confirm-dialog"):
            yield Label(self.question, id="modal-title")
            yield Button("Delete", id="confirm", variant="error")
            yield Button("Cancel", id="cancel", variant="primary")

    def action_cancel(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")


class AddressFormScreen(ModalScreen[AddressFormData | None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, title: str, entry: Address | None = None) -> None:
        super().__init__()
        self.screen_title = title
        self.entry = entry

    def compose(self) -> ComposeResult:
        with Grid(id="modal-dialog", classes="address-form"):
            yield Label(self.screen_title, id="modal-title")
            yield Input(value=self.entry.name if self.entry else "", placeholder="Full name", id="address-name")
            yield Input(value=self.entry.email if self.entry else "", placeholder="Email", id="address-email")
            yield Input(
                value=format_birthday(self.entry.birthday) if self.entry else "",
                placeholder="Birthday (YYYY-MM-DD)",
                id="address-birthday",
            )
            yield Input(value=self.entry.phone if self.entry else "", placeholder="Phone", id="address-phone")
            yield Input(value=self.entry.mobile if self.entry else "", placeholder="Mobile", id="address-mobile")
            yield Input(value=self.entry.address if self.entry else "", placeholder="Postal address", id="address-address")
            yield Input(
                value=self.entry.custom if self.entry else "",
                placeholder="Custom: client;family",
                id="address-custom",
            )
            yield Input(value=self.entry.notes if self.entry else "", placeholder="Notes", id="address-notes")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Save", id="save", variant="success")
                yield Button("Cancel", id="cancel", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#address-name", Input).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return

        name = self.query_one("#address-name", Input).value.strip()
        email = self.query_one("#address-email", Input).value.strip()
        birthday_text = self.query_one("#address-birthday", Input).value.strip()
        phone = self.query_one("#address-phone", Input).value.strip()
        mobile = self.query_one("#address-mobile", Input).value.strip()
        postal_address = self.query_one("#address-address", Input).value.strip()
        custom = self.query_one("#address-custom", Input).value.strip()
        notes = self.query_one("#address-notes", Input).value.strip()

        if not name or not email:
            self.notify("Name and email are required.", severity="error")
            return

        try:
            birthday = parse_birthday(birthday_text)
        except ValueError:
            self.notify("Birthday must use YYYY-MM-DD.", severity="error")
            return

        self.dismiss(
            AddressFormData(
                name=name,
                email=email,
                birthday=birthday,
                address=postal_address,
                phone=phone,
                mobile=mobile,
                custom=custom,
                notes=notes,
            )
        )


class FileActionScreen(ModalScreen[FileActionData | None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(
        self,
        title: str,
        formats: list[str],
        default_path: str = "",
        *,
        fixed_format: str | None = None,
    ) -> None:
        super().__init__()
        self.screen_title = title
        self.formats = formats
        self.default_path = default_path
        self.fixed_format = fixed_format

    def _path_placeholder(self) -> str:
        file_format = self.fixed_format or self.formats[0]
        return f"/path/to/file.{file_format}"

    def compose(self) -> ComposeResult:
        options = [(file_format.upper(), file_format) for file_format in self.formats]
        default_format = self.formats[0]

        with Grid(id="modal-dialog", classes="file-form"):
            yield Label(self.screen_title, id="modal-title")
            if self.fixed_format is None:
                yield Select(options, allow_blank=False, value=default_format, id="file-format")
            yield Input(value=self.default_path, placeholder=self._path_placeholder(), id="file-path")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Run", id="submit", variant="success")
                yield Button("Cancel", id="cancel", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#file-path", Input).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return

        file_format = self.fixed_format or str(self.query_one("#file-format", Select).value)
        path = self.query_one("#file-path", Input).value.strip()

        if not path:
            self.notify("A file path is required.", severity="error")
            return

        self.dismiss(FileActionData(file_format=file_format, path=path))


class FileTransferProgressScreen(ModalScreen[None]):
    def __init__(self, title: str, subtitle: str, pending_message: str) -> None:
        super().__init__()
        self.screen_title = title
        self.subtitle = subtitle
        self.pending_message = pending_message

    def compose(self) -> ComposeResult:
        with Grid(id="modal-dialog", classes="progress-dialog"):
            yield Label(self.screen_title, id="modal-title")
            yield Static(self.subtitle, id="progress-subtitle")
            yield ProgressBar(total=None, id="transfer-progress", gradient=TRANSFER_PROGRESS_GRADIENT)
            yield Static(self.pending_message, id="progress-status")

    def update_progress(self, completed: int, total: int | None) -> None:
        if not self.is_mounted:
            return

        self.query_one("#transfer-progress", ProgressBar).update(total=total, progress=completed)
        self.query_one("#progress-status", Static).update(self._status_text(completed, total))

    def _status_text(self, completed: int, total: int | None) -> str:
        if total is None:
            return self.pending_message

        noun = "address" if total == 1 else "addresses"
        return f"{completed} of {total} {noun}"


class DoostanApp(App[None]):
    CSS_PATH = "tui.tcss"
    TITLE = "Doostan"
    SUB_TITLE = "Address book manager"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("a", "add_address", "Add"),
        Binding("e", "edit_address", "Edit"),
        Binding("d", "delete_address", "Delete"),
        Binding("i", "import_addresses", "Import"),
        Binding("x", "export_addresses", "Export"),
    ]

    def __init__(self, db_path: Path) -> None:
        super().__init__()
        self.service = AddressService(db_path)
        self.addresses: list[Address] = []
        self.selected_address_id: int | None = None
        self._file_action_worker: Worker[FileActionOutcome] | None = None
        self._file_action_screen: FileTransferProgressScreen | None = None
        self._open_details_on_row_select = False

    def compose(self) -> ComposeResult:
        file_menu_options = [(file_format.upper(), file_format) for file_format in self.service.available_formats()]

        yield Header(show_clock=True)
        with Horizontal(id="app-shell"):
            with Vertical(id="sidebar"):
                yield Static("Selected", classes="panel-title")
                yield Static("No address selected.", id="details", classes="panel-block")
                yield Static("", id="stats", classes="sidebar-status")
                yield Static("Find", classes="panel-title")
                with Horizontal(classes="filter-row"):
                    yield Select(FILTER_FIELD_OPTIONS, allow_blank=False, value="name", id="filter-field")
                    yield Input(placeholder=FILTER_FIELD_PLACEHOLDERS["name"], id="filter-value")
                with Horizontal(classes="sidebar-actions"):
                    yield Button("Apply", id="apply-filters", variant="primary")
                    yield Button("Clear", id="clear-filters")
                with Horizontal(classes="sidebar-actions"):
                    yield Select(file_menu_options, prompt="Import", id="import-menu", compact=True)
                    yield Select(file_menu_options, prompt="Export", id="export-menu", compact=True)
            with Vertical(id="main-pane"):
                yield Static("Addresses", classes="panel-title")
                with Horizontal(id="toolbar"):
                    yield Button("Add", id="add", variant="success", compact=True)
                    yield Button("Edit", id="edit", compact=True)
                    yield Button("Delete", id="delete", variant="error", compact=True)
                    yield Button("Import", id="toolbar-import", compact=True)
                    yield Button("Export", id="toolbar-export", compact=True)
                yield DataTable(id="addresses-table", zebra_stripes=True, cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self.service.initialize_database()
        table = self.query_one("#addresses-table", DataTable)
        table.add_columns("Name", "Email", "Birthday", "Phone", "Mobile", "Custom", "ID")
        table.focus()
        self.refresh_table()

    def on_unmount(self) -> None:
        self.service.close()

    def current_filters(self) -> AddressFilters:
        filter_value = self.query_one("#filter-value", Input).value.strip()
        if not filter_value:
            return AddressFilters()

        return AddressFilters(**{self._selected_filter_field(): filter_value})

    def _selected_filter_field(self) -> str:
        selected_value = self.query_one("#filter-field", Select).value
        if isinstance(selected_value, str) and selected_value in FILTER_FIELD_PLACEHOLDERS:
            return selected_value
        return "name"

    def _sync_filter_placeholder(self) -> None:
        self.query_one("#filter-value", Input).placeholder = FILTER_FIELD_PLACEHOLDERS[self._selected_filter_field()]

    def selected_address(self) -> Address | None:
        if self.selected_address_id is None:
            return None
        return next((item for item in self.addresses if item.id == self.selected_address_id), None)

    def _address_id_from_row_key(self, row_key: object) -> int:
        value = getattr(row_key, "value", row_key)
        return int(str(value))

    def refresh_table(self, preferred_address_id: int | None = None) -> None:
        table = self.query_one("#addresses-table", DataTable)
        self.addresses = self.service.list_addresses(self.current_filters())
        table.clear()

        for item in self.addresses:
            table.add_row(
                item.name,
                item.email,
                format_birthday(item.birthday),
                item.phone,
                item.mobile,
                item.custom,
                str(item.id or ""),
                key=str(item.id),
            )

        if self.addresses:
            selected_index = 0
            if preferred_address_id is not None:
                selected_index = next(
                    (index for index, item in enumerate(self.addresses) if item.id == preferred_address_id),
                    0,
                )
            self.selected_address_id = self.addresses[selected_index].id
            table.move_cursor(row=selected_index, column=0)
        else:
            self.selected_address_id = None

        self.refresh_sidebar()

    def refresh_sidebar(self) -> None:
        stats = self.query_one("#stats", Static)
        entry = self.selected_address()
        stats.update(f"{len(self.addresses)} address(es) loaded")

        if entry is None:
            self.query_one("#details", Static).update("No address selected.")
            return

        self.query_one("#details", Static).update(format_address_details(entry))

    def action_refresh(self) -> None:
        self.refresh_table()
        self.notify("Addresses refreshed.")

    def action_add_address(self) -> None:
        self.push_screen(AddressFormScreen("Add address"), self._handle_add_result)

    def action_edit_address(self) -> None:
        entry = self.selected_address()
        if entry is None:
            self.notify("Select an address first.", severity="warning")
            return

        self.push_screen(AddressFormScreen("Edit address", entry), self._handle_edit_result)

    def action_delete_address(self) -> None:
        entry = self.selected_address()
        if entry is None:
            self.notify("Select an address first.", severity="warning")
            return

        self.push_screen(ConfirmScreen(f"Delete '{entry.name}'?"), self._handle_delete_result)

    def action_import_addresses(self) -> None:
        self.open_import_screen()

    def open_import_screen(self, file_format: str | None = None) -> None:
        self.push_screen(
            FileActionScreen(
                self._file_action_title("Import addresses", file_format),
                self.service.available_formats(),
                fixed_format=file_format,
            ),
            self._handle_import_result,
        )

    def action_export_addresses(self) -> None:
        self.open_export_screen()

    def open_export_screen(self, file_format: str | None = None) -> None:
        self.push_screen(
            FileActionScreen(
                self._file_action_title("Export current results", file_format),
                self.service.available_formats(),
                fixed_format=file_format,
            ),
            self._handle_export_result,
        )

    def _file_action_title(self, base_title: str, file_format: str | None) -> str:
        if file_format is None:
            return base_title
        return f"{base_title} ({file_format.upper()})"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "apply-filters":
            self.refresh_table()
        elif button_id == "clear-filters":
            self.query_one("#filter-field", Select).value = "name"
            self.query_one("#filter-value", Input).value = ""
            self._sync_filter_placeholder()
            self.refresh_table()
        elif button_id == "add":
            self.action_add_address()
        elif button_id == "edit":
            self.action_edit_address()
        elif button_id == "delete":
            self.action_delete_address()
        elif button_id == "toolbar-import":
            self.action_import_addresses()
        elif button_id == "toolbar-export":
            self.action_export_addresses()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter-value":
            self.refresh_table()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "filter-field":
            self._sync_filter_placeholder()
            return

        if event.select.id not in {"import-menu", "export-menu"} or event.value == Select.BLANK:
            return

        file_format = str(event.value)
        event.select.value = Select.BLANK

        if event.select.id == "import-menu":
            self.open_import_screen(file_format)
            return

        self.open_export_screen(file_format)

    def on_key(self, event: events.Key) -> None:
        if event.key != "enter":
            return

        table = self.query_one("#addresses-table", DataTable)
        if table.has_focus and self.selected_address() is not None:
            self._open_details_on_row_select = True

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.selected_address_id = self._address_id_from_row_key(event.row_key)
        self.refresh_sidebar()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.selected_address_id = self._address_id_from_row_key(event.row_key)
        self.refresh_sidebar()
        if self._open_details_on_row_select:
            self._open_details_on_row_select = False
            entry = self.selected_address()
            if entry is not None:
                self.push_screen(AddressDetailScreen(entry))

    def _handle_add_result(self, result: AddressFormData | None) -> None:
        if result is None:
            return

        try:
            entry = self.service.add_address(
                name=result.name,
                email=result.email,
                birthday=result.birthday,
                address=result.address,
                phone=result.phone,
                mobile=result.mobile,
                custom=result.custom,
                notes=result.notes,
            )
        except (SystemExit, ValueError) as error:
            self.notify(str(error), severity="error", timeout=8)
            return

        self.refresh_table(preferred_address_id=entry.id)
        self.notify(f"Added '{entry.name}'.")

    def _handle_edit_result(self, result: AddressFormData | None) -> None:
        entry = self.selected_address()
        if result is None or entry is None or entry.id is None:
            return

        try:
            updated = self.service.update_address(
                entry.id,
                name=result.name,
                email=result.email,
                birthday=result.birthday,
                address=result.address,
                phone=result.phone,
                mobile=result.mobile,
                custom=result.custom,
                notes=result.notes,
            )
        except ValueError as error:
            self.notify(str(error), severity="error", timeout=8)
            return

        self.refresh_table(preferred_address_id=updated.id)
        self.notify(f"Updated '{updated.name}'.")

    def _handle_delete_result(self, confirmed: bool) -> None:
        entry = self.selected_address()
        if not confirmed or entry is None or entry.id is None:
            return

        self.service.delete_address(entry.id)
        self.refresh_table()
        self.notify(f"Deleted '{entry.name}'.")

    def _handle_import_result(self, result: FileActionData | None) -> None:
        if result is None:
            return

        self._start_file_action("import", result)

    def _handle_export_result(self, result: FileActionData | None) -> None:
        if result is None:
            return

        self._start_file_action("export", result)

    def _start_file_action(self, action: str, result: FileActionData) -> None:
        path = Path(result.path).expanduser()
        pending_message = "Scanning file..." if action == "import" else "Collecting current results..."
        title = f"{action.title()}ing {result.file_format.upper()} addresses"
        screen = FileTransferProgressScreen(title=title, subtitle=str(path), pending_message=pending_message)

        self._file_action_screen = screen
        self.push_screen(screen)

        if action == "import":
            self._file_action_worker = self._run_import_job(path, result.file_format, screen)
            return

        self._file_action_worker = self._run_export_job(path, result.file_format, self.current_filters(), screen)

    def _make_progress_callback(
        self,
        screen: FileTransferProgressScreen,
    ) -> ProgressCallback:
        last_bucket = -1

        def callback(completed: int, total: int | None) -> None:
            nonlocal last_bucket

            if total not in {None, 0}:
                bucket = int((completed * 100) / total)
                if bucket == last_bucket and completed not in {0, total}:
                    return
                last_bucket = bucket

            self.call_from_thread(screen.update_progress, completed, total)

        return callback

    @work(thread=True, group="file-actions", exit_on_error=False)
    def _run_import_job(
        self,
        path: Path,
        file_format: str,
        screen: FileTransferProgressScreen,
    ) -> FileActionOutcome:
        progress_callback = self._make_progress_callback(screen)
        progress_callback(0, None)
        self.service.import_addresses(
            path=path,
            file_format=file_format,
            progress_callback=progress_callback,
        )
        return FileActionOutcome(action="import", path=path, file_format=file_format)

    @work(thread=True, group="file-actions", exit_on_error=False)
    def _run_export_job(
        self,
        path: Path,
        file_format: str,
        filters: AddressFilters,
        screen: FileTransferProgressScreen,
    ) -> FileActionOutcome:
        progress_callback = self._make_progress_callback(screen)
        progress_callback(0, None)
        self.service.export_addresses(
            path=path,
            file_format=file_format,
            filters=filters,
            progress_callback=progress_callback,
        )
        return FileActionOutcome(action="export", path=path, file_format=file_format)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker is not self._file_action_worker:
            return

        if event.state not in {WorkerState.SUCCESS, WorkerState.ERROR, WorkerState.CANCELLED}:
            return

        screen = self._file_action_screen
        self._file_action_worker = None
        self._file_action_screen = None

        if screen is not None and screen.is_mounted:
            screen.dismiss(None)

        if event.state == WorkerState.SUCCESS:
            outcome = event.worker.result
            if outcome is None:
                return
            self._handle_file_action_success(outcome)
            return

        error = event.worker.error
        message = str(error) if error else "The file action did not finish."
        self.notify(message, severity="error", timeout=8)

    def _handle_file_action_success(self, outcome: FileActionOutcome) -> None:
        if outcome.action == "import":
            self.refresh_table()
            self.notify(f"Imported addresses from {outcome.path}.")
            return

        self.notify(f"Exported addresses to {outcome.path}.")
