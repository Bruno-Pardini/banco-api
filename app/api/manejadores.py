"""Manejo centralizado de errores: todas las respuestas de error tienen la forma ErrorRespuesta."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errores import ErrorDominio, FolioOperacionAgotado

log = logging.getLogger("banco.errores")


def _respuesta(status_code: int, codigo: str, mensaje: str, detalles: object | None = None) -> JSONResponse:
    cuerpo = {"codigo": codigo, "mensaje": mensaje, "detalles": detalles}
    return JSONResponse(status_code=status_code, content=jsonable_encoder(cuerpo))


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorDominio)
    async def _dominio(_: Request, exc: ErrorDominio) -> JSONResponse:
        return _respuesta(exc.status_code, exc.codigo, exc.mensaje, exc.detalles)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        errores = [
            {"campo": ".".join(str(p) for p in e.get("loc", ()) if p != "body"), "mensaje": e.get("msg")}
            for e in exc.errors()
        ]
        return _respuesta(
            422, "DATOS_INVALIDOS", "Los datos enviados no son válidos", errores
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        codigo = {404: "NO_ENCONTRADO", 405: "METODO_NO_PERMITIDO"}.get(exc.status_code, "ERROR_HTTP")
        return _respuesta(exc.status_code, codigo, str(exc.detail))

    @app.exception_handler(FolioOperacionAgotado)
    async def _folio(_: Request, exc: FolioOperacionAgotado) -> JSONResponse:
        log.error("Se agotó el consecutivo de folio_operacion (999999)")
        return _respuesta(500, "FOLIO_AGOTADO", "Se agotó el consecutivo de folio de operación")

    @app.exception_handler(Exception)
    async def _no_controlado(request: Request, exc: Exception) -> JSONResponse:
        log.exception("Error no controlado en %s %s", request.method, request.url.path)
        return _respuesta(500, "ERROR_INTERNO", "Ocurrió un error interno; intenta de nuevo")
