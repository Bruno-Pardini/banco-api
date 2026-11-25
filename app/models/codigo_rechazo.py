from sqlalchemy import CHAR, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CodigoRechazoModel(Base):
    """Catálogo R01–R06 (se llena en la migración inicial)."""

    __tablename__ = "codigo_rechazo"

    codigo: Mapped[str] = mapped_column(CHAR(3), primary_key=True)
    motivo: Mapped[str] = mapped_column(String(100), nullable=False)
