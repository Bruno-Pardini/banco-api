from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

# NUMERIC(12,2) se devuelve como número JSON (el contrato del Paso 8 muestra "importe": 16650.00)
Importe = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")]
NumeroCuenta = Annotated[str, Field(pattern=r"^\d{10}$", examples=["3514126802"])]

T = TypeVar("T")


class Esquema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class Pagina(Esquema, Generic[T]):
    total: int
    pagina: int
    tamano: int
    datos: list[T]


class ErrorRespuesta(BaseModel):
    codigo: str = Field(examples=["NO_ENCONTRADO"])
    mensaje: str = Field(examples=["No existe la transacción OP-2026-000099"])
    detalles: object | None = None


class Salud(BaseModel):
    estado: str = Field(examples=["ok"])
    base_de_datos: str = Field(examples=["ok"])
    version: str
