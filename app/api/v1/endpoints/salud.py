from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import SesionDep
from app.core.config import get_settings
from app.schemas.comun import Salud

router = APIRouter()


@router.get("/health", response_model=Salud, responses={503: {"model": Salud}}, tags=["Salud"])
async def health(session: SesionDep) -> Salud | JSONResponse:
    version = get_settings().APP_VERSION
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503, content=Salud(estado="degradado", base_de_datos="sin conexión", version=version).model_dump()
        )
    return Salud(estado="ok", base_de_datos="ok", version=version)
