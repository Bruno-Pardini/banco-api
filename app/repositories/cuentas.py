from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Cliente, Cuenta, Movimiento
from app.services.entidades import CuentaInfo


class RepoCuentasSQL:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def bloquear(self, numeros: list[str]) -> dict[str, CuentaInfo]:
        if not numeros:
            return {}
        filas = await self.s.execute(
            select(Cuenta.numero_cuenta, Cuenta.saldo, Cuenta.estatus, Cliente.nombre)
            .join(Cliente, Cliente.id_cliente == Cuenta.id_cliente)
            .where(Cuenta.numero_cuenta.in_(sorted(set(numeros))))
            .order_by(Cuenta.numero_cuenta)
            .with_for_update(of=Cuenta)
        )
        return {n: CuentaInfo(n, s, e, t) for n, s, e, t in filas.all()}

    async def actualizar_saldo(self, numero_cuenta: str, saldo: Decimal) -> None:
        await self.s.execute(update(Cuenta).where(Cuenta.numero_cuenta == numero_cuenta).values(saldo=saldo))

    # ---- consultas para los endpoints de administración
    async def obtener(self, numero_cuenta: str) -> tuple[Cuenta, str] | None:
        fila = (
            await self.s.execute(
                select(Cuenta, Cliente.nombre)
                .join(Cliente, Cliente.id_cliente == Cuenta.id_cliente)
                .where(Cuenta.numero_cuenta == numero_cuenta)
            )
        ).first()
        return (fila[0], fila[1]) if fila else None

    async def listar(
        self, id_cliente: int | None, estatus: str | None, offset: int, limite: int
    ) -> tuple[int, list[tuple[Cuenta, str]]]:
        q = select(Cuenta, Cliente.nombre).join(Cliente, Cliente.id_cliente == Cuenta.id_cliente)
        if id_cliente is not None:
            q = q.where(Cuenta.id_cliente == id_cliente)
        if estatus:
            q = q.where(Cuenta.estatus == estatus)
        total = await self.s.scalar(select(func.count()).select_from(q.subquery()))
        filas = await self.s.execute(q.order_by(Cuenta.numero_cuenta).offset(offset).limit(limite))
        return int(total or 0), [(c, n) for c, n in filas.all()]

    async def movimientos(self, numero_cuenta: str, offset: int, limite: int) -> tuple[int, list[Movimiento]]:
        q = select(Movimiento).where(Movimiento.numero_cuenta == numero_cuenta)
        total = await self.s.scalar(select(func.count()).select_from(q.subquery()))
        filas = await self.s.scalars(q.order_by(Movimiento.folio_operacion.desc()).offset(offset).limit(limite))
        return int(total or 0), list(filas)
