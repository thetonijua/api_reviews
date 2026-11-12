from pydantic import BaseModel


class BenchmarkingResponse(BaseModel):
    empresa: str
    total_resenas: int
    promedio_estrellas: float
    tasa_respuesta: float


class TendenciaMensual(BaseModel):
    periodo: str               # "AAAA-MM"
    total_resenas: int
    promedio_estrellas: float


class TendenciaResponse(BaseModel):
    empresa: str
    resenas_incluidas: int
    resenas_excluidas: int     # sin fecha o con precisión de año: no se pueden ubicar en un mes
    meses: list[TendenciaMensual]
