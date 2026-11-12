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

Ejecuta las migraciones en orden (cada una se puede repetir sin problema):

    python -m scripts.migrar_001_deduplicar
    python -m scripts.migrar_002_fechas --fecha-extraccion AAAA-MM-DD

* **001:** detecta duplicados, elimina las reseñas repetidas y las que no tienen calificación válida.
* **002:** calcula la fecha estimada de cada reseña. En `--fecha-extraccion` indica el día (aproximado) en que hiciste el scraping de los datos que ya tienes.

## 🔄 Flujo de uso

**Etapa 1: Extracción (scraping).** Sin argumentos, usa la lista de negocios definida al final de `scraper.py` y genera `resenas_benchmarking.csv`.

    python scraper.py

También puedes indicar los negocios, la cantidad de reseñas y el archivo de salida (útil para pruebas):

    python scraper.py "Hotel Vendimia Santa Cruz" --max 20 --salida prueba_hotel.csv

Si en alguna reseña no se encuentra la nota o la fecha, el scraper guarda el HTML de esa tarjeta en `diagnostico_scraper/` para poder revisarla.

**Etapa 2: Carga a la base de datos (ETL).** Crea las empresas que no existan y carga sus reseñas. Se puede ejecutar varias veces: las reseñas nuevas se agregan, las que ya están en la base se actualizan (respuesta del dueño, "me gusta" y fecha si viene más precisa) y las que no tienen una calificación válida se descartan.

    python load_csv_bd.py                     # carga resenas_benchmarking.csv
    python load_csv_bd.py prueba_hotel.csv    # o cualquier otro archivo

**Etapa 3: Levantar la API**

    uvicorn app.main:app --reload

Documentación interactiva (Swagger UI): **http://localhost:8000/docs**

## 📅 Fechas de las reseñas

Google Maps no muestra la fecha exacta de una reseña, sino el tiempo transcurrido ("hace 2 meses"). A partir de ese texto y de la fecha en que se hizo el scraping, se calcula una **fecha estimada** y su **precisión**:

| Texto de Google | Precisión | Confiable a nivel de |
|---|---|---|
| hace 5 horas / hace 3 días | `dia` | día |
| hace 2 semanas | `semana` | semana |
| hace 4 meses | `mes` | mes |
| hace 2 años | `anio` | año |

Las tendencias mensuales solo usan reseñas con precisión de día, semana o mes.

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
| `GET` | `/empresas/{empresa_id}/tendencias` | Reseñas y promedio de estrellas por mes (filtros opcionales `desde` y `hasta`) |
| `GET` | `/nlp/conceptos/{nombre_empresa}` | Los 10 conceptos (sustantivos y adjetivos) más mencionados en las reseñas de una empresa |
