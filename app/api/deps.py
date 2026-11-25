from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.repositories.uow import UnidadDeTrabajoSQL
from app.services.administracion import ServicioClientes, ServicioCuentas
from app.services.transacciones import ServicioTransacciones

SesionDep = Annotated[AsyncSession, Depends(get_session)]


def zona() -> ZoneInfo:
    return ZoneInfo(get_settings().ZONA_HORARIA)


def servicio_transacciones(session: SesionDep) -> ServicioTransacciones:
    return ServicioTransacciones(UnidadDeTrabajoSQL(session), zona())


def servicio_clientes(session: SesionDep) -> ServicioClientes:
    return ServicioClientes(session)


def servicio_cuentas(session: SesionDep) -> ServicioCuentas:
    return ServicioCuentas(session)


TransaccionesDep = Annotated[ServicioTransacciones, Depends(servicio_transacciones)]
ClientesDep = Annotated[ServicioClientes, Depends(servicio_clientes)]
CuentasDep = Annotated[ServicioCuentas, Depends(servicio_cuentas)]
PaginaQ = Annotated[int, Query(ge=1, description="Número de página (desde 1)")]
TamanoQ = Annotated[int, Query(ge=1, le=200, description="Registros por página (máx. 200)")]
