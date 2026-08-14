# Crece Bit - API de Reseñas de Google Maps 📊

Este proyecto es un sistema completo de extracción (Scraping), transformación (ETL) y exposición (API REST) de reseñas de clientes desde Google Maps. Está diseñado para recopilar datos de negocios de forma automatizada y servirlos a través de endpoints rápidos y documentados.

## 🚀 Tecnologías Utilizadas

* **Backend / API:** [FastAPI](https://fastapi.tiangolo.com/) y Pydantic.
* **Scraping:** [Playwright](https://playwright.dev/python/) (simulación de navegación humana).
* **Base de Datos & ORM:** MySQL, SQLAlchemy y Python-dotenv.
* **Lenguaje:** Python 3.x

## 📁 Arquitectura del Proyecto

El proyecto sigue una estructura modular para separar responsabilidades:

    /
    ├── app/
    │   ├── api/            # Configuraciones adicionales de la API
    │   ├── core/           # Configuración central (ej. conexión a BD)
    │   ├── models/         # Modelos de SQLAlchemy (Tablas BD)
    │   ├── routers/        # Rutas y Endpoints de FastAPI
    │   ├── schemas/        # Esquemas de Pydantic (Validación JSON)
    │   ├── services/       # Lógica de negocio 
    │   └── main.py         # Punto de entrada de FastAPI
    ├── cargar_csv.py       # Script ETL para migrar datos a MySQL
    ├── .env                # Variables de entorno (No versionado)
    ├── .gitignore          # Archivos ignorados por Git
    └── README.md           # Documentación del proyecto

## ⚙️ Configuración e Instalación

**1. Clonar el repositorio y crear entorno virtual:**
    
    git clone https://github.com/TU-USUARIO/TU-REPOSITORIO.git
    cd TU-REPOSITORIO
    python -m venv venv
    source venv/Scripts/activate  # En Windows (Git Bash)

**2. Instalar dependencias:**

    pip install fastapi uvicorn sqlalchemy pymysql pydantic python-dotenv playwright
    playwright install chromium

**3. Configurar Variables de Entorno:**
Crea un archivo llamado `.env` en la carpeta `app/` (o en la raíz, dependiendo de tu configuración exacta) con tus credenciales de MySQL:

    SQLALCHEMY_DATABASE_URL=mysql+pymysql://usuario:password@localhost:3306/tu_base_de_datos

## 🔄 Flujo de Uso

El sistema funciona en 3 etapas principales:

### Etapa 1: Extracción de Datos (Scraping)
Ejecuta el script de Playwright para navegar por Google Maps, evitar bloqueos de bots y descargar las reseñas a un archivo `resenas_casino.csv`.

### Etapa 2: Carga a la Base de Datos (ETL)
Migra los datos del archivo CSV directamente a tu tabla MySQL transformando los tipos de datos correspondientes (ej. calificaciones a formato `Float`).

    python cargar_csv.py

### Etapa 3: Iniciar la API REST
Levanta el servidor local con recarga automática:

    uvicorn app.main:app --reload

## 🌐 Endpoints Disponibles

Una vez iniciada la API, puedes acceder a la documentación interactiva (Swagger UI) generada automáticamente ingresando a:
👉 **`http://localhost:8000/docs`**

* **`GET /resenas`**: Obtiene el listado de reseñas procesadas. Soporta paginación mediante los parámetros `skip` y `limit`.