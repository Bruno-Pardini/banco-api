from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.cuenta import Cuenta


class Cliente(Base):
    __tablename__ = "cliente"
    __table_args__ = (
        CheckConstraint("tipo_cliente IN ('HUESPED','EMPRESA','HOTEL','PROVEEDOR')", name="tipo_cliente"),
    )

    id_cliente: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo_cliente: Mapped[str] = mapped_column(String(9), nullable=False)
    rfc: Mapped[str | None] = mapped_column(String(13), unique=True)
    correo: Mapped[str | None] = mapped_column(String(100))

    cuentas: Mapped[list["Cuenta"]] = relationship(back_populates="cliente")
