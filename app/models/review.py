from sqlalchemy import Column, Integer, String, Float, DateTime
from app.core.database import Base

class Review(Base):
    # Nombre que tendrá la tabla en MySQL
    __tablename__ = "reviews"

    #columnas
    id = Column(Integer, primary_key=True, index=True)
    plataforma = Column(String(30), index=True)
    autor = Column(String(100))
    calificacion = Column(Float)
    texto = Column(String(500))
    fecha_publicacion = Column(String(100))