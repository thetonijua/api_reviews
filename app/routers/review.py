from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# Importamos la conexión a BD y nuestros modelos/esquemas actualizados
from app.core.database import get_db
from app.models.review import Empresa, Resena
from app.schemas.review import EmpresaCreate, EmpresaResponse, ResenaCreate, ResenaResponse

router = APIRouter()

# ==========================================
# RUTAS PARA EMPRESAS
# ==========================================

@router.post("/empresas", response_model=EmpresaResponse, tags=["Empresas"])
def crear_empresa(empresa: EmpresaCreate, db: Session = Depends(get_db)):
    nueva_empresa = Empresa(**empresa.model_dump())
    db.add(nueva_empresa)
    db.commit()
    db.refresh(nueva_empresa)
    return nueva_empresa

@router.get("/empresas", response_model=List[EmpresaResponse], tags=["Empresas"])
def listar_empresas(db: Session = Depends(get_db)):
    # Al pedir las empresas, el schema EmpresaResponse incluirá automáticamente sus reseñas
    return db.query(Empresa).all()

# ==========================================
# RUTAS PARA RESEÑAS
# ==========================================

@router.post("/resenas", response_model=ResenaResponse, tags=["Reseñas"])
def crear_resena(resena: ResenaCreate, db: Session = Depends(get_db)):
    # Verificamos que la empresa exista antes de asignarle una reseña
    empresa_existe = db.query(Empresa).filter(Empresa.id == resena.empresa_id).first()
    if not empresa_existe:
        raise HTTPException(status_code=404, detail="La empresa no existe en la base de datos")
    
    nueva_resena = Resena(**resena.model_dump())
    db.add(nueva_resena)
    db.commit()
    db.refresh(nueva_resena)
    return nueva_resena

@router.get("/resenas", response_model=List[ResenaResponse], tags=["Reseñas"])
def listar_resenas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Resena).offset(skip).limit(limit).all()