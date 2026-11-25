"""Unidad de trabajo en memoria con semántica transaccional (para probar el servicio sin PostgreSQL)."""

import copy
from datetime import datetime
from decimal import Decimal
from typing import Self

from app.core.errores import FolioSolicitudDuplicado
from app.services.entidades import CuentaInfo, FiltroBitacora, MovimientoRegistro, TransaccionRegistro
from app.services.reglas import formatear_folio_operacion


class Almacen:
    def __init__(self, cuentas: list[CuentaInfo]) -> None:
        self.cuentas = {c.numero_cuenta: c for c in cuentas}
        self.transacciones: dict[str, TransaccionRegistro] = {}
        self.secuencia = 0  # como una SEQUENCE: no se revierte con rollback


class RepoCuentasMem:
    def __init__(self, uow: "UoWMem") -> None:
        self.uow = uow

    async def bloquear(self, numeros: list[str]) -> dict[str, CuentaInfo]:
        return {n: copy.copy(self.uow.trabajo.cuentas[n]) for n in sorted(set(numeros)) if n in self.uow.trabajo.cuentas}

    async def actualizar_saldo(self, numero_cuenta: str, saldo: Decimal) -> None:
        if self.uow.fallar_al_actualizar:
            raise RuntimeError("falla simulada de BD")
        if saldo < 0:
            raise RuntimeError("violación ck_cuenta_saldo_no_negativo")
        self.uow.trabajo.cuentas[numero_cuenta].saldo = saldo


class RepoTransaccionesMem:
    def __init__(self, uow: "UoWMem") -> None:
        self.uow = uow

    async def por_folio_solicitud(self, folio_solicitud: str) -> TransaccionRegistro | None:
        return next((t for t in self.uow.trabajo.transacciones.values() if t.folio_solicitud == folio_solicitud), None)

    async def por_folio_operacion(self, folio_operacion: str) -> TransaccionRegistro | None:
        return self.uow.trabajo.transacciones.get(folio_operacion)

    async def siguiente_folio(self, fecha: datetime) -> str:
        self.uow.almacen.secuencia += 1
        return formatear_folio_operacion(fecha.year, self.uow.almacen.secuencia)

    async def agregar(self, tx: TransaccionRegistro, movimientos: list[MovimientoRegistro]) -> None:
        if self.uow.antes_de_agregar:
            await self.uow.antes_de_agregar(tx)
        if tx.folio_solicitud and await self.por_folio_solicitud(tx.folio_solicitud):
            raise FolioSolicitudDuplicado(tx.folio_solicitud)
        guardada = copy.deepcopy(tx)
        guardada.movimientos = list(movimientos)
        self.uow.trabajo.transacciones[tx.folio_operacion] = guardada

    async def listar(self, filtro: FiltroBitacora) -> tuple[int, list[TransaccionRegistro]]:
        filas = [t for t in self.uow.trabajo.transacciones.values() if not filtro.estatus or t.estatus == filtro.estatus]
        return len(filas), filas


class UoWMem:
    def __init__(self, almacen: Almacen) -> None:
        self.almacen = almacen
        self.cuentas = RepoCuentasMem(self)
        self.transacciones = RepoTransaccionesMem(self)
        self.fallar_al_actualizar = False
        self.antes_de_agregar = None
        self.commits = 0

    async def __aenter__(self) -> Self:
        self.trabajo = copy.deepcopy(self.almacen)
        self.trabajo.secuencia = self.almacen.secuencia
        self._confirmada = False
        return self

    async def __aexit__(self, *_: object) -> None:
        self.trabajo = self.almacen  # rollback implícito: se descarta la copia de trabajo

    async def commit(self) -> None:
        self.almacen.cuentas = self.trabajo.cuentas
        self.almacen.transacciones = self.trabajo.transacciones
        self.commits += 1

    async def rollback(self) -> None:
        self.trabajo = copy.deepcopy(self.almacen)
