"""Catálogos y valores del Paso 8 (Banco E6 · PR06B)."""

from enum import StrEnum


class Sistema(StrEnum):
    """Procesos que consumen SolTransf (8)."""

    RES = "RES"  # E3 Gestión de Reservas
    VST = "VST"  # E5 Venta de Servicios Turísticos
    VGS = "VGS"  # E7 Venta y Gestión de Souvenirs
    SRE = "SRE"  # E8 Servicio de Restaurante
    SPA = "SPA"  # E9 Gestión de SPA
    GEE = "GEE"  # E10 Gestión y Ejecución de Eventos
    GJA = "GJA"  # E11 Gestión de Juegos y Apuestas del Casino
    CIO = "CIO"  # E12 Servicio de Recepción


NOMBRE_SISTEMA: dict[Sistema, str] = {
    Sistema.RES: "Gestión de Reservas",
    Sistema.VST: "Venta de Servicios Turísticos",
    Sistema.VGS: "Venta y Gestión de Souvenirs",
    Sistema.SRE: "Servicio de Restaurante",
    Sistema.SPA: "Gestión de SPA",
    Sistema.GEE: "Gestión y Ejecución de Eventos",
    Sistema.GJA: "Gestión de Juegos y Apuestas del Casino",
    Sistema.CIO: "Servicio de Recepción",
}


class TipoOperacion(StrEnum):
    DEPOSITO = "DEPOSITO"
    RETIRO = "RETIRO"
    TRANSFERENCIA = "TRANSFERENCIA"


class Estatus(StrEnum):
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"


class CodigoRechazo(StrEnum):
    R01 = "R01"
    R02 = "R02"
    R03 = "R03"
    R04 = "R04"
    R05 = "R05"
    R06 = "R06"


MOTIVO_RECHAZO: dict[CodigoRechazo, str] = {
    CodigoRechazo.R01: "Cuenta origen inexistente o inactiva",
    CodigoRechazo.R02: "Cuenta destino inexistente, inactiva o, en una transferencia, igual a la origen",
    CodigoRechazo.R03: "Fondos insuficientes en la cuenta origen",
    CodigoRechazo.R04: "El titular no coincide con el registrado en la cuenta origen",
    CodigoRechazo.R05: "Error técnico al aplicar la operación; se revirtió sin afectar saldos",
    CodigoRechazo.R06: "Solicitud incompleta o con importe menor o igual a $0.00",
}


class TipoMovimiento(StrEnum):
    RETIRO = "RETIRO"
    DEPOSITO = "DEPOSITO"


class EstatusCuenta(StrEnum):
    ACTIVA = "ACTIVA"
    INACTIVA = "INACTIVA"


class TipoCliente(StrEnum):
    HUESPED = "HUESPED"
    EMPRESA = "EMPRESA"
    HOTEL = "HOTEL"
    PROVEEDOR = "PROVEEDOR"


# Formatos de los datos de transmisión (sección 6 del Paso 8)
PATRON_FOLIO_SOLICITUD = r"^(RES|VST|VGS|SRE|SPA|GEE|GJA|CIO)-\d{4}-\d{6}$"
PATRON_CUENTA = r"^\d{10}$"
PATRON_FOLIO_OPERACION = r"^OP-\d{4}-\d{6}$"
IMPORTE_MAXIMO_DIGITOS = 12  # NUMERIC(12,2)
