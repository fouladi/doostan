# Changelog

This listing shows the version of the `Doostan`, the date of
release, and a summary of the changes in that release.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-11-05

### Refactored

* This release replaces the storage backend. Doostan now stores contacts in a
  [DuckDB](https://duckdb.org/) database instead of SQLite. The application API, the Textual TUI,
  and the import/export plugins are unchanged, so day-to-day usage stays the same.

### Changed

* **Storage backend migrated from SQLite to DuckDB.** The database is now
  accessed through SQLAlchemy's DuckDB dialect (`duckdb_engine`), keeping
  the ORM and query code backend-agnostic.
* The `addresses` primary key is now backed by an explicit SQLAlchemy
  `Sequence` (`addresses_id_seq`), because DuckDB has no `SERIAL`/
  auto-increment column type. Automatic `id` assignment behaves as before.
* Removed SQLite-specific engine setup (the `NullPool` connection pool and
  the foreign-keys `PRAGMA` connect listener), which DuckDB does not need.
* Updated the project documentation (`README.md` and `doc/README.md`) to
  describe the DuckDB backend.

### Added

* Runtime dependencies on `duckdb` and `duckdb-engine`.
* Expanded the automated test suite and raised overall coverage above 90%,
  including end-to-end import/export flows through the TUI.

### Removed

* Dependency on the implicit SQLite backend.

### Breaking

* The on-disk storage format changed. Existing SQLite database files
  (the previous `~/.doost.db`) cannot be opened by this version. Data from
  an older SQLite database must be migrated into a new DuckDB database; the
  contents are not converted automatically.

## [1.2.1] - 2026-05-25

### Fixed

* Improved package metadata handling by reading the current version and
  authors directly from `pyproject.toml`.

## [1.2.0] - 2026-05-23

### Added

* `vcard` plugin for improved compatibility with other address book tools.
* Import and export contacts in *RFC 6350* `vCard 4.0` format, with
  compatibility for older sample-style vCards on import.

## [1.1.0] - 2026-05-19

### Added

* Pull-down menu instead of separate input fields for searching
  address elements.

## [1.0.0] - 2026-05-11

### Added

* Initial version.
