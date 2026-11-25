from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import Field

from app.core.dominio import EstatusCuenta
from app.schemas.comun import Esquema, Importe, NumeroCuenta


class CuentaCrear(Esquema):
    numero_cuenta: NumeroCuenta
    id_cliente: int = Field(gt=0)
    saldo_inicial: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)] = Decimal("0.00")


class CuentaActualizar(Esquema):
    """El saldo solo cambia por transacciones; aquí solo se activa o inactiva la cuenta."""

    estatus: EstatusCuenta


class CuentaSalida(Esquema):
    numero_cuenta: str
    id_cliente: int
    titular: str
    saldo: Importe
    estatus: EstatusCuenta
    fecha_apertura: date


class MovimientoCuenta(Esquema):
    folio_operacion: str
    tipo_movimiento: str
    importe: Importe
    saldo_resultante: Importe
