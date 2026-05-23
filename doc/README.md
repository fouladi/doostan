# Doostan Design Notes

This document covers the application design and internal structure. For
installation, running the app, and user-facing usage, see the [project README](../README.md).

## Overview

Doostan is a terminal address book backed by SQLite and a
[Textual](https://textual.textualize.io/) TUI. The application supports
listing, searching, adding, editing, deleting, importing, and exporting
address entries.

The codebase is organized around four layers:

1. `doostan.py` launches the app.
2. `doost/tui.py` owns the Textual UI and modal workflows.
3. `doost/services.py` exposes the address-oriented application API.
4. `doost/db.py`, `doost/models.py`, and `doost/plugins/` handle
   persistence and file I/O.

## Design Goals

- Keep data local and simple by default with SQLite storage.
- Favor keyboard-first interaction through a Textual TUI.
- Separate UI, application logic, and persistence clearly enough to test
  each layer independently.
- Keep import and export extensible through a small plugin registry.

## Data Model

The core record lives in [`doost/address.py`](../doost/address.py):

```python
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
```

`notes` is intentionally separate from `custom`. `custom` works well for
short labels or categories, while `notes` carries longer freeform
context. Birthdays use ISO date format: `YYYY-MM-DD`.

## Database Layer

[`doost/models.py`](../doost/models.py) maps the dataclass to a single
`addresses` table. [`doost/db.py`](../doost/db.py) exposes focused database
operations:

- `get_address_by_id`
- `get_addresses_by_name`
- `get_addresses_by_email`
- `get_addresses_by_phone`
- `get_addresses_by_filter`
- `insert_address`
- `update_address`
- `delete_address_by_id`
- `delete_address_by_name`

The DB layer rejects identical duplicate address rows and returns
dataclass instances back to the caller.

## Service Layer

[`doost/services.py`](../doost/services.py) provides the main application API:

- `AddressService.initialize_database()`
- `AddressService.list_addresses(filters=None)`
- `AddressService.get_address(id)`
- `AddressService.add_address(...)`
- `AddressService.update_address(id, ...)`
- `AddressService.delete_address(id)`
- `AddressService.import_addresses(path, file_format, progress_callback=None)`
- `AddressService.export_addresses(path, file_format, filters=None, progress_callback=None)`

Filtering is represented by `AddressFilters`, which supports:

- `name`
- `email`
- `birthday`
- `address`
- `phone`
- `mobile`
- `custom`
- `notes`

The service layer can combine multiple fields at once. The current TUI
intentionally exposes a simpler search interaction and maps one selected
sidebar field into `AddressFilters` at a time.

## TUI Design

[`doost/tui.py`](../doost/tui.py) keeps the interaction model applied to
address records:

- A sidebar with selected-record details, result count, search controls,
  and import/export menus
- A search row with a dropdown for `Full name`, `Email`, `Birthday`,
  `Phone`, `Mobile`, `Address`, or `Custom`, plus one value input
- `Apply` and `Clear` actions for the current search term
- A main table showing `Name`, `Email`, `Birthday`, `Phone`, `Mobile`,
  `Custom`, and `ID`
- Modal screens for add, edit, delete confirmation, file actions, and
  progress reporting

This design keeps the primary view compact while still exposing the full
address record in the selected-item details panel and modal screens.

Key bindings:

- `a`: add address
- `e`: edit selected address
- `d`: delete selected address
- `i`: import addresses
- `x`: export current results
- `r`: refresh
- `q`: quit

## Import / Export Plugins

The plugin registry in [`doost/plugins/registry.py`](../doost/plugins/registry.py)
loads supported file adapters. The built-in plugins serialize address
entries in these formats:

- `csv`: `name,email,birthday,address,phone,mobile,custom,notes`
- `json`: one object per address entry
- `html`: one `<li>` per address entry with `data-*` attributes
- `vcard`: RFC 6350 vCard 4.0 with one `BEGIN:VCARD` / `END:VCARD` block per address entry

Plugins implement the protocol in [`doost/plugins/io.py`](../doost/plugins/io.py)
and are invoked exclusively through `AddressService`.

## Testing Strategy

The test suite covers:

- database CRUD and filtering
- service behavior and plugin delegation
- CSV / JSON / HTML / vCard import-export plugins
- TUI CRUD and dialog flows
- terminal table formatting

Run everything with:

```bash
pytest
```
