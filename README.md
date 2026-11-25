# API Banco E6 · PR06B Procesamiento de Transacciones Bancarias

API REST del Banco (E6 · BCO) del Hotel Resort Sierra Madre, construida a partir del documento **Paso 8 · Pruebas de interconectividad**.

| Interfaz | Endpoint | Formato |
|---|---|---|
| **SolTransf (8)** | `POST /api/transacciones` (ruta del contrato) · alias `POST /api/v1/transacciones` | FR06-03 Solicitud de Transferencia |
| **EdoTransf (9)** | Respuesta HTTP 200 de la misma llamada | FR06-04 Comprobante de Transacción |
| **IG 6.1 Bitácora** | `GET /api/v1/transacciones` y `GET /api/v1/transacciones/{folio_operacion}` | Solo lectura |

Los consumidores son RES, VST, VGS, SRE, SPA, GEE, GJA y CIO. El stack es Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 async con asyncpg, Alembic, PostgreSQL 16 y Docker.

---

## 1. Estructura del proyecto

```
banco-api/
├── .vscode/                 settings, launch (uvicorn, alembic, pytest), tasks (docker), extensiones
├── alembic/
│   ├── env.py               migraciones con motor async; URL tomada de DATABASE_URL
│   └── versions/0001_esquema_inicial.py   5 tablas + secuencia de folio + catálogo R01–R06
├── app/
│   ├── main.py              FastAPI, CORS, manejadores, routers, /docs y /redoc
│   ├── core/                config.py (pydantic-settings), dominio.py (catálogos), errores.py, tiempo.py
│   ├── db/                  base.py (convención de nombres), session.py (engine + sesión async)
│   ├── models/              cliente, cuenta, movimiento, transaccion, codigo_rechazo
│   ├── schemas/             SolTransf / EdoTransf, bitácora, clientes, cuentas, errores
│   ├── repositories/        acceso a datos SQL + unidad de trabajo (uow.py)
│   ├── services/            reglas.py (reglas puras R01–R06), transacciones.py (caso de uso), administracion.py
│   ├── api/                 deps.py, manejadores.py (errores centralizados), v1/endpoints/*
│   └── scripts/seed.py      datos de demostración (cuentas de la IG 6.1)
├── tests/                   56 pruebas: reglas y servicio con unidad de trabajo en memoria
├── http/banco.http          peticiones listas para REST Client
├── docker/entrypoint.sh     migra, carga demo (opcional) y arranca uvicorn
├── Dockerfile               multistage, usuario no-root, HEALTHCHECK
├── docker-compose.yml       api + postgres:16 con healthcheck y volumen
├── .env.example  .env.local.example
├── alembic.ini  pyproject.toml  requirements.txt  requirements-dev.txt
```

La dependencia va en una sola dirección: **endpoints → servicios → puertos (Protocol) ← repositorios SQL**. El servicio de transacciones no importa SQLAlchemy ni FastAPI. Por eso se puede probar sin base de datos.

---

## 2. Levantar con Docker

```bash
cp .env.example .env                 # cambia POSTGRES_PASSWORD y la misma contraseña en DATABASE_URL
docker compose up -d --build         # db espera healthy → api migra (alembic upgrade head) y carga demo
docker compose ps                    # ambos servicios "healthy"
docker compose logs -f api
```

* Documentación: http://localhost:8000/docs y http://localhost:8000/redoc
* Salud: http://localhost:8000/health. Responde 200 si la BD contesta y 503 si no.

Comandos manuales:

```bash
docker compose exec api alembic upgrade head          # migraciones
docker compose exec api alembic current
docker compose exec api python -m app.scripts.seed    # datos demo (idempotente)
docker compose exec db psql -U banco -d banco -c "select * from transaccion order by fecha_hora desc limit 5;"
docker compose down            # conserva datos   ·   docker compose down -v  borra el volumen
```

Para no cargar datos demo en producción pon `SEED_DEMO=false` en `.env`.

## 3. Desarrollo y depuración en VS Code

1. Instala las extensiones recomendadas (VS Code las propone al abrir la carpeta).
2. Crea el entorno virtual y levanta solo la base:
   ```bash
   python3.12 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements-dev.txt
   cp .env.local.example .env.local                            # host localhost, misma contraseña que .env
   docker compose up -d db
   ```
3. En **Run and Debug** ejecuta, en este orden:
   - **Alembic: upgrade head**
   - **API Banco (uvicorn --reload)**, que acepta breakpoints.
4. Para los datos demo: `set -a && . ./.env.local && set +a && python -m app.scripts.seed`.
5. Para las pruebas: usa la vista **Testing** o `pytest -q`.
6. Abre `http/banco.http` y da clic en **Send Request** sobre cada bloque.

También hay tareas en *Terminal → Run Task*: `docker: levantar`, `docker: migrar`, `docker: datos demo`, `pytest`.

## 4. Pruebas con curl

**SolTransf (8) del documento → EdoTransf (9) APROBADA**

```bash
curl -s -X POST http://localhost:8000/api/transacciones -H "Content-Type: application/json" -d '{
  "folio_solicitud": "RES-2026-000001", "sistema_solicitante": "RES",
  "fecha_hora": "2026-11-15T09:04:12-07:00",
  "cuenta_origen": "3514126802", "cuenta_destino": "8103021410",
  "titular_origen": "Mariana Salcido Ruiz", "importe": 16650.00,
  "concepto": "Pago reservación SMR-2026-00142" }'
```
```json
{ "folio_operacion": "OP-2026-000001", "folio_solicitud": "RES-2026-000001",
  "fecha_hora": "2026-11-24T17:20:05-07:00", "tipo_operacion": "TRANSFERENCIA",
  "cuenta_origen": "3514126802", "cuenta_destino": "8103021410", "importe": 16650.0,
  "estatus": "APROBADA", "codigo_rechazo": null }
```

**Rechazos.** Las cuentas vienen del seed. Todos responden 200 con `"estatus": "RECHAZADA"`.

| Caso | Cambio sobre el ejemplo | Código |
|---|---|---|
| Cuenta origen inexistente o inactiva | `"cuenta_origen": "9000000001"` | R01 |
| Cuenta destino inexistente | `"cuenta_destino": "1111111111"` | R02 |
| Fondos insuficientes | origen `7448067658` (titular *Lucía Fimbres Ochoa*), importe 3800 | R03 |
| Titular distinto | `"titular_origen": "Otra Persona"` | R04 |
| Falta un campo o importe ≤ 0 | `"importe": 0` | R06 |

**Otros casos**

```bash
# Folio repetido: mismo comprobante y cabecera X-Solicitud-Repetida: true (no se reprocesa)
curl -si -X POST http://localhost:8000/api/transacciones -H "Content-Type: application/json" \
  -d '{"folio_solicitud":"RES-2026-000001","sistema_solicitante":"RES","fecha_hora":"2026-11-15T09:04:12-07:00","cuenta_origen":"3514126802","cuenta_destino":"8103021410","titular_origen":"Mariana Salcido Ruiz","importe":1}' | grep -i -E "HTTP/|x-solicitud"

# 400: JSON inválido (no se registra)
curl -si -X POST http://localhost:8000/api/transacciones -H "Content-Type: application/json" -d '{"folio":' | head -1

# Bitácora IG 6.1 y detalle
curl -s "http://localhost:8000/api/v1/transacciones?estatus=RECHAZADA&sistema=RES&pagina=1&tamano=20"
curl -s http://localhost:8000/api/v1/transacciones/OP-2026-000001        # 404 si no existe

# Clientes y cuentas (201 / 200 / 204 / 404 / 409 / 422)
curl -s -X POST http://localhost:8000/api/v1/clientes -H "Content-Type: application/json" -d '{"nombre":"Ana Valenzuela Duarte"}'
curl -s http://localhost:8000/api/v1/cuentas/3514126802/movimientos
```

## 5. Endpoints

| Método | Ruta | Códigos |
|---|---|---|
| POST | `/api/transacciones`, `/api/v1/transacciones` | 200 (EdoTransf), 400 |
| GET | `/api/v1/transacciones` · filtros `estatus, tipo, sistema, codigo_rechazo, q, desde, hasta, pagina, tamano` | 200, 422 |
| GET | `/api/v1/transacciones/{folio_operacion}` | 200, 404 |
| POST / GET | `/api/v1/clientes` | 201 / 200, 409, 422 |
| GET / PATCH / DELETE | `/api/v1/clientes/{id}` | 200 / 200 / 204, 404, 409 |
| POST / GET | `/api/v1/cuentas` | 201 / 200, 404, 409, 422 |
| GET / PATCH | `/api/v1/cuentas/{numero}` (PATCH solo estatus) | 200, 404 |
| GET | `/api/v1/cuentas/{numero}/movimientos` | 200, 404 |
| GET | `/api/v1/codigos-rechazo` | 200 |
| GET | `/health` | 200, 503 |

Todos los errores salen con la forma `{"codigo", "mensaje", "detalles"}`. Un error no controlado devuelve 500 `ERROR_INTERNO` y queda en el log.

---

## 6. Supuestos y decisiones de diseño

**Contrato**

1. **Ruta.** El documento fija `POST /api/transacciones` y ocho procesos ya la consumen, así que se conserva tal cual. También se expone el alias versionado `/api/v1/transacciones`. Ambas usan el mismo código.
2. **No se responde 422 en SolTransf (8).** El Paso 8 dice que los datos incompletos o con importe ≤ $0.00 responden **200 con RECHAZADA · R06** y quedan registrados. Por eso el cuerpo se valida campo por campo en `services/reglas.py` y no con la validación automática de FastAPI. El 422 se usa solo en los endpoints de administración y en los filtros de consulta.
3. **400.** Solo se devuelve cuando el cuerpo no es JSON válido, como dice el documento, o cuando es JSON pero no es un objeto (por ejemplo, una lista). En ambos casos no se registra nada.
4. **Datos con formato inválido también son R06.** Por ejemplo: una cuenta que no tiene 10 dígitos o que llega como número JSON en vez de texto, más de 2 decimales, un concepto de más de 100 caracteres, una fecha inválida, o un `folio_solicitud` cuyo prefijo `XXX` no es el `sistema_solicitante`. El código R06 dice "solicitud incompleta" y es el único que cubre estos casos.
5. **`cuenta_destino`.** La llave es obligatoria. Si llega `""` o `null`, la operación es **RETIRO**. Si la llave **falta**, se responde R06. Así se evita que un sistema que olvidó el destino haga un retiro sin querer.
6. **Contradicción entre R02 y la regla de depósito.** El catálogo dice que R02 incluye "en una transferencia, igual a la origen", pero la regla de `cuenta_destino` dice que "igual a la origen = depósito". Se aplicó la regla de datos: destino igual a origen es **DEPOSITO**, así que una transferencia nunca tiene cuentas iguales. R02 queda para un destino inexistente o inactivo.
7. **Orden de validación.** Sigue la tabla de tareas: R06, después "Valida cuentas" (R01 → R02 → R04) y al final "Verifica fondo" (R03). Si hay varios problemas, se devuelve el primero.
8. **Titular (R04).** La comparación con `cliente.nombre` ignora mayúsculas, acentos y espacios repetidos.
9. **Depósito.** Abona a la cuenta origen sin revisar fondos, porque el dinero entra. El retiro y la transferencia sí revisan fondos.
10. **`fecha_hora` del EdoTransf (9).** Es la hora del procesamiento bancario, según la regla de la sección 6. En el ejemplo del documento coincide con la de la solicitud, pero se tomó como ilustrativo.

**Base de datos**

11. **Modelo de 5 tablas.** Es idéntico a la Figura 5: mismos nombres, tipos y llaves, incluida la llave compuesta `movimiento(folio_operacion, tipo_movimiento)`. `transaccion.cuenta_origen` y `cuenta_destino` no tienen llave foránea a `cuenta` (el diagrama tampoco la tiene), porque una solicitud con una cuenta inexistente también se registra (R01/R02).
12. **Columnas que aceptan nulos.** El documento no dice cuáles aceptan nulos. Las capturadas de la SolTransf son opcionales para poder registrar los R06. Un dato inválido se guarda como NULL. Un importe ≤ 0 sí se guarda, porque la IG 6.1 muestra un R06 con $0.00.
13. **Restricciones agregadas.** Para cuidar la integridad se agregaron:
    - `CHECK` de catálogos, saldo ≥ 0 y formato de cuenta y de folio.
    - Coherencia entre estatus y código: APROBADA sin código, RECHAZADA con código.
    - `UNIQUE(folio_solicitud)`, que respalda la idempotencia.
    - Índices para la bitácora.
14. **Valores que el documento no define.**
    - `tipo_cliente` (VARCHAR 9): HUESPED, EMPRESA, HOTEL o PROVEEDOR.
    - `cuenta.estatus` (VARCHAR 8): ACTIVA o INACTIVA.
    - `movimiento.tipo_movimiento` (VARCHAR 8): RETIRO o DEPOSITO.
    - `rfc` es único.
15. **`folio_operacion`.** Usa la secuencia `transaccion_folio_seq`: `OP-<año del procesamiento>-<consecutivo de 6 dígitos>`. El consecutivo es global, no se reinicia cada año y puede dejar huecos si hay un rollback. Al llegar a 999999 responde 500 `FOLIO_AGOTADO`.
16. **Fechas.** Las columnas son `TIMESTAMP` sin zona, como en el diagrama. Se guardan en la hora local `ZONA_HORARIA=America/Hermosillo`. Una fecha recibida con otra zona se convierte; una fecha sin zona se toma como local. Las respuestas salen con offset (`-07:00`).

**Concurrencia e idempotencia**

17. **Bloqueo de cuentas.** Cargo, abono, movimientos y transacción van en **una sola transacción** de PostgreSQL. Las cuentas se bloquean con `SELECT … FOR UPDATE` en orden de número, para evitar interbloqueos y saldos negativos con peticiones simultáneas.
18. **Folio repetido.** Si un `folio_solicitud` ya existe, se responde el comprobante original sin reprocesar, aunque cambie el contenido, y se agrega la cabecera `X-Solicitud-Repetida: true`. Si dos peticiones con el mismo folio llegan al mismo tiempo, la restricción única decide cuál gana y la otra recibe el original. Un R06 sin folio válido no se puede deduplicar: cada intento queda como un registro nuevo.
19. **R05.** Si hay un error técnico después de validar, se revierte todo y se registra la transacción como RECHAZADA · R05, sin movimientos ni cambios de saldo. Si tampoco se puede registrar el R05 (por ejemplo, la BD está caída), la respuesta es 500.

**Alcance**

20. **Endpoints de administración.** Los de `clientes`, `cuentas` y `codigos-rechazo` **no están en el Paso 8**. Se agregaron para poder dar de alta y consultar los datos que valida la SolTransf. El saldo solo cambia mediante transacciones; por API solo se activa o inactiva una cuenta, y no se borran cuentas.
21. **Autenticación.** El documento no define autenticación entre procesos, así que no se implementó. Antes de producción se recomienda una API key por sistema solicitante o mTLS, para verificar además que `sistema_solicitante` sea quien llama.
22. **VST y GJA.** No tienen flujo en el modelo, pero usan el mismo contrato que los demás procesos.
