from typing import Annotated

from pydantic import Field, field_validator

from app.core.dominio import TipoCliente
from app.schemas.comun import Esquema

Nombre = Annotated[str, Field(min_length=1, max_length=120)]
Correo = Annotated[str, Field(max_length=100, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
Rfc = Annotated[str, Field(pattern=r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$", examples=["SARM900101AB1"])]


class _Limpieza(Esquema):
    @field_validator("nombre", "rfc", "correo", mode="before", check_fields=False)
    @classmethod
    def _quitar_espacios(cls, v: object) -> object:
        return " ".join(v.split()) if isinstance(v, str) else v


class ClienteCrear(_Limpieza):
    nombre: Nombre
    tipo_cliente: TipoCliente = TipoCliente.HUESPED
    rfc: Rfc | None = None
    correo: Correo | None = None


class ClienteActualizar(_Limpieza):
    nombre: Nombre | None = None
    tipo_cliente: TipoCliente | None = None
    rfc: Rfc | None = None
    correo: Correo | None = None


class ClienteSalida(Esquema):
    id_cliente: int
    nombre: str
    tipo_cliente: TipoCliente
    rfc: str | None
    correo: str | None
