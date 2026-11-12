from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# Importamos la conexión a BD y nuestros modelos/esquemas actualizados
from app.core.database import get_db
from app.models.resena import Resena, calcular_hash
from app.schemas.resena import ResenaCreate, ResenaResponse
from app.models.empresa import Empresa
from app.services.fechas import estimar_fecha
from datetime import datetime


router = APIRouter()



@router.post("/resenas", response_model=ResenaResponse, tags=["Reseñas"])
def crear_resena(resena: ResenaCreate, db: Session = Depends(get_db)):
    # Verificamos que la empresa exista antes de asignarle una reseña
    empresa_existe = db.query(Empresa).filter(Empresa.id == resena.empresa_id).first()
    if not empresa_existe:
        raise HTTPException(status_code=404, detail="La empresa no existe en la base de datos")
    
    hash_unico = calcular_hash(resena.empresa_id, resena.plataforma, resena.autor, resena.comentario)
    if db.query(Resena).filter(Resena.hash_unico == hash_unico).first():
        raise HTTPException(status_code=409, detail="Esta reseña ya existe para la empresa")

    ahora = datetime.now()
    fecha_estimada, precision = estimar_fecha(resena.fecha, ahora)
    nueva_resena = Resena(
        **resena.model_dump(),
        hash_unico=hash_unico,
        fecha_estimada=fecha_estimada,
        precision_fecha=precision,
        fecha_extraccion=ahora,
    )
    db.add(nueva_resena)
    db.commit()
    db.refresh(nueva_resena)
    return nueva_resena

@router.get("/resenas", response_model=List[ResenaResponse], tags=["Reseñas"])
def listar_resenas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Resena).offset(skip).limit(limit).all()
