from sqlalchemy import Column, Integer, String, Float, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), index=True, unique=True, nullable=False) # Ej: "Casino Enjoy Santa Cruz"
    sector = Column(String(100), nullable=True)              # Ej: "Hotelería", "Gastronomía"
    es_cliente = Column(Boolean, default=False)              # True = Tu cliente, False = Competencia
    
    # Relación: Una empresa puede tener muchas reseñas
    resenas = relationship("Resena", back_populates="empresa", cascade="all, delete-orphan")
    
    # Usamos el string "Resena" para evitar importaciones circulares
