"""Tests for pw/db.py."""

from collections.abc import Generator
from datetime import date
from pathlib import Path
import sqlite3

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from doost import db
from doost.address import Address
from doost.models import Base


@pytest.fixture
def session() -> Generator[Session]:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(engine, expire_on_commit=False)
    current_session = SessionLocal()
    try:
        yield current_session
    finally:
        current_session.close()
        engine.dispose()


def _insert(
    session: Session,
    name: str,
    email: str,
    *,
    birthday: date | None = None,
    address: str = "",
    phone: str = "",
    mobile: str = "",
    custom: str = "",
    notes: str = "",
) -> Address:
    return db.insert_address(
        session,
        Address(
            id=None,
            name=name,
            email=email,
            birthday=birthday,
            address=address,
            phone=phone,
            mobile=mobile,
            custom=custom,
            notes=notes,
        ),
    )


def test_create_database_is_idempotent(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    db.create_database(db_path)
    db.create_database(db_path)


def test_create_database_migrates_existing_addresses_table(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE addresses (
                id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL,
                email VARCHAR NOT NULL,
                address VARCHAR NOT NULL DEFAULT '',
                phone VARCHAR NOT NULL DEFAULT '',
                mobile VARCHAR NOT NULL DEFAULT '',
                custom VARCHAR NOT NULL DEFAULT '',
                notes VARCHAR NOT NULL DEFAULT ''
            )
            """
        )

    db.create_database(str(db_path))

    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(addresses)")}

    assert "birthday" in columns


def test_get_addresses_by_email_fuzzy(session: Session) -> None:
    _insert(session, "Alice", "alice@example.com", custom="friend")
    _insert(session, "Bob", "bob@work.example", custom="vendor")

    results = db.get_addresses_by_email(session, "example.com")
    assert len(results) == 1
    assert results[0].email == "alice@example.com"


def test_get_addresses_by_email_strict(session: Session) -> None:
    _insert(session, "Alice", "alice@example.com")

    results = db.get_addresses_by_email(session, "alice@example.com", is_strict=True)
    assert len(results) == 1

    results = db.get_addresses_by_email(session, "example.com", is_strict=True)
    assert results == []


def test_get_addresses_by_phone_matches_phone_or_mobile(session: Session) -> None:
    _insert(session, "Alice", "alice@example.com", phone="1000")
    _insert(session, "Bob", "bob@example.com", mobile="2000")

    phone_results = db.get_addresses_by_phone(session, "1000", is_strict=True)
    mobile_results = db.get_addresses_by_phone(session, "2000", is_strict=True)

    assert [item.name for item in phone_results] == ["Alice"]
    assert [item.name for item in mobile_results] == ["Bob"]


def test_get_addresses_by_filter_strict(session: Session) -> None:
    _insert(
        session,
        "Alice Adams",
        "alice@example.com",
        birthday=date(1990, 1, 2),
        custom="family",
        address="Main Street 1",
    )
    _insert(session, "Alice Baker", "alice@work.example", custom="work", address="Second Street 2")

    results = db.get_addresses_by_filter(session, name="Alice Adams", is_strict=True)
    assert len(results) == 1
    assert results[0].email == "alice@example.com"

    results = db.get_addresses_by_filter(session, custom="family", address="Main Street 1", is_strict=True)
    assert len(results) == 1

    results = db.get_addresses_by_filter(session, birthday="1990-01-02", is_strict=True)
    assert len(results) == 1

    results = db.get_addresses_by_filter(session, custom="fam", is_strict=True)
    assert results == []


def test_insert_address_rejects_identical_duplicates(session: Session) -> None:
    entry = Address(
        id=None,
        name="Alice",
        email="alice@example.com",
        birthday=date(1990, 1, 2),
        address="Main Street 1",
        phone="1000",
        mobile="2000",
        custom="family",
        notes="Prefers email",
    )
    db.insert_address(session, entry)

    with pytest.raises(ValueError, match="already exists"):
        db.insert_address(session, entry)


def test_delete_address_by_name(session: Session) -> None:
    _insert(session, "Alice", "alice@example.com")

    db.delete_address_by_name(session, "Alice", "alice@example.com")

    results = db.get_addresses_by_name(session)
    assert results == []


def test_delete_address_by_name_no_match_is_safe(session: Session) -> None:
    _insert(session, "Alice", "alice@example.com")

    db.delete_address_by_name(session, "Nobody", "nobody@example.com")

    results = db.get_addresses_by_name(session)
    assert len(results) == 1


def test_update_address_not_found_raises(session: Session) -> None:
    with pytest.raises(ValueError, match="Address not found"):
        db.update_address(
            session,
            9999,
            Address(
                id=None,
                name="X",
                email="x@example.com",
                birthday=None,
                address="",
                phone="",
                mobile="",
                custom="",
                notes="",
            ),
        )
