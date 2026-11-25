from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CHAR, CheckConstraint, Date, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.cliente import Cliente


class Cuenta(Base):
    __tablename__ = "cuenta"
    __table_args__ = (
        CheckConstraint("numero_cuenta ~ '^[0-9]{10}$'", name="numero_cuenta_10_digitos"),
        CheckConstraint("saldo >= 0", name="saldo_no_negativo"),
        CheckConstraint("estatus IN ('ACTIVA','INACTIVA')", name="estatus"),
    )

    numero_cuenta: Mapped[str] = mapped_column(CHAR(10), primary_key=True)
    id_cliente: Mapped[int] = mapped_column(
        Integer, ForeignKey("cliente.id_cliente", ondelete="RESTRICT"), nullable=False, index=True
    )
    saldo: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default="0")
    estatus: Mapped[str] = mapped_column(String(8), nullable=False, server_default="ACTIVA")
    fecha_apertura: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())

    cliente: Mapped["Cliente"] = relationship(back_populates="cuentas")
