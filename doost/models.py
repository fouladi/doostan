from datetime import date

from sqlalchemy import Date, Sequence, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .address import Address


class Base(DeclarativeBase):
    pass


# DuckDB has no SERIAL/auto-increment type, so the primary key is backed by an
# explicit sequence. The sequence is created alongside the table by
# ``Base.metadata.create_all`` and supplies the server-side default for new rows.
_address_id_seq = Sequence("addresses_id_seq")


class Addresses(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(
        _address_id_seq,
        primary_key=True,
        server_default=_address_id_seq.next_value(),
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    birthday: Mapped[date | None] = mapped_column(Date, nullable=True)
    address: Mapped[str] = mapped_column(String, nullable=False, default="")
    phone: Mapped[str] = mapped_column(String, nullable=False, default="")
    mobile: Mapped[str] = mapped_column(String, nullable=False, default="")
    custom: Mapped[str] = mapped_column(String, nullable=False, default="")
    notes: Mapped[str] = mapped_column(String, nullable=False, default="")

    def to_dataclass(self) -> Address:
        return Address(
            id=self.id,
            name=self.name,
            email=self.email,
            birthday=self.birthday,
            address=self.address,
            phone=self.phone,
            mobile=self.mobile,
            custom=self.custom,
            notes=self.notes,
        )
