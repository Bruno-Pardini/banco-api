from datetime import datetime, time, timedelta

from sqlalchemy import Select, String, cast, func, or_, select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errores import FolioOperacionAgotado, FolioSolicitudDuplicado
from app.models import Movimiento, Transaccion
from app.models.transaccion import FOLIO_OPERACION_SEQ
from app.services.entidades import FiltroBitacora, MovimientoRegistro, TransaccionRegistro
from app.services.reglas import formatear_folio_operacion

RESTRICCION_FOLIO = "uq_transaccion_folio_solicitud"


def a_registro(t: Transaccion, con_movimientos: bool = True) -> TransaccionRegistro:
    return TransaccionRegistro(
        folio_operacion=t.folio_operacion,
        folio_solicitud=t.folio_solicitud,
        sistema_solicitante=t.sistema_solicitante,
        tipo_operacion=t.tipo_operacion,
        cuenta_origen=t.cuenta_origen,
        cuenta_destino=t.cuenta_destino,
        importe=t.importe,
        concepto=t.concepto,
        estatus=t.estatus,
        codigo_rechazo=t.codigo_rechazo,
        fecha_hora=t.fecha_hora,
        fecha_hora_solicitud=t.fecha_hora_solicitud,
        movimientos=[
            MovimientoRegistro(m.folio_operacion, m.tipo_movimiento, m.numero_cuenta, m.importe, m.saldo_resultante)
            for m in t.movimientos
        ]
        if con_movimientos
        else [],
    )


class RepoTransaccionesSQL:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def por_folio_solicitud(self, folio_solicitud: str) -> TransaccionRegistro | None:
        t = await self.s.scalar(
            select(Transaccion)
            .options(selectinload(Transaccion.movimientos))
            .where(Transaccion.folio_solicitud == folio_solicitud)
        )
        return a_registro(t) if t else None

    async def por_folio_operacion(self, folio_operacion: str) -> TransaccionRegistro | None:
        t = await self.s.scalar(
            select(Transaccion)
            .options(selectinload(Transaccion.movimientos))
            .where(Transaccion.folio_operacion == folio_operacion)
        )
        return a_registro(t) if t else None

    async def siguiente_folio(self, fecha: datetime) -> str:
        try:
            n = await self.s.scalar(select(FOLIO_OPERACION_SEQ.next_value()))
        except DBAPIError as e:
            if "reached maximum value" in str(e.orig):
                raise FolioOperacionAgotado() from e
            raise
        return formatear_folio_operacion(fecha.year, int(n))

    async def agregar(self, tx: TransaccionRegistro, movimientos: list[MovimientoRegistro]) -> None:
        self.s.add(
            Transaccion(
                folio_operacion=tx.folio_operacion,
                folio_solicitud=tx.folio_solicitud,
                sistema_solicitante=tx.sistema_solicitante,
                tipo_operacion=tx.tipo_operacion,
                cuenta_origen=tx.cuenta_origen,
                cuenta_destino=tx.cuenta_destino,
                importe=tx.importe,
                concepto=tx.concepto,
                estatus=tx.estatus,
                codigo_rechazo=tx.codigo_rechazo,
                fecha_hora=tx.fecha_hora,
                fecha_hora_solicitud=tx.fecha_hora_solicitud,
            )
        )
        try:
            await self.s.flush()  # la transacción debe existir antes que sus movimientos (FK)
        except IntegrityError as e:
            if tx.folio_solicitud and RESTRICCION_FOLIO in str(e.orig):
                raise FolioSolicitudDuplicado(tx.folio_solicitud) from e
            raise
        self.s.add_all(
            Movimiento(
                folio_operacion=m.folio_operacion,
                tipo_movimiento=m.tipo_movimiento,
                numero_cuenta=m.numero_cuenta,
                importe=m.importe,
                saldo_resultante=m.saldo_resultante,
            )
            for m in movimientos
        )
        await self.s.flush()

    @staticmethod
    def _filtrar(q: Select, f: FiltroBitacora) -> Select:
        if f.estatus:
            q = q.where(Transaccion.estatus == f.estatus)
        if f.tipo_operacion:
            q = q.where(Transaccion.tipo_operacion == f.tipo_operacion)
        if f.sistema_solicitante:
            q = q.where(Transaccion.sistema_solicitante == f.sistema_solicitante)
        if f.codigo_rechazo:
            q = q.where(Transaccion.codigo_rechazo == f.codigo_rechazo)
        if f.desde:
            q = q.where(Transaccion.fecha_hora >= datetime.combine(f.desde, time.min))
        if f.hasta:
            q = q.where(Transaccion.fecha_hora < datetime.combine(f.hasta + timedelta(days=1), time.min))
        if f.texto:
            patron = f"%{f.texto.strip()}%"
            q = q.where(
                or_(
                    Transaccion.folio_operacion.ilike(patron),
                    Transaccion.folio_solicitud.ilike(patron),
                    cast(Transaccion.cuenta_origen, String).ilike(patron),
                    cast(Transaccion.cuenta_destino, String).ilike(patron),
                    Transaccion.concepto.ilike(patron),
                )
            )
        return q

    async def listar(self, filtro: FiltroBitacora) -> tuple[int, list[TransaccionRegistro]]:
        base = self._filtrar(select(Transaccion), filtro)
        total = await self.s.scalar(select(func.count()).select_from(base.order_by(None).subquery()))
        filas = await self.s.scalars(
            base.order_by(Transaccion.fecha_hora.desc(), Transaccion.folio_operacion.desc())
            .offset((filtro.pagina - 1) * filtro.tamano)
            .limit(filtro.tamano)
        )
        return int(total or 0), [a_registro(t, con_movimientos=False) for t in filas]
