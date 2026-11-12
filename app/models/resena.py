import hashlib

from sqlalchemy import Column, Integer, String, Float, Text, Boolean, ForeignKey, Date, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


def calcular_hash(empresa_id: int, plataforma: str | None, autor: str | None, comentario: str | None) -> str:
    """
    Huella única de una reseña para detectar duplicados.

    No incluye la fecha a propósito: el scraper la obtiene en formato relativo
    ("hace 2 meses"), que cambia entre una extracción y otra, y la misma reseña
    se duplicaría al volver a scrapear.
    """
    def normalizar(texto: str | None) -> str:
        return " ".join((texto or "").split()).lower()

    base = "|".join([str(empresa_id), normalizar(plataforma), normalizar(autor), normalizar(comentario)])
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


class Resena(Base):
    __tablename__ = "resenas"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    plataforma = Column(String(50), default="Google Maps")

    # Datos del autor
    autor = Column(String(150), nullable=True)
    es_local_guide = Column(Boolean, default=False)

    # Datos de la reseña
    calificacion = Column(Float, nullable=False)
    fecha = Column(String(50), nullable=False)        # Texto original de Google, ej: "hace 2 meses"
    fecha_estimada = Column(Date, nullable=True, index=True)  # Fecha calculada a partir del texto
    precision_fecha = Column(String(10), nullable=True)       # "dia", "semana", "mes" o "anio"
    fecha_extraccion = Column(DateTime, nullable=True)        # Cuándo se obtuvo la reseña
    comentario = Column(Text, nullable=True)
    me_gusta = Column(Integer, default=0)

    # Datos del negocio
    respuesta_dueno = Column(Text, nullable=True)

    # Evita cargar la misma reseña dos veces (ver calcular_hash)
    hash_unico = Column(String(64), unique=True, index=True, nullable=True)

    # Relación: Esta reseña pertenece a una empresa
    empresa = relationship("Empresa", back_populates="resenas")
