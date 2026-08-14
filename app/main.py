from fastapi import FastAPI
from app.core.database import engine, Base

# Importamos la "caja" de rutas que acabamos de crear
from app.routers import review

# Crea las tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CreceBit - API", version="1.0.0")

# "Enchufamos" las rutas al archivo principal
app.include_router(review.router)

@app.get("/")
def read_root():
    return {"mensaje": "Bienvenido a la API de reseñas"}