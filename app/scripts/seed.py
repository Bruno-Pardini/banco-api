"""Datos de demostración (clientes y cuentas de la IG 6.1 del Paso 8). Se puede ejecutar varias veces.

    python -m app.scripts.seed
"""

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.session import get_engine, get_sessionmaker
from app.models import Cliente, Cuenta

HOTEL = "Hotel Resort Sierra Madre"

# (nombre, tipo_cliente, rfc, correo, [(numero_cuenta, saldo, estatus)])
CLIENTES: list[tuple[str, str, str | None, str | None, list[tuple[str, str, str]]]] = [
    ("Mariana Salcido Ruiz", "HUESPED", "SARM900115KJ2", "mariana.salcido@example.com",
     [("3514126802", "60000.00", "ACTIVA")]),
    ("Jorge Ibarra Valenzuela", "HUESPED", "IAVJ850302QW1", None, [("2921815266", "12000.00", "ACTIVA")]),
    ("Lucía Fimbres Ochoa", "HUESPED", None, None, [("7448067658", "2500.00", "ACTIVA")]),
    ("Ricardo Moreno Haros", "HUESPED", None, None, [("1193833709", "8000.00", "ACTIVA")]),
    ("Grupo Turístico del Noroeste", "EMPRESA", "GTN120101AB3", "pagos@gtn.example.com",
     [("5889592713", "150000.00", "ACTIVA")]),
    ("Cliente de prueba inactivo", "HUESPED", None, None, [("9000000001", "1000.00", "INACTIVA")]),
    (HOTEL, "HOTEL", "HRS010101HR5", "tesoreria@sierramadre.example.com", [
        ("8103021410", "0.00", "ACTIVA"),  # RES · Gestión de Reservas
        ("5520190034", "0.00", "ACTIVA"),  # VST · Venta de Servicios Turísticos
        ("6610472283", "0.00", "ACTIVA"),  # VGS · Venta y Gestión de Souvenirs
        ("1303715383", "0.00", "ACTIVA"),  # SRE · Servicio de Restaurante
        ("7888110888", "0.00", "ACTIVA"),  # SPA · Gestión de SPA
        ("8148000003", "0.00", "ACTIVA"),  # GEE · Gestión y Ejecución de Eventos
        ("4471092256", "0.00", "ACTIVA"),  # GJA · Juegos y Apuestas del Casino
        ("3390017745", "0.00", "ACTIVA"),  # CIO · Servicio de Recepción
    ]),
]


async def cargar() -> None:
    async with get_sessionmaker()() as s:
        for nombre, tipo, rfc, correo, cuentas in CLIENTES:
            cliente = await s.scalar(select(Cliente).where(Cliente.nombre == nombre))
            if cliente is None:
                cliente = Cliente(nombre=nombre, tipo_cliente=tipo, rfc=rfc, correo=correo)
                s.add(cliente)
                await s.flush()
            for numero, saldo, estatus in cuentas:
                await s.execute(
                    insert(Cuenta)
                    .values(numero_cuenta=numero, id_cliente=cliente.id_cliente, saldo=Decimal(saldo), estatus=estatus)
                    .on_conflict_do_nothing(index_elements=[Cuenta.numero_cuenta])
                )
        await s.commit()
    await get_engine().dispose()
    print(f"Datos de demostración listos: {len(CLIENTES)} clientes, {sum(len(c[4]) for c in CLIENTES)} cuentas")


if __name__ == "__main__":
    asyncio.run(cargar())
