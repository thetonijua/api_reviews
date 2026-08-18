from pydantic import BaseModel, ConfigDict
from typing import Optional, List



class ResenaBase(BaseModel):
    plataforma: str = "Google Maps"
    autor: Optional[str] = None
    es_local_guide: bool = False
    calificacion: float
    fecha: str
    comentario: Optional[str] = None
    me_gusta:int = 0
    respuesta_dueno: Optional[str] = None

class ResenaCreate(ResenaBase):
    empresa_id: int # Obligatorio al crear, para saber a quién pertenece

class ResenaResponse(ResenaBase):
    id: int
    empresa_id: int

    # Esto le dice a Pydantic que lea los datos desde SQLAlchemy (modo ORM)
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# SCHEMAS PARA EMPRESAS
# ==========================================

class EmpresaBase(BaseModel):
    nombre: str
    sector: Optional[str] = None
    es_cliente: bool = False

class EmpresaCreate(EmpresaBase):
    pass


class EmpresaResponse(EmpresaBase):
    id: int
    resenas: List[ResenaResponse] = []

    model_config = ConfigDict(from_attributes=True)