from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class BenchmarkingResponse(BaseModel):
    empresa: str
    total_resenas: int
    promedio_estrellas: float
    tasa_respuesta: float