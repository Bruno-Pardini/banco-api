from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CHAR, CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.transaccion import Transaccion


class Movimiento(Base):
    """Retiro (cargo) o depósito (abono) que genera una transacción aprobada.
    PK compuesta (folio_operacion, tipo_movimiento): una transferencia tiene un RETIRO y un DEPOSITO."""

    __tablename__ = "movimiento"
    __table_args__ = (
        CheckConstraint("tipo_movimiento IN ('RETIRO','DEPOSITO')", name="tipo_movimiento"),
        CheckConstraint("importe > 0", name="importe_positivo"),
        CheckConstraint("saldo_resultante >= 0", name="saldo_resultante_no_negativo"),
    )

    folio_operacion: Mapped[str] = mapped_column(
        CHAR(14), ForeignKey("transaccion.folio_operacion", ondelete="RESTRICT"), primary_key=True
    )
    tipo_movimiento: Mapped[str] = mapped_column(String(8), primary_key=True)
    numero_cuenta: Mapped[str] = mapped_column(
        CHAR(10), ForeignKey("cuenta.numero_cuenta", ondelete="RESTRICT"), nullable=False, index=True
    )
    importe: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    saldo_resultante: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    transaccion: Mapped["Transaccion"] = relationship(back_populates="movimientos")
