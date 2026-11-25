from decimal import Decimal

import pytest

from app.core.errores import SolicitudInvalida
from app.schemas.transaccion import EdoTransf
from tests.conftest import solicitud

pytestmark = pytest.mark.anyio


async def test_transferencia_aprobada_mueve_saldos_y_registra_dos_movimientos(servicio, almacen):
    r = await servicio.procesar(solicitud())
    tx = r.transaccion
    assert (tx.folio_operacion, tx.estatus, tx.codigo_rechazo, tx.tipo_operacion) == (
        "OP-2026-000001", "APROBADA", None, "TRANSFERENCIA")
    assert almacen.cuentas["3514126802"].saldo == Decimal("43350.00")
    assert almacen.cuentas["8103021410"].saldo == Decimal("16650.00")
    assert [m.tipo_movimiento for m in almacen.transacciones[tx.folio_operacion].movimientos] == ["RETIRO", "DEPOSITO"]


async def test_respuesta_edotransf_como_en_el_paso_8(servicio):
    r = await servicio.procesar(solicitud())
    t = r.transaccion
    edo = EdoTransf(
        folio_operacion=t.folio_operacion, folio_solicitud=t.folio_solicitud, fecha_hora=t.fecha_hora,
        tipo_operacion=t.tipo_operacion, cuenta_origen=t.cuenta_origen, cuenta_destino=t.cuenta_destino,
        importe=t.importe, estatus=t.estatus, codigo_rechazo=t.codigo_rechazo,
    ).model_dump(mode="json")
    assert edo["importe"] == 16650.0 and edo["codigo_rechazo"] is None and edo["estatus"] == "APROBADA"


async def test_folio_repetido_devuelve_el_comprobante_original_sin_reprocesar(servicio, almacen):
    primero = await servicio.procesar(solicitud())
    segundo = await servicio.procesar(solicitud(importe=1.00))
    assert segundo.repetida and segundo.transaccion.folio_operacion == primero.transaccion.folio_operacion
    assert almacen.cuentas["3514126802"].saldo == Decimal("43350.00")
    assert len(almacen.transacciones) == 1


async def test_r03_fondos_insuficientes_no_mueve_saldos(servicio, almacen):
    r = await servicio.procesar(solicitud(
        folio_solicitud="RES-2026-000002", cuenta_origen="7448067658", titular_origen="Lucía Fimbres Ochoa",
        importe=3800.00))
    assert (r.transaccion.estatus, r.transaccion.codigo_rechazo) == ("RECHAZADA", "R03")
    assert almacen.cuentas["7448067658"].saldo == Decimal("2500.00")
    assert almacen.transacciones[r.transaccion.folio_operacion].movimientos == []


@pytest.mark.parametrize(
    "cambios, codigo",
    [
        ({"cuenta_origen": "1111111111"}, "R01"),
        ({"cuenta_origen": "9000000001", "titular_origen": "Cliente de prueba inactivo"}, "R01"),
        ({"cuenta_destino": "2222222222"}, "R02"),
        ({"cuenta_destino": "8148000004"}, "R02"),
        ({"titular_origen": "Juan Pérez"}, "R04"),
        ({"importe": 0}, "R06"),
        ({"cuenta_origen": ...}, "R06"),
    ],
)
async def test_codigos_de_rechazo_se_registran(servicio, almacen, cambios, codigo):
    r = await servicio.procesar(solicitud(**cambios))
    assert (r.transaccion.estatus, r.transaccion.codigo_rechazo) == ("RECHAZADA", codigo)
    assert r.transaccion.folio_operacion in almacen.transacciones


async def test_r06_sin_folio_se_registra_y_cada_intento_es_nuevo(servicio, almacen):
    a = await servicio.procesar({"importe": 10})
    b = await servicio.procesar({"importe": 10})
    assert a.transaccion.codigo_rechazo == b.transaccion.codigo_rechazo == "R06"
    assert a.transaccion.folio_operacion != b.transaccion.folio_operacion
    assert a.transaccion.folio_solicitud is None


async def test_retiro_y_deposito(servicio, almacen):
    r = await servicio.procesar(solicitud(folio_solicitud="CIO-2026-000001", sistema_solicitante="CIO", cuenta_destino=None, importe=100))
    assert (r.transaccion.tipo_operacion, r.transaccion.estatus) == ("RETIRO", "APROBADA")
    d = await servicio.procesar(solicitud(folio_solicitud="CIO-2026-000002", sistema_solicitante="CIO", cuenta_destino="3514126802", importe=100))
    assert (d.transaccion.tipo_operacion, d.transaccion.estatus) == ("DEPOSITO", "APROBADA")
    assert almacen.cuentas["3514126802"].saldo == Decimal("60000.00")


async def test_r05_error_tecnico_revierte_saldos(servicio, almacen, uow):
    uow.fallar_al_actualizar = True
    r = await servicio.procesar(solicitud())
    assert (r.transaccion.estatus, r.transaccion.codigo_rechazo) == ("RECHAZADA", "R05")
    assert almacen.cuentas["3514126802"].saldo == Decimal("60000.00")
    assert almacen.cuentas["8103021410"].saldo == Decimal("0.00")
    assert almacen.transacciones[r.transaccion.folio_operacion].movimientos == []


async def test_carrera_de_folio_duplicado_devuelve_el_original(servicio, almacen, uow):
    """Otro request registra el mismo folio entre la consulta inicial y el INSERT."""
    from tests.conftest import AHORA
    from app.services.entidades import TransaccionRegistro

    async def otro_request(_tx):
        uow.antes_de_agregar = None
        almacen.transacciones["OP-2026-000099"] = TransaccionRegistro(
            "OP-2026-000099", "RES-2026-000001", "RES", "TRANSFERENCIA", "3514126802", "8103021410",
            Decimal("16650.00"), None, "APROBADA", None, AHORA, None)
        uow.trabajo.transacciones["OP-2026-000099"] = almacen.transacciones["OP-2026-000099"]

    uow.antes_de_agregar = otro_request
    r = await servicio.procesar(solicitud())
    assert r.repetida and r.transaccion.folio_operacion == "OP-2026-000099"
    assert almacen.cuentas["3514126802"].saldo == Decimal("60000.00")


@pytest.mark.parametrize("cuerpo", [[1, 2], "texto", 5, None])
async def test_cuerpo_que_no_es_objeto_es_400(servicio, cuerpo):
    with pytest.raises(SolicitudInvalida):
        await servicio.procesar(cuerpo)
