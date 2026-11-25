from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CHAR, CheckConstraint, DateTime, ForeignKey, Index, Numeric, Sequence, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.movimiento import Movimiento

# Consecutivo de folio_operacion (OP-AAAA-NNNNNN)
FOLIO_OPERACION_SEQ = Sequence(
    "transaccion_folio_seq", start=1, minvalue=1, maxvalue=999999, cycle=False, metadata=Base.metadata
)


class Transaccion(Base):
    """Cada SolTransf (8) recibida y su EdoTransf (9). Las columnas capturadas son opcionales porque
    una solicitud incompleta también se registra (RECHAZADA · R06)."""

    __tablename__ = "transaccion"
    __table_args__ = (
        CheckConstraint(
            "sistema_solicitante IN ('RES','VST','VGS','SRE','SPA','GEE','GJA','CIO')", name="sistema_solicitante"
        ),
        CheckConstraint("tipo_operacion IN ('DEPOSITO','RETIRO','TRANSFERENCIA')", name="tipo_operacion"),
        CheckConstraint("estatus IN ('APROBADA','RECHAZADA')", name="estatus"),
        CheckConstraint(
            "(estatus = 'APROBADA' AND codigo_rechazo IS NULL) OR (estatus = 'RECHAZADA' AND codigo_rechazo IS NOT NULL)",
            name="estatus_codigo",
        ),
        CheckConstraint("folio_operacion ~ '^OP-[0-9]{4}-[0-9]{6}$'", name="folio_operacion_formato"),
        Index("ix_transaccion_fecha_hora", "fecha_hora"),
        Index("ix_transaccion_sistema_estatus", "sistema_solicitante", "estatus"),
    )

    folio_operacion: Mapped[str] = mapped_column(CHAR(14), primary_key=True)
    folio_solicitud: Mapped[str | None] = mapped_column(String(20), unique=True)
    sistema_solicitante: Mapped[str | None] = mapped_column(CHAR(3))
    tipo_operacion: Mapped[str | None] = mapped_column(String(13))
    cuenta_origen: Mapped[str | None] = mapped_column(CHAR(10), index=True)
    cuenta_destino: Mapped[str | None] = mapped_column(CHAR(10), index=True)
    importe: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    concepto: Mapped[str | None] = mapped_column(String(100))
    estatus: Mapped[str] = mapped_column(String(9), nullable=False)
    codigo_rechazo: Mapped[str | None] = mapped_column(
        CHAR(3), ForeignKey("codigo_rechazo.codigo", ondelete="RESTRICT")
    )
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    fecha_hora_solicitud: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))

    movimientos: Mapped[list["Movimiento"]] = relationship(
        back_populates="transaccion", order_by="Movimiento.tipo_movimiento.desc()", lazy="raise"
    )
