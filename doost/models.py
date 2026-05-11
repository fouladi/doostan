from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .address import Address


class Base(DeclarativeBase):
    pass


class Addresses(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
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
