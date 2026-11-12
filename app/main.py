from fastapi import FastAPI
from app.core.database import engine, Base

# Importamos la "caja" de rutas que acabamos de crear
from app.routers import resena, empresa, nlp

# Crea las tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CreceBit - API", version="1.0.0")

app.include_router(resena.router)
app.include_router(empresa.router)
app.include_router(nlp.router)

@app.get("/")
def read_root():
    return {"mensaje": "Bienvenido a la API de reseñas"}