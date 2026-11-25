"""Excepciones de dominio. Los manejadores HTTP están en app/api/manejadores.py."""


class ErrorDominio(Exception):
    status_code = 400
    codigo = "ERROR"

    def __init__(self, mensaje: str, *, detalles: object | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalles = detalles


class SolicitudInvalida(ErrorDominio):
    """El cuerpo no es JSON válido o no es un objeto: no se registra transacción (400)."""

    status_code = 400
    codigo = "SOLICITUD_INVALIDA"


class NoEncontrado(ErrorDominio):
    status_code = 404
    codigo = "NO_ENCONTRADO"


class Conflicto(ErrorDominio):
    status_code = 409
    codigo = "CONFLICTO"


class FolioSolicitudDuplicado(Exception):
    """Carrera de idempotencia: otro request registró el mismo folio_solicitud primero."""

    def __init__(self, folio_solicitud: str) -> None:
        super().__init__(folio_solicitud)
        self.folio_solicitud = folio_solicitud


class FolioOperacionAgotado(Exception):
    """El consecutivo del folio OP-AAAA-NNNNNN superó 999999."""
