from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# 1. El molde base con los datos comunes
class ReviewBase(BaseModel):
    plataforma: str = Field(..., description="Origen del dato (Google Maps, TripAdvisor, etc.)")
    autor: Optional[str] = Field(None, description="Autor de la reseña")
    calificacion: float = Field(..., ge=1, le=5, description="Nota del 1 al 5")
    texto: str
    fecha_publicacion: str

# 2. Molde para RECIBIR datos (cuando el scraper envía una nueva reseña)
class ReviewCreate(ReviewBase):
    pass # No añadimos nada extra, usa exactamente lo del Base

# 3. Molde para DEVOLVER datos (cuando tu frontend pida ver las reseñas)
class ReviewResponse(ReviewBase):
    id: int # Le agregamos un ID porque al devolverlo ya estará guardado en la BD
    class Config:
        from_attributes = True 