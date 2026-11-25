"""Caso de uso principal: atender SolTransf (8) y devolver EdoTransf (9) en la misma llamada."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.core.dominio import MOTIVO_RECHAZO, CodigoRechazo, Estatus
from app.core.errores import FolioOperacionAgotado, FolioSolicitudDuplicado, NoEncontrado, SolicitudInvalida
from app.core.tiempo import ahora_local
from app.services import reglas
from app.services.entidades import FiltroBitacora, MovimientoRegistro, TransaccionRegistro
from app.services.puertos import UnidadDeTrabajo

log = logging.getLogger("banco.transacciones")


@dataclass(slots=True)
class Resultado:
    transaccion: TransaccionRegistro
    repetida: bool  # True: el folio_solicitud ya existía y se devolvió el comprobante original


class ServicioTransacciones:
    def __init__(self, uow: UnidadDeTrabajo, zona: ZoneInfo, reloj: Callable[[], datetime] | None = None) -> None:
        self.uow = uow
        self.zona = zona
        self.reloj = reloj or (lambda: ahora_local(zona))

    # ------------------------------------------------------------------ SolTransf (8) → EdoTransf (9)
    async def procesar(self, cuerpo: Any) -> Resultado:
        if not isinstance(cuerpo, dict):
            raise SolicitudInvalida("El cuerpo debe ser un objeto JSON con los datos del FR06-03")

        datos = reglas.validar_solicitud(cuerpo, self.zona)

        # Folio de solicitud repetido: no se procesa de nuevo; se responde el comprobante original.
        if datos.folio_solicitud:
            async with self.uow:
                previa = await self.uow.transacciones.por_folio_solicitud(datos.folio_solicitud)
            if previa is not None:
                return Resultado(previa, repetida=True)

        if not datos.completa:
            log.info("SolTransf rechazada R06 folio=%s errores=%s", datos.folio_solicitud, datos.errores)
            return await self._registrar_rechazo(datos, CodigoRechazo.R06)

        try:
            return await self._aplicar(datos)
        except FolioSolicitudDuplicado as dup:
            return await self._original(dup.folio_solicitud)
        except FolioOperacionAgotado:
            raise
        except Exception:
            # R05: error técnico al aplicar; la unidad de trabajo ya revirtió cargo y abono.
            log.exception("Error técnico al aplicar folio=%s; se registra R05", datos.folio_solicitud)
            return await self._registrar_rechazo(datos, CodigoRechazo.R05)

    async def _aplicar(self, d: reglas.DatosCapturados) -> Resultado:
        assert d.cuenta_origen and d.importe is not None and d.titular_origen
        tipo = reglas.tipo_operacion(d.cuenta_origen, d.cuenta_destino)
        assert tipo is not None
        async with self.uow:
            fecha = self.reloj()
            folio = await self.uow.transacciones.siguiente_folio(fecha)
            numeros = [n for n in {d.cuenta_origen, d.cuenta_destino} if n]
            cuentas = await self.uow.cuentas.bloquear(numeros)
            origen = cuentas.get(d.cuenta_origen)
            destino = cuentas.get(d.cuenta_destino) if d.cuenta_destino else None

            codigo = reglas.evaluar(tipo, d.importe, d.titular_origen, origen, destino)
            movimientos: list[MovimientoRegistro] = []
            if codigo is None:
                assert origen is not None
                for m in reglas.calcular_movimientos(tipo, d.importe, origen, destino):
                    await self.uow.cuentas.actualizar_saldo(m.numero_cuenta, m.saldo_resultante)
                    movimientos.append(
                        MovimientoRegistro(folio, m.tipo_movimiento.value, m.numero_cuenta, m.importe, m.saldo_resultante)
                    )

            tx = self._nueva(folio, fecha, d, codigo, tipo.value)
            tx.movimientos = movimientos
            await self.uow.transacciones.agregar(tx, movimientos)
            await self.uow.commit()
        log.info("SolTransf %s → %s %s %s", d.folio_solicitud, folio, tx.estatus, tx.codigo_rechazo or "")
        return Resultado(tx, repetida=False)

    async def _registrar_rechazo(self, d: reglas.DatosCapturados, codigo: CodigoRechazo) -> Resultado:
        tipo = reglas.tipo_operacion(d.cuenta_origen, d.cuenta_destino)
        try:
            async with self.uow:
                fecha = self.reloj()
                folio = await self.uow.transacciones.siguiente_folio(fecha)
                tx = self._nueva(folio, fecha, d, codigo, tipo.value if tipo else None)
                await self.uow.transacciones.agregar(tx, [])
                await self.uow.commit()
            return Resultado(tx, repetida=False)
        except FolioSolicitudDuplicado as dup:
            return await self._original(dup.folio_solicitud)

    async def _original(self, folio_solicitud: str) -> Resultado:
        async with self.uow:
            previa = await self.uow.transacciones.por_folio_solicitud(folio_solicitud)
        if previa is None:  # no debería ocurrir: la restricción única lo garantiza
            raise RuntimeError(f"folio_solicitud {folio_solicitud} duplicado pero no encontrado")
        return Resultado(previa, repetida=True)

    @staticmethod
    def _nueva(
        folio: str, fecha: datetime, d: reglas.DatosCapturados, codigo: CodigoRechazo | None, tipo: str | None
    ) -> TransaccionRegistro:
        return TransaccionRegistro(
            folio_operacion=folio,
            folio_solicitud=d.folio_solicitud,
            sistema_solicitante=d.sistema_solicitante,
            tipo_operacion=tipo,
            cuenta_origen=d.cuenta_origen,
            cuenta_destino=d.cuenta_destino,
            importe=d.importe,
            concepto=d.concepto,
            estatus=(Estatus.APROBADA if codigo is None else Estatus.RECHAZADA).value,
            codigo_rechazo=codigo.value if codigo else None,
            fecha_hora=fecha,
            fecha_hora_solicitud=d.fecha_hora_solicitud,
        )

    # ------------------------------------------------------------------ IG 6.1 Bitácora (solo lectura)
    async def bitacora(self, filtro: FiltroBitacora) -> tuple[int, list[TransaccionRegistro]]:
        async with self.uow:
            return await self.uow.transacciones.listar(filtro)

    async def detalle(self, folio_operacion: str) -> TransaccionRegistro:
        async with self.uow:
            tx = await self.uow.transacciones.por_folio_operacion(folio_operacion)
        if tx is None:
            raise NoEncontrado(f"No existe la transacción {folio_operacion}")
        return tx

    @staticmethod
    def motivo(codigo: str | None) -> str | None:
        return MOTIVO_RECHAZO[CodigoRechazo(codigo)] if codigo else None
