from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Cliente, Cuenta


class RepoClientesSQL:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def obtener(self, id_cliente: int) -> Cliente | None:
        return await self.s.get(Cliente, id_cliente)

    async def listar(self, texto: str | None, offset: int, limite: int) -> tuple[int, list[Cliente]]:
        q = select(Cliente)
        if texto:
            q = q.where(Cliente.nombre.ilike(f"%{texto.strip()}%"))
        total = await self.s.scalar(select(func.count()).select_from(q.subquery()))
        filas = await self.s.scalars(q.order_by(Cliente.id_cliente).offset(offset).limit(limite))
        return int(total or 0), list(filas)

    async def tiene_cuentas(self, id_cliente: int) -> bool:
        return bool(await self.s.scalar(select(func.count()).where(Cuenta.id_cliente == id_cliente)))
