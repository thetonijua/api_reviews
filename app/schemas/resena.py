from pydantic import BaseModel, ConfigDict, Field
from datetime import date, datetime
from typing import Optional, List



class ResenaBase(BaseModel):
    plataforma: str = "Google Maps"
    autor: Optional[str] = None
    es_local_guide: bool = False
    calificacion: float = Field(ge=1, le=5)
    fecha: str
    comentario: Optional[str] = None
    me_gusta:int = 0
    respuesta_dueno: Optional[str] = None

class ResenaCreate(ResenaBase):
    empresa_id: int # Obligatorio al crear, para saber a quién pertenece

class ResenaResponse(ResenaBase):
    id: int
    empresa_id: int
    fecha_estimada: Optional[date] = None
    precision_fecha: Optional[str] = None
    fecha_extraccion: Optional[datetime] = None

    # Esto le dice a Pydantic que lea los datos desde SQLAlchemy (modo ORM)
    model_config = ConfigDict(from_attributes=True)

