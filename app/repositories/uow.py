"""Unidad de trabajo sobre AsyncSession: un commit = una transacción de PostgreSQL."""

from typing import Self

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import FolioSolicitudDuplicado
from app.repositories.cuentas import RepoCuentasSQL
from app.repositories.transacciones import RESTRICCION_FOLIO, RepoTransaccionesSQL


class UnidadDeTrabajoSQL:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cuentas = RepoCuentasSQL(session)
        self.transacciones = RepoTransaccionesSQL(session)
        self._confirmada = False

    async def __aenter__(self) -> Self:
        self._confirmada = False
        return self

    async def __aexit__(self, *_: object) -> None:
        if not self._confirmada:
            await self.session.rollback()

    async def commit(self) -> None:
        try:
            await self.session.commit()
            self._confirmada = True
        except IntegrityError as e:
            await self.session.rollback()
            raise self._traducir(e) from e

    async def rollback(self) -> None:
        await self.session.rollback()

    @staticmethod
    def _traducir(e: IntegrityError) -> Exception:
        if RESTRICCION_FOLIO in str(e.orig):
            folio = e.params.get("folio_solicitud") if isinstance(e.params, dict) else None
            return FolioSolicitudDuplicado(str(folio or ""))
        return e
