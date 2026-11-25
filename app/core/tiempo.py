"""Manejo de fechas: la BD guarda TIMESTAMP sin zona en la hora local del Banco."""

from datetime import datetime
from zoneinfo import ZoneInfo


def ahora_local(zona: ZoneInfo) -> datetime:
    """Hora local actual sin tzinfo (se guarda así en columnas TIMESTAMP)."""
    return datetime.now(zona).replace(tzinfo=None, microsecond=0)


def a_local_sin_zona(valor: datetime, zona: ZoneInfo) -> datetime:
    """Convierte una fecha recibida a hora local sin zona. Si llega sin zona, se asume hora local."""
    if valor.tzinfo is None:
        return valor.replace(microsecond=0)
    return valor.astimezone(zona).replace(tzinfo=None, microsecond=0)


def con_zona(valor: datetime | None, zona: ZoneInfo) -> datetime | None:
    """Agrega la zona del Banco a una fecha leída de la BD para devolverla con offset (-07:00)."""
    if valor is None:
        return None
    return valor.replace(tzinfo=zona) if valor.tzinfo is None else valor.astimezone(zona)
