"""Catálogos de apoyo (clientes y cuentas) para dar de alta los datos que valida SolTransf (8)."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import Conflicto, NoEncontrado
from app.models import Cliente, CodigoRechazoModel, Cuenta, Movimiento
from app.repositories.clientes import RepoClientesSQL
from app.repositories.cuentas import RepoCuentasSQL
from app.schemas.cliente import ClienteActualizar, ClienteCrear
from app.schemas.cuenta import CuentaActualizar, CuentaCrear


class ServicioClientes:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session
        self.repo = RepoClientesSQL(session)

    async def crear(self, datos: ClienteCrear) -> Cliente:
        cliente = Cliente(**datos.model_dump())
        self.s.add(cliente)
        await self._guardar("Ya existe un cliente con ese RFC")
        return cliente

    async def obtener(self, id_cliente: int) -> Cliente:
        cliente = await self.repo.obtener(id_cliente)
        if cliente is None:
            raise NoEncontrado(f"No existe el cliente {id_cliente}")
        return cliente

    async def listar(self, texto: str | None, pagina: int, tamano: int) -> tuple[int, list[Cliente]]:
        return await self.repo.listar(texto, (pagina - 1) * tamano, tamano)

    async def actualizar(self, id_cliente: int, datos: ClienteActualizar) -> Cliente:
        cliente = await self.obtener(id_cliente)
        for campo, valor in datos.model_dump(exclude_unset=True).items():
            setattr(cliente, campo, valor)
        await self._guardar("Ya existe un cliente con ese RFC")
        return cliente

    async def eliminar(self, id_cliente: int) -> None:
        cliente = await self.obtener(id_cliente)
        if await self.repo.tiene_cuentas(id_cliente):
            raise Conflicto("El cliente tiene cuentas; inactívalas en lugar de borrar al cliente")
        await self.s.delete(cliente)
        await self.s.commit()

    async def _guardar(self, mensaje_conflicto: str) -> None:
        try:
            await self.s.commit()
        except IntegrityError as e:
            await self.s.rollback()
            raise Conflicto(mensaje_conflicto) from e


class ServicioCuentas:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session
        self.repo = RepoCuentasSQL(session)

    async def crear(self, datos: CuentaCrear) -> tuple[Cuenta, str]:
        cliente = await self.s.get(Cliente, datos.id_cliente)
        if cliente is None:
            raise NoEncontrado(f"No existe el cliente {datos.id_cliente}")
        cuenta = Cuenta(numero_cuenta=datos.numero_cuenta, id_cliente=datos.id_cliente, saldo=datos.saldo_inicial)
        self.s.add(cuenta)
        try:
            await self.s.commit()
        except IntegrityError as e:
            await self.s.rollback()
            raise Conflicto(f"La cuenta {datos.numero_cuenta} ya existe") from e
        await self.s.refresh(cuenta)
        return cuenta, cliente.nombre

    async def obtener(self, numero_cuenta: str) -> tuple[Cuenta, str]:
        r = await self.repo.obtener(numero_cuenta)
        if r is None:
            raise NoEncontrado(f"No existe la cuenta {numero_cuenta}")
        return r

    async def listar(
        self, id_cliente: int | None, estatus: str | None, pagina: int, tamano: int
    ) -> tuple[int, list[tuple[Cuenta, str]]]:
        return await self.repo.listar(id_cliente, estatus, (pagina - 1) * tamano, tamano)

    async def actualizar(self, numero_cuenta: str, datos: CuentaActualizar) -> tuple[Cuenta, str]:
        cuenta, titular = await self.obtener(numero_cuenta)
        cuenta.estatus = datos.estatus.value
        await self.s.commit()
        return cuenta, titular

    async def movimientos(self, numero_cuenta: str, pagina: int, tamano: int) -> tuple[int, list[Movimiento]]:
        await self.obtener(numero_cuenta)
        return await self.repo.movimientos(numero_cuenta, (pagina - 1) * tamano, tamano)


async def codigos_rechazo(session: AsyncSession) -> list[CodigoRechazoModel]:
    return list(await session.scalars(select(CodigoRechazoModel).order_by(CodigoRechazoModel.codigo)))
