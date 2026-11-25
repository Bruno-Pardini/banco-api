"""Reglas de negocio puras de SolTransf (8) → EdoTransf (9). Sin BD ni HTTP: se prueban con pytest.

Orden de evaluación (tabla de tareas del Paso 8):
  R06 solicitud incompleta / importe <= 0  →  Valida cuentas: R01, R02, R04  →  Verifica fondo: R03
"""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from pydantic import Field, TypeAdapter, ValidationError

from app.core.dominio import (
    PATRON_CUENTA,
    PATRON_FOLIO_SOLICITUD,
    CodigoRechazo,
    EstatusCuenta,
    Sistema,
    TipoMovimiento,
    TipoOperacion,
)
from app.core.tiempo import a_local_sin_zona
from app.services.entidades import CuentaInfo

_folio: TypeAdapter[str] = TypeAdapter(Annotated[str, Field(max_length=20, pattern=PATRON_FOLIO_SOLICITUD)])
_sistema: TypeAdapter[Sistema] = TypeAdapter(Sistema)
_fecha: TypeAdapter[datetime] = TypeAdapter(datetime)
_cuenta: TypeAdapter[str] = TypeAdapter(Annotated[str, Field(pattern=PATRON_CUENTA)])
_titular: TypeAdapter[str] = TypeAdapter(Annotated[str, Field(min_length=1, max_length=120)])
_importe: TypeAdapter[Decimal] = TypeAdapter(Annotated[Decimal, Field(max_digits=12, decimal_places=2, allow_inf_nan=False)])
_concepto: TypeAdapter[str] = TypeAdapter(Annotated[str, Field(max_length=100)])

CAMPOS_OBLIGATORIOS = (
    "folio_solicitud",
    "sistema_solicitante",
    "fecha_hora",
    "cuenta_origen",
    "cuenta_destino",  # la llave debe venir; "" o null significan retiro
    "titular_origen",
    "importe",
)


@dataclass(slots=True)
class DatosCapturados:
    """Lo que se pudo leer de la SolTransf (8). Un campo inválido queda en None y se anota en errores."""

    folio_solicitud: str | None = None
    sistema_solicitante: str | None = None
    fecha_hora_solicitud: datetime | None = None
    cuenta_origen: str | None = None
    cuenta_destino: str | None = None
    titular_origen: str | None = None
    importe: Decimal | None = None
    concepto: str | None = None
    errores: list[str] = field(default_factory=list)

    @property
    def completa(self) -> bool:
        return not self.errores


def _limpiar_texto(v: Any) -> Any:
    return " ".join(v.split()) if isinstance(v, str) else v


def _leer(adaptador: TypeAdapter[Any], valor: Any, nombre: str, errores: list[str]) -> Any:
    try:
        return adaptador.validate_python(valor, strict=nombre in {"cuenta_origen", "cuenta_destino"})
    except ValidationError as e:
        errores.append(f"{nombre}: {e.errors()[0]['msg']}")
        return None


def validar_solicitud(datos: dict[str, Any], zona: ZoneInfo) -> DatosCapturados:
    """Valida el FR06-03 campo por campo. Nunca lanza excepción: los problemas se vuelven R06."""
    r = DatosCapturados()
    e = r.errores

    for campo in CAMPOS_OBLIGATORIOS:
        if campo not in datos:
            e.append(f"{campo}: campo obligatorio")
        elif campo != "cuenta_destino" and datos[campo] in (None, ""):
            e.append(f"{campo}: no puede ir vacío")

    if datos.get("folio_solicitud") not in (None, ""):
        r.folio_solicitud = _leer(_folio, _limpiar_texto(datos["folio_solicitud"]), "folio_solicitud", e)
    if datos.get("sistema_solicitante") not in (None, ""):
        r.sistema_solicitante = _leer(_sistema, datos["sistema_solicitante"], "sistema_solicitante", e)
    if datos.get("fecha_hora") not in (None, ""):
        f = _leer(_fecha, datos["fecha_hora"], "fecha_hora", e)
        r.fecha_hora_solicitud = a_local_sin_zona(f, zona) if f is not None else None
    if datos.get("cuenta_origen") not in (None, ""):
        r.cuenta_origen = _leer(_cuenta, datos["cuenta_origen"], "cuenta_origen", e)
    if datos.get("cuenta_destino") not in (None, ""):
        r.cuenta_destino = _leer(_cuenta, datos["cuenta_destino"], "cuenta_destino", e)
    if datos.get("titular_origen") not in (None, ""):
        r.titular_origen = _leer(_titular, _limpiar_texto(datos["titular_origen"]), "titular_origen", e)
    if datos.get("importe") not in (None, "") and not isinstance(datos.get("importe"), bool):
        r.importe = _leer(_importe, datos["importe"], "importe", e)
        if r.importe is not None:
            r.importe = r.importe.quantize(Decimal("0.01"))
        if r.importe is not None and r.importe <= 0:
            e.append("importe: debe ser mayor a 0.00")
    elif isinstance(datos.get("importe"), bool):
        e.append("importe: debe ser numérico")
    if datos.get("concepto") not in (None, ""):
        r.concepto = _leer(_concepto, _limpiar_texto(datos["concepto"]), "concepto", e)

    if r.folio_solicitud and r.sistema_solicitante and not r.folio_solicitud.startswith(f"{r.sistema_solicitante}-"):
        e.append("folio_solicitud: el prefijo XXX debe ser el sistema_solicitante")
    return r


def tipo_operacion(cuenta_origen: str | None, cuenta_destino: str | None) -> TipoOperacion | None:
    """Igual a la origen = depósito; vacía = retiro; distinta = transferencia."""
    if cuenta_origen is None:
        return None
    if cuenta_destino is None:
        return TipoOperacion.RETIRO
    if cuenta_destino == cuenta_origen:
        return TipoOperacion.DEPOSITO
    return TipoOperacion.TRANSFERENCIA


def normalizar_nombre(nombre: str) -> str:
    """Comparación de titular sin acentos, mayúsculas ni espacios repetidos."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", nombre) if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", sin_acentos).strip().casefold()


def evaluar(
    tipo: TipoOperacion,
    importe: Decimal,
    titular_origen: str,
    origen: CuentaInfo | None,
    destino: CuentaInfo | None,
) -> CodigoRechazo | None:
    """Devuelve el código de rechazo o None si la operación se aprueba."""
    if origen is None or origen.estatus != EstatusCuenta.ACTIVA:
        return CodigoRechazo.R01
    if tipo is TipoOperacion.TRANSFERENCIA and (destino is None or destino.estatus != EstatusCuenta.ACTIVA):
        return CodigoRechazo.R02
    if normalizar_nombre(titular_origen) != normalizar_nombre(origen.titular):
        return CodigoRechazo.R04
    if tipo in (TipoOperacion.RETIRO, TipoOperacion.TRANSFERENCIA) and origen.saldo < importe:
        return CodigoRechazo.R03
    return None


@dataclass(slots=True, frozen=True)
class MovimientoCalculado:
    tipo_movimiento: TipoMovimiento
    numero_cuenta: str
    importe: Decimal
    saldo_resultante: Decimal


def calcular_movimientos(
    tipo: TipoOperacion, importe: Decimal, origen: CuentaInfo, destino: CuentaInfo | None
) -> list[MovimientoCalculado]:
    """Ejecuta cargo Cta Origen (RETIRO) y/o abono Cta Destino (DEPOSITO)."""
    movs: list[MovimientoCalculado] = []
    if tipo in (TipoOperacion.RETIRO, TipoOperacion.TRANSFERENCIA):
        movs.append(MovimientoCalculado(TipoMovimiento.RETIRO, origen.numero_cuenta, importe, origen.saldo - importe))
    if tipo is TipoOperacion.TRANSFERENCIA:
        assert destino is not None
        movs.append(MovimientoCalculado(TipoMovimiento.DEPOSITO, destino.numero_cuenta, importe, destino.saldo + importe))
    if tipo is TipoOperacion.DEPOSITO:
        movs.append(MovimientoCalculado(TipoMovimiento.DEPOSITO, origen.numero_cuenta, importe, origen.saldo + importe))
    return movs


def formatear_folio_operacion(anio: int, consecutivo: int) -> str:
    """OP-AAAA-NNNNNN (CHAR(14))."""
    if not 1 <= consecutivo <= 999_999:
        raise ValueError("consecutivo fuera de rango")
    return f"OP-{anio:04d}-{consecutivo:06d}"
