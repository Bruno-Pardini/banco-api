"""Contratos de las interfaces de conexión SolTransf (8) y EdoTransf (9), y de la bitácora IG 6.1."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.core.dominio import (
    PATRON_CUENTA,
    PATRON_FOLIO_OPERACION,
    PATRON_FOLIO_SOLICITUD,
    CodigoRechazo,
    Estatus,
    Sistema,
    TipoMovimiento,
    TipoOperacion,
)
from app.schemas.comun import Esquema, Importe


class SolTransf(BaseModel):
    """FR06-03 Solicitud de Transferencia · interfaz SolTransf (8).

    Este modelo documenta el contrato en OpenAPI. La validación real la hace app/services/reglas.py campo
    por campo, porque una solicitud incompleta NO responde 422: se registra RECHAZADA con R06 (Paso 8)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "folio_solicitud": "RES-2026-000001",
                    "sistema_solicitante": "RES",
                    "fecha_hora": "2026-11-15T09:04:12-07:00",
                    "cuenta_origen": "3514126802",
                    "cuenta_destino": "8103021410",
                    "titular_origen": "Mariana Salcido Ruiz",
                    "importe": 16650.00,
                    "concepto": "Pago reservación SMR-2026-00142",
                }
            ]
        }
    )

    folio_solicitud: Annotated[
        str, Field(max_length=20, pattern=PATRON_FOLIO_SOLICITUD, description="XXX-AAAA-NNNNNN; XXX = sistema")
    ]
    sistema_solicitante: Sistema
    fecha_hora: datetime = Field(description="Fecha y hora de envío de la solicitud (ISO 8601)")
    cuenta_origen: Annotated[str, Field(pattern=PATRON_CUENTA, description="10 dígitos")]
    cuenta_destino: Annotated[
        str | None,
        Field(description="Igual a la origen = depósito; vacía o null = retiro; distinta = transferencia"),
    ]
    titular_origen: Annotated[str, Field(min_length=1, max_length=120)]
    importe: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2, description="MXN, mayor a 0.00")]
    concepto: Annotated[str | None, Field(max_length=100, description="Motivo del pago; opcional")] = None


class EdoTransf(Esquema):
    """FR06-04 Comprobante de Transacción · interfaz EdoTransf (9), respuesta HTTP de la 8."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "folio_operacion": "OP-2026-000001",
                    "folio_solicitud": "RES-2026-000001",
                    "fecha_hora": "2026-11-15T09:04:12-07:00",
                    "tipo_operacion": "TRANSFERENCIA",
                    "cuenta_origen": "3514126802",
                    "cuenta_destino": "8103021410",
                    "importe": 16650.00,
                    "estatus": "APROBADA",
                    "codigo_rechazo": None,
                }
            ]
        },
    )

    folio_operacion: Annotated[str, Field(pattern=PATRON_FOLIO_OPERACION)]
    folio_solicitud: str | None
    fecha_hora: datetime = Field(description="Fecha y hora del procesamiento bancario")
    tipo_operacion: TipoOperacion | None
    cuenta_origen: str | None
    cuenta_destino: str | None
    importe: Importe | None
    estatus: Estatus
    codigo_rechazo: CodigoRechazo | None = Field(description="R01 a R06; null si APROBADA")


class MovimientoSalida(Esquema):
    tipo_movimiento: TipoMovimiento
    numero_cuenta: str
    importe: Importe
    saldo_resultante: Importe


class TransaccionBitacora(Esquema):
    """Renglón de la IG 6.1 Bitácora de transacciones."""

    folio_operacion: str
    folio_solicitud: str | None
    sistema_solicitante: Sistema | None
    tipo_operacion: TipoOperacion | None
    cuenta_origen: str | None
    cuenta_destino: str | None
    importe: Importe | None
    estatus: Estatus
    codigo_rechazo: CodigoRechazo | None
    fecha_hora: datetime


class TransaccionDetalle(TransaccionBitacora):
    concepto: str | None
    fecha_hora_solicitud: datetime | None
    motivo_rechazo: str | None = None
    movimientos: list[MovimientoSalida] = []


class CodigoRechazoSalida(Esquema):
    codigo: CodigoRechazo
    motivo: str
