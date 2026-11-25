from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import CuentasDep, PaginaQ, TamanoQ
from app.core.dominio import EstatusCuenta
from app.models import Cuenta
from app.schemas.comun import ErrorRespuesta, Pagina
from app.schemas.cuenta import CuentaActualizar, CuentaCrear, CuentaSalida, MovimientoCuenta

router = APIRouter()
NumeroCuentaPath = Annotated[str, Path(pattern=r"^\d{10}$", examples=["3514126802"])]
_404 = {404: {"model": ErrorRespuesta}}


def _salida(cuenta: Cuenta, titular: str) -> CuentaSalida:
    return CuentaSalida(
        numero_cuenta=cuenta.numero_cuenta,
        id_cliente=cuenta.id_cliente,
        titular=titular,
        saldo=cuenta.saldo,
        estatus=EstatusCuenta(cuenta.estatus),
        fecha_apertura=cuenta.fecha_apertura,
    )


@router.post(
    "", response_model=CuentaSalida, status_code=status.HTTP_201_CREATED,
    responses={**_404, 409: {"model": ErrorRespuesta}},
)
async def crear_cuenta(datos: CuentaCrear, servicio: CuentasDep) -> CuentaSalida:
    return _salida(*await servicio.crear(datos))


@router.get("", response_model=Pagina[CuentaSalida])
async def listar_cuentas(
    servicio: CuentasDep,
    id_cliente: Annotated[int | None, Query(gt=0)] = None,
    estatus: EstatusCuenta | None = None,
    pagina: PaginaQ = 1,
    tamano: TamanoQ = 50,
) -> Pagina[CuentaSalida]:
    total, filas = await servicio.listar(id_cliente, estatus.value if estatus else None, pagina, tamano)
    return Pagina[CuentaSalida](total=total, pagina=pagina, tamano=tamano, datos=[_salida(c, t) for c, t in filas])


@router.get("/{numero_cuenta}", response_model=CuentaSalida, responses=_404)
async def obtener_cuenta(numero_cuenta: NumeroCuentaPath, servicio: CuentasDep) -> CuentaSalida:
    return _salida(*await servicio.obtener(numero_cuenta))


@router.patch("/{numero_cuenta}", response_model=CuentaSalida, responses=_404)
async def actualizar_cuenta(
    numero_cuenta: NumeroCuentaPath, datos: CuentaActualizar, servicio: CuentasDep
) -> CuentaSalida:
    """Activa o inactiva la cuenta. El saldo solo cambia mediante SolTransf (8)."""
    return _salida(*await servicio.actualizar(numero_cuenta, datos))


@router.get("/{numero_cuenta}/movimientos", response_model=Pagina[MovimientoCuenta], responses=_404)
async def movimientos_cuenta(
    numero_cuenta: NumeroCuentaPath, servicio: CuentasDep, pagina: PaginaQ = 1, tamano: TamanoQ = 50
) -> Pagina[MovimientoCuenta]:
    total, filas = await servicio.movimientos(numero_cuenta, pagina, tamano)
    return Pagina[MovimientoCuenta](
        total=total, pagina=pagina, tamano=tamano, datos=[MovimientoCuenta.model_validate(m) for m in filas]
    )
