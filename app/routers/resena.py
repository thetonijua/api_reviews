from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func

# Importamos la conexión a BD y nuestros modelos/esquemas actualizados
from app.core.database import get_db
from crecebit_reputation.app.models.resena import Empresa, Resena
from crecebit_reputation.app.schemas.resena import EmpresaCreate, EmpresaResponse, ResenaCreate, ResenaResponse

router = APIRouter()



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

# ==========================================
# RUTAS DE ANÁLISIS Y BENCHMARKING
# ==========================================

@router.get("/benchmarking", tags=["Análisis"])
def obtener_resumen_competitivo(db: Session = Depends(get_db)):
    """
    Devuelve un resumen comparativo de todas las empresas en la base de datos.
    Calcula el total de reseñas y el promedio exacto de estrellas.
    """
    resultados = db.query(
        Empresa.nombre,
        func.count(Resena.id).label("total_resenas"),
        func.avg(Resena.calificacion).label("promedio_estrellas"),
        # Opcional: Contar cuántas reseñas tienen respuesta del dueño
        func.sum(func.case((Resena.respuesta_dueno != "", 1), else_=0)).label("respuestas_dueno")
    ).outerjoin(Resena, Empresa.id == Resena.empresa_id).group_by(Empresa.id).all()

    # Formateamos los datos para que el JSON salga limpio
    benchmarking = []
    for fila in resultados:
        benchmarking.append({
            "empresa": fila.nombre,
            "total_resenas": fila.total_resenas,
            "promedio_estrellas": round(fila.promedio_estrellas, 2) if fila.promedio_estrellas else 0.0,
            "tasa_respuesta": round((fila.respuestas_dueno / fila.total_resenas * 100), 1) if fila.total_resenas > 0 else 0.0
        })

    # Ordenamos el ranking por promedio de estrellas (de mayor a menor)
    benchmarking.sort(key=lambda x: x["promedio_estrellas"], reverse=True)

    return benchmarking