"""SolTransf (8) / EdoTransf (9) y la bitácora de la IG 6.1."""

import json
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel

from app.api.deps import PaginaQ, TamanoQ, TransaccionesDep, zona
from app.core.dominio import CodigoRechazo, Estatus, Sistema, TipoOperacion
from app.core.errores import SolicitudInvalida
from app.core.tiempo import con_zona
from app.schemas.comun import ErrorRespuesta, Pagina
from app.schemas.transaccion import EdoTransf, MovimientoSalida, SolTransf, TransaccionBitacora, TransaccionDetalle
from app.services.entidades import FiltroBitacora, TransaccionRegistro
from app.services.transacciones import ServicioTransacciones

router = APIRouter()


def _esquema_en_linea(modelo: type[BaseModel]) -> dict[str, Any]:
    """JSON Schema del modelo con sus $defs resueltos (para usarlo en openapi_extra)."""
    esquema = modelo.model_json_schema()
    defs = esquema.pop("$defs", {})

    def resolver(nodo: Any) -> Any:
        if isinstance(nodo, dict):
            if "$ref" in nodo and nodo["$ref"].startswith("#/$defs/"):
                return resolver(defs[nodo["$ref"].split("/")[-1]])
            return {k: resolver(v) for k, v in nodo.items()}
        if isinstance(nodo, list):
            return [resolver(v) for v in nodo]
        return nodo

    return resolver(esquema)


def _edo(tx: TransaccionRegistro) -> EdoTransf:
    return EdoTransf.model_validate(
        {
            "folio_operacion": tx.folio_operacion,
            "folio_solicitud": tx.folio_solicitud,
            "fecha_hora": con_zona(tx.fecha_hora, zona()),
            "tipo_operacion": tx.tipo_operacion,
            "cuenta_origen": tx.cuenta_origen,
            "cuenta_destino": tx.cuenta_destino,
            "importe": tx.importe,
            "estatus": tx.estatus,
            "codigo_rechazo": tx.codigo_rechazo,
        }
    )


def _bitacora(tx: TransaccionRegistro) -> TransaccionBitacora:
    datos = {f: getattr(tx, f) for f in TransaccionBitacora.model_fields}
    datos["fecha_hora"] = con_zona(tx.fecha_hora, zona())
    return TransaccionBitacora.model_validate(datos)


async def sol_transf(request: Request, response: Response, servicio: TransaccionesDep) -> EdoTransf:
    """**SolTransf (8) → EdoTransf (9).** Recibe el FR06-03 y devuelve el FR06-04 en la misma llamada.

    - **200**: transacción registrada, APROBADA o RECHAZADA con su código R01–R06.
    - **200 + R06**: datos incompletos, con formato inválido o importe ≤ $0.00 (no responde 422, según el Paso 8).
    - **200 + cabecera `X-Solicitud-Repetida: true`**: el folio_solicitud ya existía; se devuelve el comprobante
      original sin volver a procesar.
    - **400**: el cuerpo no es JSON válido o no es un objeto; no se registra transacción.
    """
    try:
        cuerpo = json.loads(await request.body())
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise SolicitudInvalida("El cuerpo no es JSON válido; no se registró la transacción") from e
    resultado = await servicio.procesar(cuerpo)
    if resultado.repetida:
        response.headers["X-Solicitud-Repetida"] = "true"
    return _edo(resultado.transaccion)


RUTA_SOL_TRANSF: dict[str, Any] = {
    "endpoint": sol_transf,
    "methods": ["POST"],
    "response_model": EdoTransf,
    "status_code": 200,
    "summary": "SolTransf (8): solicitar transferencia, depósito o retiro",
    "responses": {400: {"model": ErrorRespuesta, "description": "Cuerpo que no es JSON válido"}},
    "openapi_extra": {
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": _esquema_en_linea(SolTransf)}},
        }
    },
}

router.add_api_route("", operation_id="sol_transf_v1", **RUTA_SOL_TRANSF)


@router.get("", response_model=Pagina[TransaccionBitacora], summary="IG 6.1 Bitácora de transacciones")
async def bitacora(
    servicio: TransaccionesDep,
    estatus: Estatus | None = None,
    tipo: TipoOperacion | None = None,
    sistema: Sistema | None = None,
    codigo_rechazo: CodigoRechazo | None = None,
    q: Annotated[str | None, Query(min_length=1, max_length=50, description="Folio, cuenta o concepto")] = None,
    desde: date | None = None,
    hasta: date | None = None,
    pagina: PaginaQ = 1,
    tamano: TamanoQ = 50,
) -> Pagina[TransaccionBitacora]:
    """Consulta de solo lectura de todas las operaciones recibidas, la más reciente primero."""
    filtro = FiltroBitacora(
        estatus=estatus.value if estatus else None,
        tipo_operacion=tipo.value if tipo else None,
        sistema_solicitante=sistema.value if sistema else None,
        codigo_rechazo=codigo_rechazo.value if codigo_rechazo else None,
        texto=q,
        desde=desde,
        hasta=hasta,
        pagina=pagina,
        tamano=tamano,
    )
    total, filas = await servicio.bitacora(filtro)
    return Pagina[TransaccionBitacora](total=total, pagina=pagina, tamano=tamano, datos=[_bitacora(t) for t in filas])


@router.get(
    "/{folio_operacion}",
    response_model=TransaccionDetalle,
    responses={404: {"model": ErrorRespuesta}},
    summary="Detalle de una transacción con sus movimientos",
)
async def detalle(folio_operacion: str, servicio: TransaccionesDep) -> TransaccionDetalle:
    tx = await servicio.detalle(folio_operacion.strip().upper())
    datos = _bitacora(tx).model_dump()
    return TransaccionDetalle(
        **datos,
        concepto=tx.concepto,
        fecha_hora_solicitud=con_zona(tx.fecha_hora_solicitud, zona()),
        motivo_rechazo=ServicioTransacciones.motivo(tx.codigo_rechazo),
        movimientos=[MovimientoSalida.model_validate(m) for m in tx.movimientos],
    )
