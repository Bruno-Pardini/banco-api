from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.services.entidades import CuentaInfo
from app.services.transacciones import ServicioTransacciones
from tests.fakes import Almacen, UoWMem

ZONA = ZoneInfo("America/Hermosillo")
AHORA = datetime(2026, 11, 15, 9, 4, 12)


def cuentas_demo() -> list[CuentaInfo]:
    return [
        CuentaInfo("3514126802", Decimal("60000.00"), "ACTIVA", "Mariana Salcido Ruiz"),
        CuentaInfo("7448067658", Decimal("2500.00"), "ACTIVA", "Lucía Fimbres Ochoa"),
        CuentaInfo("9000000001", Decimal("1000.00"), "INACTIVA", "Cliente de prueba inactivo"),
        CuentaInfo("8103021410", Decimal("0.00"), "ACTIVA", "Hotel Resort Sierra Madre"),
        CuentaInfo("8148000004", Decimal("0.00"), "INACTIVA", "Hotel Resort Sierra Madre"),
    ]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def almacen() -> Almacen:
    return Almacen(cuentas_demo())


@pytest.fixture
def uow(almacen: Almacen) -> UoWMem:
    return UoWMem(almacen)


@pytest.fixture
def servicio(uow: UoWMem) -> ServicioTransacciones:
    return ServicioTransacciones(uow, ZONA, reloj=lambda: AHORA)


def solicitud(**cambios: object) -> dict[str, object]:
    base: dict[str, object] = {
        "folio_solicitud": "RES-2026-000001",
        "sistema_solicitante": "RES",
        "fecha_hora": "2026-11-15T09:04:12-07:00",
        "cuenta_origen": "3514126802",
        "cuenta_destino": "8103021410",
        "titular_origen": "Mariana Salcido Ruiz",
        "importe": 16650.00,
        "concepto": "Pago reservación SMR-2026-00142",
    }
    base.update(cambios)
    return {k: v for k, v in base.items() if v is not ...}
