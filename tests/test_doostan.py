from collections.abc import Generator
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from doost import address_view, db
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


def test_all(session: Session) -> None:
    a1 = Address(None, "Alpha", "alpha@example.com", date(1990, 1, 2), "Street 1", "111", "211", "family", "One")
    a2 = Address(None, "Beta", "beta@example.com", None, "Street 2", "222", "322", "work", "Two")
    a3 = Address(None, "Gamma", "gamma@example.com", date(1992, 3, 4), "Street 3", "333", "433", "friend", "Three")
    a4 = Address(None, "Delta", "delta@example.com", None, "Street 4", "444", "544", "vip", "Four")
    a5 = Address(None, "Epsilon", "epsilon@example.com", date(1994, 5, 6), "Street 5", "555", "655", "vendor", "Five")

    db.insert_address(session, a1)
    db.insert_address(session, a2)
    db.insert_address(session, a3)
    db.insert_address(session, a4)
    db.insert_address(session, a5)

    a6 = db.get_address_by_id(session, 5)
    assert a6.name == a5.name

    address_view.print_search_result([a1, a2, a3, a4, a5, a6], alternate_row_color="no")
    address_view.print_search_result([], alternate_row_color="no")

    rows = db.get_addresses_by_name(session)
    address_view.print_search_result(rows, alternate_row_color="light_green")

    updated = Address(
        None,
        "Updated",
        "updated@example.com",
        date(2000, 7, 8),
        "New Street",
        "999",
        "888",
        "priority",
        "Changed",
    )
    db.update_address(session, 3, updated)

    a3_new = db.get_address_by_id(session, 3)
    assert a3_new.name == updated.name

    refreshed = db.get_addresses_by_name(session)
    address_view.print_search_result(refreshed, alternate_row_color="light_green")
