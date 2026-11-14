from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.empresa import Empresa
from app.models.resena import Resena
from app.schemas.nlp import ConceptoFrecuente
from app.services.nlp import temas_frecuentes

router = APIRouter(prefix="/nlp", tags=["Inteligencia Artificial"])


@router.get("/conceptos/{nombre_empresa}", response_model=list[ConceptoFrecuente])
def obtener_conceptos_clave(nombre_empresa: str, db: Session = Depends(get_db)):
    """
    Extrae los 10 conceptos más mencionados (sustantivos y adjetivos)
    en las reseñas de una empresa específica.
    """
    empresa = db.query(Empresa).filter(Empresa.nombre == nombre_empresa).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    comentarios = [
        c for (c,) in db.query(Resena.comentario).filter(Resena.empresa_id == empresa.id, Resena.comentario.isnot(None))
    ]
    return [{"palabra": palabra, "menciones": cantidad} for palabra, cantidad in temas_frecuentes(comentarios)]
