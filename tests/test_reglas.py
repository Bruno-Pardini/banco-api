from datetime import datetime
from decimal import Decimal

import pytest

from app.core.dominio import CodigoRechazo, TipoOperacion
from app.services import reglas
from app.services.entidades import CuentaInfo
from tests.conftest import ZONA, solicitud


def test_solicitud_completa_del_paso_8():
    d = reglas.validar_solicitud(solicitud(), ZONA)
    assert d.completa, d.errores
    assert d.importe == Decimal("16650.00")
    assert d.fecha_hora_solicitud == datetime(2026, 11, 15, 9, 4, 12)


def test_fecha_con_otra_zona_se_convierte_a_hora_del_banco():
    d = reglas.validar_solicitud(solicitud(fecha_hora="2026-11-15T16:04:12Z"), ZONA)
    assert d.fecha_hora_solicitud == datetime(2026, 11, 15, 9, 4, 12)


@pytest.mark.parametrize(
    "cambios, error",
    [
        ({"folio_solicitud": ...}, "folio_solicitud: campo obligatorio"),
        ({"folio_solicitud": "RES-26-1"}, "folio_solicitud"),
        ({"folio_solicitud": "SPA-2026-000001"}, "prefijo"),
        ({"sistema_solicitante": "XYZ"}, "sistema_solicitante"),
        ({"cuenta_origen": "351412680"}, "cuenta_origen"),
        ({"cuenta_origen": 3514126802}, "cuenta_origen"),
        ({"cuenta_destino": ...}, "cuenta_destino: campo obligatorio"),
        ({"titular_origen": "   "}, "titular_origen"),
        ({"importe": 0}, "mayor a 0.00"),
        ({"importe": -5}, "mayor a 0.00"),
        ({"importe": 10.555}, "importe"),
        ({"importe": "abc"}, "importe"),
        ({"importe": True}, "importe"),
        ({"importe": 12345678901.0}, "importe"),
        ({"concepto": "x" * 101}, "concepto"),
        ({"fecha_hora": "ayer"}, "fecha_hora"),
    ],
)
def test_r06_por_datos_incompletos_o_invalidos(cambios, error):
    d = reglas.validar_solicitud(solicitud(**cambios), ZONA)
    assert not d.completa
    assert any(error in e for e in d.errores), d.errores


def test_importe_cero_se_conserva_para_la_bitacora():
    d = reglas.validar_solicitud(solicitud(importe=0), ZONA)
    assert d.importe == Decimal("0") and not d.completa


def test_concepto_es_opcional_y_destino_vacio_es_retiro():
    d = reglas.validar_solicitud(solicitud(concepto=..., cuenta_destino=""), ZONA)
    assert d.completa, d.errores
    assert d.cuenta_destino is None
    assert reglas.tipo_operacion(d.cuenta_origen, d.cuenta_destino) is TipoOperacion.RETIRO


@pytest.mark.parametrize(
    "origen, destino, esperado",
    [
        ("3514126802", None, TipoOperacion.RETIRO),
        ("3514126802", "3514126802", TipoOperacion.DEPOSITO),
        ("3514126802", "8103021410", TipoOperacion.TRANSFERENCIA),
        (None, "8103021410", None),
    ],
)
def test_tipo_operacion(origen, destino, esperado):
    assert reglas.tipo_operacion(origen, destino) is esperado


ORIGEN = CuentaInfo("3514126802", Decimal("100.00"), "ACTIVA", "Mariana Salcido Ruiz")
DESTINO = CuentaInfo("8103021410", Decimal("0.00"), "ACTIVA", "Hotel")
T = TipoOperacion


@pytest.mark.parametrize(
    "tipo, importe, titular, origen, destino, esperado",
    [
        (T.TRANSFERENCIA, Decimal("50"), "Mariana Salcido Ruiz", ORIGEN, DESTINO, None),
        (T.TRANSFERENCIA, Decimal("50"), "mariana  salcído RUIZ", ORIGEN, DESTINO, None),
        (T.TRANSFERENCIA, Decimal("50"), "Mariana", None, DESTINO, CodigoRechazo.R01),
        (T.TRANSFERENCIA, Decimal("50"), "Mariana Salcido Ruiz",
         CuentaInfo("3514126802", Decimal("100"), "INACTIVA", "Mariana Salcido Ruiz"), DESTINO, CodigoRechazo.R01),
        (T.TRANSFERENCIA, Decimal("50"), "Mariana Salcido Ruiz", ORIGEN, None, CodigoRechazo.R02),
        (T.TRANSFERENCIA, Decimal("50"), "Mariana Salcido Ruiz", ORIGEN,
         CuentaInfo("8103021410", Decimal("0"), "INACTIVA", "Hotel"), CodigoRechazo.R02),
        (T.TRANSFERENCIA, Decimal("50"), "Otra Persona", ORIGEN, DESTINO, CodigoRechazo.R04),
        (T.TRANSFERENCIA, Decimal("100.01"), "Mariana Salcido Ruiz", ORIGEN, DESTINO, CodigoRechazo.R03),
        (T.TRANSFERENCIA, Decimal("100.00"), "Mariana Salcido Ruiz", ORIGEN, DESTINO, None),
        (T.RETIRO, Decimal("100.01"), "Mariana Salcido Ruiz", ORIGEN, None, CodigoRechazo.R03),
        (T.DEPOSITO, Decimal("999999"), "Mariana Salcido Ruiz", ORIGEN, ORIGEN, None),
    ],
)
def test_evaluar_codigos_de_rechazo(tipo, importe, titular, origen, destino, esperado):
    assert reglas.evaluar(tipo, importe, titular, origen, destino) == esperado


def test_movimientos_de_transferencia_retiro_y_deposito():
    m = reglas.calcular_movimientos(T.TRANSFERENCIA, Decimal("40.00"), ORIGEN, DESTINO)
    assert [(x.tipo_movimiento.value, x.numero_cuenta, x.saldo_resultante) for x in m] == [
        ("RETIRO", "3514126802", Decimal("60.00")),
        ("DEPOSITO", "8103021410", Decimal("40.00")),
    ]
    assert [x.tipo_movimiento.value for x in reglas.calcular_movimientos(T.RETIRO, Decimal("1"), ORIGEN, None)] == ["RETIRO"]
    dep = reglas.calcular_movimientos(T.DEPOSITO, Decimal("1"), ORIGEN, ORIGEN)
    assert [(x.tipo_movimiento.value, x.saldo_resultante) for x in dep] == [("DEPOSITO", Decimal("101.00"))]


def test_formato_folio_operacion():
    assert reglas.formatear_folio_operacion(2026, 1) == "OP-2026-000001"
    assert len(reglas.formatear_folio_operacion(2026, 999999)) == 14
    with pytest.raises(ValueError):
        reglas.formatear_folio_operacion(2026, 1_000_000)
