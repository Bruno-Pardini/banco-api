from fastapi import APIRouter

from app.api.deps import SesionDep
from app.schemas.transaccion import CodigoRechazoSalida
from app.services.administracion import codigos_rechazo

router = APIRouter()


@router.get("/codigos-rechazo", response_model=list[CodigoRechazoSalida], summary="Catálogo R01–R06")
async def listar_codigos_rechazo(session: SesionDep) -> list[CodigoRechazoSalida]:
    return [CodigoRechazoSalida.model_validate(c) for c in await codigos_rechazo(session)]
