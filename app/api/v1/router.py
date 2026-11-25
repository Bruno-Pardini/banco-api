from fastapi import APIRouter

from app.api.v1.endpoints import catalogos, clientes, cuentas, transacciones

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(transacciones.router, prefix="/transacciones", tags=["Transacciones (SolTransf 8 / EdoTransf 9)"])
api_v1.include_router(clientes.router, prefix="/clientes", tags=["Clientes"])
api_v1.include_router(cuentas.router, prefix="/cuentas", tags=["Cuentas"])
api_v1.include_router(catalogos.router, tags=["Catálogos"])

# Ruta exacta del contrato del Paso 8 (POST /api/transacciones), la que ya consumen los 8 procesos.
contrato = APIRouter(prefix="/api", tags=["Contrato Paso 8"])
contrato.add_api_route("/transacciones", operation_id="sol_transf_contrato", **transacciones.RUTA_SOL_TRANSF)
