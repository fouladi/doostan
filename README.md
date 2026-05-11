# Doostan

Doostan is a terminal address book built around a local SQLite
database. It uses a Textual TUI for browsing, filtering, editing,
importing, and exporting contact data without relying on a cloud sync
service.

The name `doostan` is Persian for `friends`.

## Features

- Store addresses locally in `~/.doost.db`
- Browse contacts in a Textual table with keyboard-driven navigation
- Filter, add, update, and delete addresses from an interactive TUI
- Search by name, email, birthday, phone, mobile, address, or custom field
- Import and export address data as `html`, `json`, or `csv`
- Extend file I/O through the plugin registry in [`doost/plugins`](doost/plugins)

## Requirements

- Python `3.14+`
- `pip`

## Installation

Install the project from the repository root:

```bash
python -m pip install .
```

For local development, install it in editable mode and add the dev
tools:

```bash
python -m pip install -e .
python -m pip install -r requirements-dev.txt
```

If you prefer installing only the runtime dependencies without packaging
the project, `requirements.txt` is also available:

```bash
python -m pip install -r requirements.txt
```

## Quick Start

Launch the application:

```bash
python doostan.py
```

Launch against a custom database path:

```bash
python doostan.py --db-path ~/addresses.db
```

Show the version:

```bash
python doostan.py --version
```

## Output Example

![Doostan list output](doc/images/doostan.png)

## Commands

The Textual application supports these workflows:

- Search addresses by name, email, birthday, phone, mobile, address, or custom value
- Add, edit, and delete addresses with modal forms
- Import addresses from `html`, `json`, or `csv`
- Export the current filtered result set to `html`, `json`, or `csv`
- Navigate entirely from the keyboard with footer key hints

## Project Layout

- [`doostan.py`](doostan.py): launcher for the Textual app
- [`doost/tui.py`](doost/tui.py): Textual application and modal dialogs
- [`doost/services.py`](doost/services.py): reusable address operations
- [`doost/`](doost): core address, database, and formatting logic
- [`doost/plugins/`](doost/plugins): import/export plugins and registry
- [`tests/`](tests): unit tests

## Development

Run the test suite from the repository root:

```bash
pytest
```

Lint the codebase with Ruff:

```bash
ruff check .
```

## License

This project is licensed under the terms of the [MIT License](LICENSE).
