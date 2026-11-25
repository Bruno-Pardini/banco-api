"""Interfaces (puertos) que el servicio de transacciones necesita de la capa de datos."""

from datetime import datetime
from decimal import Decimal
from typing import Protocol, Self

from app.services.entidades import CuentaInfo, FiltroBitacora, MovimientoRegistro, TransaccionRegistro


class RepoCuentas(Protocol):
    async def bloquear(self, numeros: list[str]) -> dict[str, CuentaInfo]:
        """SELECT ... FOR UPDATE de las cuentas, en orden de número para evitar interbloqueos."""
        ...

    async def actualizar_saldo(self, numero_cuenta: str, saldo: Decimal) -> None: ...


class RepoTransacciones(Protocol):
    async def por_folio_solicitud(self, folio_solicitud: str) -> TransaccionRegistro | None: ...

    async def por_folio_operacion(self, folio_operacion: str) -> TransaccionRegistro | None: ...

    async def siguiente_folio(self, fecha: datetime) -> str: ...

    async def agregar(self, tx: TransaccionRegistro, movimientos: list[MovimientoRegistro]) -> None: ...

    async def listar(self, filtro: FiltroBitacora) -> tuple[int, list[TransaccionRegistro]]: ...


class UnidadDeTrabajo(Protocol):
    @property
    def cuentas(self) -> RepoCuentas: ...

    @property
    def transacciones(self) -> RepoTransacciones: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, *exc: object) -> None:
        """Si no hubo commit, hace rollback."""
        ...

    async def commit(self) -> None:
        """Lanza FolioSolicitudDuplicado si otro request registró el mismo folio_solicitud."""
        ...

    async def rollback(self) -> None: ...
