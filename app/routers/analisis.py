from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.empresa import Empresa
from app.models.resena import Resena
from app.services.diagnostico import generar_pdf, recolectar_datos
from app.schemas.analisis import BenchmarkingResponse, TendenciaMensual, TendenciaResponse

router = APIRouter(tags=["Análisis"])

# Precisiones que permiten ubicar una reseña en un mes concreto
PRECISIONES_MENSUALES = ("dia", "semana", "mes")


@router.get("/benchmarking", response_model=list[BenchmarkingResponse])
def obtener_resumen_competitivo(db: Session = Depends(get_db)):
    """
    Devuelve un resumen comparativo de todas las empresas en la base de datos.
    Calcula el total de reseñas, el promedio de estrellas y la tasa de respuesta del dueño.
    """
    resultados = (
        db.query(
            Empresa.nombre,
            func.count(Resena.id).label("total_resenas"),
            func.avg(Resena.calificacion).label("promedio_estrellas"),
            func.sum(case((Resena.respuesta_dueno != "", 1), else_=0)).label("respuestas_dueno"),
        )
        .outerjoin(Resena, Empresa.id == Resena.empresa_id)
        .group_by(Empresa.id, Empresa.nombre)
        .all()
    )

    benchmarking = [
        {
            "empresa": fila.nombre,
            "total_resenas": fila.total_resenas,
            "promedio_estrellas": round(float(fila.promedio_estrellas), 2) if fila.promedio_estrellas else 0.0,
            "tasa_respuesta": round(float(fila.respuestas_dueno or 0) / fila.total_resenas * 100, 1)
            if fila.total_resenas > 0 else 0.0,
        }
        for fila in resultados
    ]
    # Ranking por promedio de estrellas (de mayor a menor)
    benchmarking.sort(key=lambda x: x["promedio_estrellas"], reverse=True)
    return benchmarking


@router.get("/empresas/{empresa_id}/tendencias", response_model=TendenciaResponse)
def obtener_tendencias(
    empresa_id: int,
    desde: date | None = Query(None, description="Fecha inicial (AAAA-MM-DD)"),
    hasta: date | None = Query(None, description="Fecha final (AAAA-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    Cantidad de reseñas y promedio de estrellas por mes, según la fecha estimada.

    Las reseñas con precisión de año ("hace 2 años") no se incluyen, porque no se
    pueden ubicar en un mes concreto sin inventar el dato.
    """
    empresa = db.get(Empresa, empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    consulta = db.query(Resena.fecha_estimada, Resena.precision_fecha, Resena.calificacion).filter(
        Resena.empresa_id == empresa_id
    )
    if desde:
        consulta = consulta.filter(Resena.fecha_estimada >= desde)
    if hasta:
        consulta = consulta.filter(Resena.fecha_estimada <= hasta)

    por_mes: dict[str, list[float]] = defaultdict(list)
    excluidas = 0
    for fecha, precision, calificacion in consulta:
        if fecha is None or precision not in PRECISIONES_MENSUALES:
            excluidas += 1
            continue
        por_mes[fecha.strftime("%Y-%m")].append(calificacion)

    meses = [
        TendenciaMensual(
            periodo=periodo,
            total_resenas=len(notas),
            promedio_estrellas=round(sum(notas) / len(notas), 2),
        )
        for periodo, notas in sorted(por_mes.items())
    ]
    return TendenciaResponse(
        empresa=empresa.nombre,
        resenas_incluidas=sum(m.total_resenas for m in meses),
        resenas_excluidas=excluidas,
        meses=meses,
    )


@router.get(
    "/empresas/{empresa_id}/diagnostico",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}, "description": "Diagnóstico en PDF"}},
)
def descargar_diagnostico(
    empresa_id: int,
    competidores: list[int] | None = Query(None, description="IDs de los competidores (por defecto, todas las demás empresas)"),
    db: Session = Depends(get_db),
):
    """Diagnóstico de reputación en PDF: comparación con la competencia, temas y recomendaciones."""
    try:
        datos = recolectar_datos(db, empresa_id, competidores)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    nombre_archivo = "diagnostico_" + "".join(c if c.isalnum() else "_" for c in datos["cliente"]["nombre"]) + ".pdf"
    return Response(
        content=generar_pdf(datos),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )
