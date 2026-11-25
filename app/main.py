"""Punto de entrada: uvicorn app.main:app"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.manejadores import registrar_manejadores
from app.api.v1.endpoints import salud
from app.api.v1.router import api_v1, contrato
from app.core.config import get_settings
from app.core.logging import configurar_logging
from app.db.session import get_engine

DESCRIPCION = """
API del proceso **PR06B · Procesamiento de Transacciones Bancarias** (Banco E6 · BCO) del Hotel Resort Sierra Madre.

* **SolTransf (8)** — `POST /api/transacciones` (alias versionado `POST /api/v1/transacciones`): recibe el FR06-03.
* **EdoTransf (9)** — respuesta HTTP de la misma llamada con el FR06-04.
* Consumidores: RES, VST, VGS, SRE, SPA, GEE, GJA y CIO.
* **IG 6.1 Bitácora de transacciones** — `GET /api/v1/transacciones`.
"""


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await get_engine().dispose()


def create_app() -> FastAPI:
    s = get_settings()
    configurar_logging(s.LOG_LEVEL)
    app = FastAPI(
        title=s.APP_NAME,
        version=s.APP_VERSION,
        description=DESCRIPCION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    if s.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware, allow_origins=s.CORS_ORIGINS, allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["*"], expose_headers=["X-Solicitud-Repetida"],
        )
    registrar_manejadores(app)
    app.include_router(salud.router)
    app.include_router(contrato)
    app.include_router(api_v1)
    return app


app = create_app()
