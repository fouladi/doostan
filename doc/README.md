# Doostan – Technical Documentation

## Overview

Doostan is a terminal address book backed by SQLite and a
[Textual](https://textual.textualize.io/) TUI. The application supports
listing, filtering, adding, editing, deleting, importing, and exporting
address entries.

The codebase is organized around four layers:

1. `doostan.py` launches the app.
2. `doost/tui.py` owns the Textual UI and modal workflows.
3. `doost/services.py` exposes the address-oriented application API.
4. `doost/db.py`, `doost/models.py`, and `doost/plugins/` handle persistence and file I/O.

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

## TUI

[`doost/tui.py`](../doost/tui.py) keeps the Doostan interaction model
applied to address records:

- Sidebar filters for name, email, birthday, phone, mobile, address, and custom data
- Main table showing `Name`, `Email`, `Birthday`, `Phone`, `Mobile`, `Custom`, and `ID`
- Detail panel for the selected record, including birthday, postal address, and notes
- Modal add/edit forms
- Import/export dialogs and progress feedback

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
is unchanged. The built-in plugins serialize address entries in
these formats:

- `csv`: `name,email,birthday,address,phone,mobile,custom,notes`
- `json`: one object per address entry
- `html`: one `<li>` per address entry with `data-*` attributes

Plugins implement the protocol in [`doost/plugins/io.py`](../doost/plugins/io.py)
and are invoked exclusively through `AddressService`.

## Testing

The test suite covers:

- database CRUD and filtering
- service behavior and plugin delegation
- CSV / JSON / HTML import-export plugins
- TUI CRUD and dialog flows
- terminal table formatting

Run everything with:

```bash
pytest
```
