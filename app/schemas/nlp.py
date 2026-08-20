from pydantic import BaseModel

class ConceptoFrecuente(BaseModel):
    palabra: str
    menciones: int