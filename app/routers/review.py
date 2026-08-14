from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import review as models_review
from app.schemas.review import ReviewCreate, ReviewResponse

router = APIRouter(
    prefix="/reviews",
    tags=["Reseñas"]
)

# --- POST ---
@router.post("/", response_model=ReviewResponse, tags=["Reseñas"])
async def create_review(review: ReviewCreate, db: Session = Depends(get_db)):

    nueva_resena_db = models_review.Review(
        plataforma=review.plataforma,
        autor=review.autor,
        calificacion=review.calificacion,
        texto=review.texto,
        fecha_publicacion=review.fecha_publicacion
    )
    db.add(nueva_resena_db)
    db.commit()
    db.refresh(nueva_resena_db)
    return nueva_resena_db

# --- GET ---
@router.get("/", response_model=list[ReviewResponse], tags=["Reseñas"])
async def read_reviews(db: Session = Depends(get_db)):
    reviews = db.query(models_review.Review).all()
    return reviews