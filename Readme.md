# CreceBit - API de Reseñas 📊

Sistema de extracción (scraping), carga (ETL) y exposición (API REST) de reseñas de clientes, orientado a **análisis de reputación y benchmarking competitivo** para negocios turísticos (hoteles, viñas, restaurantes).

Cada negocio se registra como `Empresa`, marcada como cliente (`es_cliente=True`) o competencia, y la API permite comparar su desempeño y analizar de qué hablan sus clientes.

## 🚀 Tecnologías

* **API:** [FastAPI](https://fastapi.tiangolo.com/) y Pydantic
* **Base de datos:** MySQL + SQLAlchemy (driver PyMySQL)
* **NLP:** [spaCy](https://spacy.io/) con el modelo `es_core_news_sm`
* **Scraping:** [Playwright](https://playwright.dev/python/)
* **Lenguaje:** Python 3.12+

## 📁 Estructura

    /
    ├── app/
    │   ├── core/database.py   # Conexión a la base de datos
    │   ├── models/            # Modelos SQLAlchemy (empresa, resena)
    │   ├── schemas/           # Esquemas Pydantic (validación JSON)
    │   ├── routers/           # Endpoints (empresas, reseñas, NLP)
    │   └── main.py            # Punto de entrada de FastAPI
    ├── scraper.py             # Extrae reseñas de Google Maps a CSV
    ├── load_csv_bd.py         # Carga el CSV a la base de datos (ETL)
    ├── requirements.txt
    ├── Dockerfile
    └── .env                   # Variables de entorno (no versionado)

## ⚙️ Instalación

**1. Clonar el repositorio y crear el entorno virtual**

    git clone https://github.com/thetonijua/api_reviews.git
    cd api_reviews
    python -m venv venv
    source venv/bin/activate          # Linux / macOS
    source venv/Scripts/activate      # Windows (Git Bash)

**2. Instalar dependencias** (incluye el modelo de spaCy en español)

    pip install -r requirements.txt
    playwright install chromium       # solo si vas a usar el scraper

**3. Configurar variables de entorno**

Crea un archivo `.env` en la raíz del proyecto:

    SQLALCHEMY_DATABASE_URL=mysql+pymysql://usuario:password@localhost:3306/tu_base_de_datos

**4. Si ya tenías una base de datos creada con una versión anterior**

Ejecuta una vez la migración, que agrega la detección de duplicados, elimina las reseñas repetidas y las que no tienen calificación válida:

    python -m scripts.migrar_001_deduplicar

## 🔄 Flujo de uso

**Etapa 1: Extracción (scraping).** Edita la lista de negocios al final de `scraper.py` y ejecútalo. Genera `resenas_benchmarking.csv`.

    python scraper.py

**Etapa 2: Carga a la base de datos (ETL).** Crea las empresas que no existan y carga sus reseñas. Se puede ejecutar varias veces: las reseñas que ya están en la base se omiten y las que no tienen una calificación válida se descartan.

    python load_csv_bd.py

**Etapa 3: Levantar la API**

    uvicorn app.main:app --reload

Documentación interactiva (Swagger UI): **http://localhost:8000/docs**

## 🐳 Docker

    docker build -t crecebit-api .
    docker run -p 8000:8000 -e SQLALCHEMY_DATABASE_URL=mysql+pymysql://usuario:password@host:3306/base crecebit-api

## 🌐 Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/empresas` | Lista las empresas con sus reseñas |
| `POST` | `/empresas` | Crea una empresa |
| `GET` | `/resenas` | Lista reseñas (paginación con `skip` y `limit`) |
| `POST` | `/resenas` | Crea una reseña para una empresa existente |
| `GET` | `/benchmarking` | Compara empresas: total de reseñas, promedio de estrellas y tasa de respuesta del dueño |
| `GET` | `/nlp/conceptos/{nombre_empresa}` | Los 10 conceptos (sustantivos y adjetivos) más mencionados en las reseñas de una empresa |
