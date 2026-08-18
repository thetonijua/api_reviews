from sqlalchemy import Column, Integer, String, Float, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), index=True, nullable=False) # Ej: "Casino Enjoy Santa Cruz"
    sector = Column(String(100), nullable=True)              # Ej: "Hotelería", "Gastronomía"
    es_cliente = Column(Boolean, default=False)              # True = Tu cliente, False = Competencia
    
    # Relación: Una empresa puede tener muchas reseñas
    resenas = relationship("Resena", back_populates="empresa", cascade="all, delete-orphan")


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
    fecha = Column(String(50), nullable=False)  # Mantenemos String para simplificar el scraping por ahora
    comentario = Column(Text, nullable=True)
    me_gusta = Column(Integer, default=0)      
    
    # Datos del negocio
    respuesta_dueno = Column(Text, nullable=True) 
    
    # Relación: Esta reseña pertenece a una empresa
    empresa = relationship("Empresa", back_populates="resenas")