from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func

# Importamos la conexión a BD y nuestros modelos/esquemas actualizados
from app.core.database import get_db
from app.models.empresa import Empresa
from app.schemas.empresa import EmpresaCreate, EmpresaResponse

router = APIRouter()


@router.post("/empresas", response_model=EmpresaResponse, tags=["Empresas"])
def crear_empresa(empresa: EmpresaCreate, db: Session = Depends(get_db)):
    if db.query(Empresa).filter(Empresa.nombre == empresa.nombre).first():
        raise HTTPException(status_code=409, detail="Ya existe una empresa con ese nombre")

    nueva_empresa = Empresa(**empresa.model_dump())
    db.add(nueva_empresa)
    db.commit()
    db.refresh(nueva_empresa)
    return nueva_empresa

@router.get("/empresas", response_model=List[EmpresaResponse], tags=["Empresas"])
def listar_empresas(db: Session = Depends(get_db)):
    # Al pedir las empresas, el schema EmpresaResponse incluirá automáticamente sus reseñas
    return db.query(Empresa).all()