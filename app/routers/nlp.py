from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import spacy
from collections import Counter

from app.core.database import get_db
from app.models.empresa import Empresa
from app.models.resena import Resena
from app.schemas.nlp import ConceptoFrecuente

router = APIRouter(prefix="/nlp", tags=["Inteligencia Artificial"])

nlp = spacy.load("es_core_news_sm")

@router.get("/conceptos/{nombre_empresa}", response_model=list[ConceptoFrecuente])
def obtener_conceptos_clave(nombre_empresa: str, db: Session = Depends(get_db)):
    """
    Extrae los 10 conceptos más mencionados (sustantivos y adjetivos) 
    en las reseñas de una empresa específica.
    """
    # 1. Buscamos la empresa
    empresa = db.query(Empresa).filter(Empresa.nombre == nombre_empresa).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
        
    # 2. Traemos todos sus comentarios válidos
    resenas = db.query(Resena).filter(
        Resena.empresa_id == empresa.id,
        Resena.comentario != "[Sin texto]",
        Resena.comentario.isnot(None)
    ).all()
    
    if not resenas:
        return []
        
    # 3. Juntamos todo el texto y lo pasamos por la IA
    textos_completos = " ".join([r.comentario for r in resenas])
    doc = nlp(textos_completos.lower())
    
    # 4. Filtramos sustantivos, adjetivos y eliminamos palabras inútiles
    palabras_clave = [
        token.lemma_ for token in doc 
        if token.pos_ in ["NOUN", "ADJ"] 
        and not token.is_stop 
        and token.is_alpha
        and len(token.text) > 2
    ]
    
    # 5. Contamos y devolvemos el Top 10
    frecuencia = Counter(palabras_clave)
    top_10 = frecuencia.most_common(10)
    
    # Lo empaquetamos con el formato del Schema
    return [{"palabra": palabra, "menciones": cantidad} for palabra, cantidad in top_10]