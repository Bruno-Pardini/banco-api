#!/bin/sh
set -e
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "[entrypoint] alembic upgrade head"
  alembic upgrade head
fi
if [ "${SEED_DEMO:-false}" = "true" ]; then
  echo "[entrypoint] cargando datos de demostración"
  python -m app.scripts.seed
fi
exec "$@"
