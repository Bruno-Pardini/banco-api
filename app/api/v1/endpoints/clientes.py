from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import ClientesDep, PaginaQ, TamanoQ
from app.schemas.cliente import ClienteActualizar, ClienteCrear, ClienteSalida
from app.schemas.comun import ErrorRespuesta, Pagina

router = APIRouter()
IdCliente = Annotated[int, Path(gt=0)]
_404 = {404: {"model": ErrorRespuesta}}
_409 = {409: {"model": ErrorRespuesta}}


@router.post("", response_model=ClienteSalida, status_code=status.HTTP_201_CREATED, responses=_409)
async def crear_cliente(datos: ClienteCrear, servicio: ClientesDep) -> ClienteSalida:
    return ClienteSalida.model_validate(await servicio.crear(datos))


@router.get("", response_model=Pagina[ClienteSalida])
async def listar_clientes(
    servicio: ClientesDep,
    q: Annotated[str | None, Query(max_length=120, description="Buscar por nombre")] = None,
    pagina: PaginaQ = 1,
    tamano: TamanoQ = 50,
) -> Pagina[ClienteSalida]:
    total, filas = await servicio.listar(q, pagina, tamano)
    return Pagina[ClienteSalida](
        total=total, pagina=pagina, tamano=tamano, datos=[ClienteSalida.model_validate(c) for c in filas]
    )


@router.get("/{id_cliente}", response_model=ClienteSalida, responses=_404)
async def obtener_cliente(id_cliente: IdCliente, servicio: ClientesDep) -> ClienteSalida:
    return ClienteSalida.model_validate(await servicio.obtener(id_cliente))


@router.patch("/{id_cliente}", response_model=ClienteSalida, responses={**_404, **_409})
async def actualizar_cliente(id_cliente: IdCliente, datos: ClienteActualizar, servicio: ClientesDep) -> ClienteSalida:
    return ClienteSalida.model_validate(await servicio.actualizar(id_cliente, datos))


@router.delete("/{id_cliente}", status_code=status.HTTP_204_NO_CONTENT, responses={**_404, **_409})
async def eliminar_cliente(id_cliente: IdCliente, servicio: ClientesDep) -> None:
    await servicio.eliminar(id_cliente)
