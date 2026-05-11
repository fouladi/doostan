from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import doost.plugins  # noqa: F401
from doost import db
from doost.address import Address
from doost.plugins.io import ProgressCallback
from doost.plugins.registry import available_formats, get as get_plugin


@dataclass(slots=True, frozen=True)
class AddressFilters:
    name: str = ""
    email: str = ""
    birthday: str = ""
    address: str = ""
    phone: str = ""
    mobile: str = ""
    custom: str = ""
    notes: str = ""

    def has_filters(self) -> bool:
        return any(
            [
                self.name,
                self.email,
                self.birthday,
                self.address,
                self.phone,
                self.mobile,
                self.custom,
                self.notes,
            ]
        )


class AddressService:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._engine, self.session_factory = db.create_engine_and_session(str(db_path))

    def initialize_database(self) -> None:
        db.create_database(str(self.db_path))

    def list_addresses(self, filters: AddressFilters | None = None) -> list[Address]:
        current_filters = filters or AddressFilters()
        with self.session_factory() as session:
            rows = db.get_addresses_by_filter(
                session,
                name=current_filters.name or None,
                email=current_filters.email or None,
                birthday=current_filters.birthday or None,
                address=current_filters.address or None,
                phone=current_filters.phone or None,
                mobile=current_filters.mobile or None,
                custom=current_filters.custom or None,
                notes=current_filters.notes or None,
            )
            if not rows and not current_filters.has_filters():
                rows = db.get_addresses_by_name(session)

        return sorted(rows or [], key=lambda item: (item.name.casefold(), item.email.casefold()))

    def get_address(self, address_id: int) -> Address:
        with self.session_factory() as session:
            return db.get_address_by_id(session, address_id)

    def add_address(
        self,
        *,
        name: str,
        email: str,
        birthday: date | None,
        address: str,
        phone: str,
        mobile: str,
        custom: str,
        notes: str,
    ) -> Address:
        row = Address(
            id=None,
            name=name,
            email=email,
            birthday=birthday,
            address=address,
            phone=phone,
            mobile=mobile,
            custom=custom,
            notes=notes,
        )
        with self.session_factory() as session:
            return db.insert_address(session, row)

    def update_address(
        self,
        address_id: int,
        *,
        name: str,
        email: str,
        birthday: date | None,
        address: str,
        phone: str,
        mobile: str,
        custom: str,
        notes: str,
    ) -> Address:
        row = Address(
            id=None,
            name=name,
            email=email,
            birthday=birthday,
            address=address,
            phone=phone,
            mobile=mobile,
            custom=custom,
            notes=notes,
        )
        with self.session_factory() as session:
            return db.update_address(session, address_id, row)

    def delete_address(self, address_id: int) -> None:
        with self.session_factory() as session:
            db.delete_address_by_id(session, address_id)

    def import_addresses(
        self,
        *,
        path: Path,
        file_format: str,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        plugin = get_plugin(file_format)
        plugin.import_data(path, self.session_factory, progress_callback)

    def export_addresses(
        self,
        *,
        path: Path,
        file_format: str,
        filters: AddressFilters | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        plugin = get_plugin(file_format)
        plugin.export_data(path, self.list_addresses(filters), progress_callback)

    def available_formats(self) -> list[str]:
        return available_formats()

    def close(self) -> None:
        self._engine.dispose()
