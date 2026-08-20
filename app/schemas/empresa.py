from pydantic import BaseModel, ConfigDict
from typing import Optional, List

from app.schemas.resena import ResenaResponse

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