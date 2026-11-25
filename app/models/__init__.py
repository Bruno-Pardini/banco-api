"""Modelos ORM: las 5 tablas del modelo relacional del Banco (Figura 5 del Paso 8)."""

from app.models.cliente import Cliente
from app.models.codigo_rechazo import CodigoRechazoModel
from app.models.cuenta import Cuenta
from app.models.movimiento import Movimiento
from app.models.transaccion import Transaccion

__all__ = ["Cliente", "CodigoRechazoModel", "Cuenta", "Movimiento", "Transaccion"]
