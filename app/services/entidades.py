"""Objetos de dominio que viajan entre servicios y repositorios (sin dependencia del ORM)."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass(slots=True)
class CuentaInfo:
    numero_cuenta: str
    saldo: Decimal
    estatus: str
    titular: str


@dataclass(slots=True)
class MovimientoRegistro:
    folio_operacion: str
    tipo_movimiento: str
    numero_cuenta: str
    importe: Decimal
    saldo_resultante: Decimal


@dataclass(slots=True)
class TransaccionRegistro:
    """Fila de la tabla transaccion (FR06-03 capturado + FR06-04 generado)."""

    folio_operacion: str
    folio_solicitud: str | None
    sistema_solicitante: str | None
    tipo_operacion: str | None
    cuenta_origen: str | None
    cuenta_destino: str | None
    importe: Decimal | None
    concepto: str | None
    estatus: str
    codigo_rechazo: str | None
    fecha_hora: datetime
    fecha_hora_solicitud: datetime | None
    movimientos: list[MovimientoRegistro] = field(default_factory=list)


@dataclass(slots=True)
class FiltroBitacora:
    estatus: str | None = None
    tipo_operacion: str | None = None
    sistema_solicitante: str | None = None
    codigo_rechazo: str | None = None
    texto: str | None = None
    desde: date | None = None
    hasta: date | None = None
    pagina: int = 1
    tamano: int = 50
