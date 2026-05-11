from sqlalchemy import String, cast, create_engine, delete, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from .address import Address
from .models import Addresses, Base


def create_engine_and_session(db_path: str) -> tuple[Engine, sessionmaker[Session]]:
    """Database is created automatically when the engine/session is created.

    SQLite connections are not pooled (NullPool) so every connection is
    closed as soon as the session that owns it is done. This prevents
    ResourceWarning about unclosed database connections.

    Returns:
        A tuple of (engine, session_factory).
    """
    engine = create_engine(f"sqlite:///{db_path}", future=True, poolclass=NullPool)
    _ensure_schema(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """SQLite does not enable foreign keys by default.

    To preserve the behavior (ON DELETE CASCADE), this function is added.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_database(db_path: str) -> None:
    """Create the Doostan database schema.

    This operation is idempotent and safe to call multiple times.
    Args:
        db_path: Path to the SQLite database file.
    """
    engine = create_engine(f"sqlite:///{db_path}", future=True, poolclass=NullPool)
    try:
        _ensure_schema(engine)
    finally:
        engine.dispose()


def _ensure_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(addresses)")}
        if columns and "birthday" not in columns:
            connection.exec_driver_sql("ALTER TABLE addresses ADD COLUMN birthday DATE")


def _pattern(value: str, is_strict: bool) -> str:
    return value if is_strict else f"%{value}%"


def _apply_filters(
    stmt,
    *,
    name: str | None = None,
    email: str | None = None,
    address: str | None = None,
    phone: str | None = None,
    mobile: str | None = None,
    birthday: str | None = None,
    custom: str | None = None,
    notes: str | None = None,
    is_strict: bool = False,
):
    if name is not None:
        stmt = stmt.where(Addresses.name.ilike(_pattern(name, is_strict)))
    if email is not None:
        stmt = stmt.where(Addresses.email.ilike(_pattern(email, is_strict)))
    if address is not None:
        stmt = stmt.where(Addresses.address.ilike(_pattern(address, is_strict)))
    if phone is not None:
        stmt = stmt.where(Addresses.phone.ilike(_pattern(phone, is_strict)))
    if mobile is not None:
        stmt = stmt.where(Addresses.mobile.ilike(_pattern(mobile, is_strict)))
    if birthday is not None:
        stmt = stmt.where(cast(Addresses.birthday, String).ilike(_pattern(birthday, is_strict)))
    if custom is not None:
        stmt = stmt.where(Addresses.custom.ilike(_pattern(custom, is_strict)))
    if notes is not None:
        stmt = stmt.where(Addresses.notes.ilike(_pattern(notes, is_strict)))
    return stmt


def get_address_by_id(session: Session, address_id: int) -> Address:
    """Retrieve an address entry by its unique ID.

    Args:
        session: Active SQLAlchemy session.
        address_id: Unique identifier of the address entry.
    Returns:
        The matching Address object.
    Raises:
        ValueError: If no address with the given ID exists.
    """
    row = session.get(Addresses, address_id)
    if not row:
        raise ValueError(f"Address with id={address_id} not found.")
    return row.to_dataclass()


def get_addresses_by_name(
    session: Session,
    query_string: str = "",
    is_strict: bool = False,
) -> list[Address]:
    """Retrieve address entries matching a name pattern.

    Args:
        session: Active SQLAlchemy session.
        query_string: Name search string.
        is_strict: If True, match exact name.
    Returns:
        A list of matching address entries.
    """
    stmt = select(Addresses).where(Addresses.name.ilike(_pattern(query_string, is_strict)))
    return [row.to_dataclass() for row in session.scalars(stmt)]


def get_addresses_by_email(
    session: Session,
    query_string: str = "",
    is_strict: bool = False,
) -> list[Address]:
    """Retrieve address entries matching an email pattern.

    Args:
        session: Active SQLAlchemy session.
        query_string: Email search string.
        is_strict: If True, match exact email.
    Returns:
        A list of matching address entries.
    """
    stmt = select(Addresses).where(Addresses.email.ilike(_pattern(query_string, is_strict)))
    return [row.to_dataclass() for row in session.scalars(stmt)]


def get_addresses_by_phone(
    session: Session,
    query_string: str = "",
    is_strict: bool = False,
) -> list[Address]:
    """Retrieve address entries matching a phone or mobile pattern.

    Args:
        session: Active SQLAlchemy session.
        query_string: Phone search string.
        is_strict: If True, require exact phone or mobile matches.
    Returns:
        A list of matching address entries.
    """
    pattern = _pattern(query_string, is_strict)
    stmt = select(Addresses).where(
        Addresses.phone.ilike(pattern) | Addresses.mobile.ilike(pattern)
    )
    return [row.to_dataclass() for row in session.scalars(stmt)]


def get_addresses_by_filter(
    session: Session,
    name: str | None = None,
    email: str | None = None,
    address: str | None = None,
    phone: str | None = None,
    mobile: str | None = None,
    birthday: str | None = None,
    custom: str | None = None,
    notes: str | None = None,
    is_strict: bool = False,
) -> list[Address]:
    """Retrieve addresses matching combined filter criteria.

    All provided filters are combined using logical AND.

    Args:
        session: Active SQLAlchemy session.
        name: Optional name filter.
        email: Optional email filter.
        address: Optional postal address filter.
        phone: Optional phone filter.
        mobile: Optional mobile filter.
        birthday: Optional birthday filter in ISO format.
        custom: Optional custom field filter.
        notes: Optional notes filter.
        is_strict: If True, use exact matching.
    Returns:
        A list of matching addresses, or an empty list if no filters matched.
    """
    stmt = _apply_filters(
        select(Addresses),
        name=name,
        email=email,
        address=address,
        phone=phone,
        mobile=mobile,
        birthday=birthday,
        custom=custom,
        notes=notes,
        is_strict=is_strict,
    )
    return [row.to_dataclass() for row in session.scalars(stmt)]


def _has_duplicate_address(session: Session, address: Address, *, exclude_id: int | None = None) -> bool:
    stmt = select(Addresses).where(
        Addresses.name == address.name,
        Addresses.email == address.email,
        Addresses.birthday == address.birthday,
        Addresses.address == address.address,
        Addresses.phone == address.phone,
        Addresses.mobile == address.mobile,
        Addresses.custom == address.custom,
        Addresses.notes == address.notes,
    )
    if exclude_id is not None:
        stmt = stmt.where(Addresses.id != exclude_id)
    return session.scalar(stmt) is not None


def insert_address(session: Session, address: Address) -> Address:
    """Insert a new address entry into the database.

    Args:
        session: Active SQLAlchemy session.
        address: Address data to insert.
    Raises:
        ValueError: If an identical address already exists.
    """
    if _has_duplicate_address(session, address):
        raise ValueError(f"Address '{address.name}' <{address.email}> already exists!")

    row = Addresses(
        name=address.name,
        email=address.email,
        birthday=address.birthday,
        address=address.address,
        phone=address.phone,
        mobile=address.mobile,
        custom=address.custom,
        notes=address.notes,
    )
    session.add(row)
    session.commit()
    return row.to_dataclass()


def delete_address_by_id(session: Session, address_id: int) -> None:
    """Delete an address entry by its unique ID.

    Args:
        session: Active SQLAlchemy session.
        address_id: ID of the address entry to delete.
    """
    session.execute(delete(Addresses).where(Addresses.id == address_id))
    session.commit()


def delete_address_by_name(session: Session, name: str, email: str) -> None:
    """Delete an address entry by name and email.

    Args:
        session: Active SQLAlchemy session.
        name: Contact name.
        email: Contact email.
    """
    session.execute(delete(Addresses).where(Addresses.name == name).where(Addresses.email == email))
    session.commit()


def update_address(session: Session, address_id: int, address: Address) -> Address:
    """Update an existing address entry.

    Args:
        session: Active SQLAlchemy session.
        address_id: ID of the address entry to update.
        address: New address data.
    Raises:
        ValueError: If the address does not exist or would duplicate another row.
    """
    row = session.get(Addresses, address_id)
    if not row:
        raise ValueError("Address not found")
    if _has_duplicate_address(session, address, exclude_id=address_id):
        raise ValueError(f"Address '{address.name}' <{address.email}> already exists!")

    row.name = address.name
    row.email = address.email
    row.birthday = address.birthday
    row.address = address.address
    row.phone = address.phone
    row.mobile = address.mobile
    row.custom = address.custom
    row.notes = address.notes
    session.commit()
    return row.to_dataclass()
