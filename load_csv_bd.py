import csv
import os
from datetime import datetime

from app.core.database import Base, SessionLocal, engine
from app.models.empresa import Empresa
from app.models.resena import Resena, calcular_hash
from app.services.fechas import es_mas_precisa, estimar_fecha

ARCHIVO_CSV = "resenas_benchmarking.csv"
PLATAFORMA = "Google Maps"


def parsear_calificacion(texto: str) -> float | None:
    """
    Convierte "4,5 estrellas" o "5 estrellas" en un número entre 1 y 5.
    Devuelve None si no se puede leer: esas reseñas se descartan en vez de
    guardarse como 0.0, que bajaría el promedio de forma artificial.
    """
    try:
        valor = float(texto.replace(",", ".").split()[0])
    except (ValueError, IndexError):
        return None
    return valor if 1 <= valor <= 5 else None


def parsear_fecha_extraccion(fila: dict, respaldo: datetime) -> datetime:
    """
    Usa la columna Fecha_Extraccion del CSV. Los CSV generados antes de que el
    scraper la guardara no la tienen: en ese caso se usa la fecha de modificación
    del archivo, que es cuando el scraper lo escribió.
    """
    try:
        return datetime.fromisoformat(fila.get("Fecha_Extraccion") or "")
    except ValueError:
        return respaldo


def actualizar_existente(resena: Resena, fila: dict, fecha_estimada, precision, fecha_extraccion) -> bool:
    """Actualiza los datos que cambian entre extracciones. Devuelve True si hubo cambios."""
    cambio = False

    respuesta = (fila["Respuesta_Dueno"] or "").strip()
    if respuesta and respuesta != (resena.respuesta_dueno or ""):
        resena.respuesta_dueno = respuesta
        cambio = True

    me_gusta = int(fila["Me_Gusta"]) if fila["Me_Gusta"].isdigit() else 0
    if me_gusta != resena.me_gusta:
        resena.me_gusta = me_gusta
        cambio = True

    # Una reseña vista como "hace 3 días" tiene mejor fecha que la misma vista luego como "hace 1 mes"
    if es_mas_precisa(precision, resena.precision_fecha):
        resena.fecha = fila["Fecha"]
        resena.fecha_estimada = fecha_estimada
        resena.precision_fecha = precision
        resena.fecha_extraccion = fecha_extraccion
        cambio = True

    return cambio


def cargar_datos(ruta_csv: str = ARCHIVO_CSV):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    insertadas = actualizadas = duplicadas = sin_calificacion = sin_fecha = 0

    try:
        print("⏳ Iniciando la carga de datos (ETL)...")
        respaldo_extraccion = datetime.fromtimestamp(os.path.getmtime(ruta_csv)).replace(microsecond=0)

        # Huellas de las reseñas que ya están en la BD
        hashes_en_bd = {h for (h,) in db.query(Resena.hash_unico).filter(Resena.hash_unico.isnot(None))}
        hashes_procesados: set[str] = set()
        empresas: dict[str, Empresa] = {}

        with open(ruta_csv, mode="r", encoding="utf-8") as archivo:
            lector = csv.DictReader(archivo)

            for fila in lector:
                nombre_empresa = fila["Empresa"].strip()

                # --- Empresa: buscar o crear (una sola consulta por empresa) ---
                empresa_db = empresas.get(nombre_empresa)
                if empresa_db is None:
                    empresa_db = db.query(Empresa).filter(Empresa.nombre == nombre_empresa).first()
                    if not empresa_db:
                        print(f"🏢 Registrando nueva empresa en la BD: {nombre_empresa}")
                        empresa_db = Empresa(nombre=nombre_empresa)
                        db.add(empresa_db)
                        db.flush()  # asigna el id sin confirmar la transacción
                    empresas[nombre_empresa] = empresa_db

                # --- Transformación ---
                calificacion = parsear_calificacion(fila["Estrellas"])
                if calificacion is None:
                    sin_calificacion += 1
                    continue

                fecha_extraccion = parsear_fecha_extraccion(fila, respaldo_extraccion)
                fecha_estimada, precision = estimar_fecha(fila["Fecha"], fecha_extraccion)
                if fecha_estimada is None:
                    sin_fecha += 1  # se guarda igual, pero sin fecha estimada

                hash_unico = calcular_hash(empresa_db.id, PLATAFORMA, fila["Autor"], fila["Comentario"])

                # Repetida dentro del mismo CSV
                if hash_unico in hashes_procesados:
                    duplicadas += 1
                    continue
                hashes_procesados.add(hash_unico)

                # Ya estaba en la BD: actualizar lo que cambia entre extracciones
                if hash_unico in hashes_en_bd:
                    existente = db.query(Resena).filter(Resena.hash_unico == hash_unico).first()
                    if actualizar_existente(existente, fila, fecha_estimada, precision, fecha_extraccion):
                        actualizadas += 1
                    else:
                        duplicadas += 1
                    continue

                db.add(Resena(
                    empresa_id=empresa_db.id,
                    plataforma=PLATAFORMA,
                    autor=fila["Autor"],
                    es_local_guide=fila["Local_Guide"] == "True",
                    calificacion=calificacion,
                    fecha=fila["Fecha"],
                    fecha_estimada=fecha_estimada,
                    precision_fecha=precision,
                    fecha_extraccion=fecha_extraccion,
                    comentario=fila["Comentario"],
                    me_gusta=int(fila["Me_Gusta"]) if fila["Me_Gusta"].isdigit() else 0,
                    respuesta_dueno=fila["Respuesta_Dueno"],
                    hash_unico=hash_unico,
                ))
                insertadas += 1

        # --- Carga: todo o nada ---
        db.commit()
        print(f"✅ Carga completada: {insertadas} reseñas nuevas, {actualizadas} actualizadas.")
        print(f"   ↪ {duplicadas} duplicadas sin cambios omitidas.")
        print(f"   ↪ {sin_calificacion} descartadas por no tener una calificación válida.")
        if sin_fecha:
            print(f"   ⚠️ {sin_fecha} con un formato de fecha no reconocido (guardadas sin fecha estimada).")

    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo '{ruta_csv}'. Corre el scraper primero.")
    except Exception as e:
        db.rollback()  # Si algo falla, deshacemos los cambios para no corromper la BD
        print(f"❌ Ocurrió un error inesperado durante la carga: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    cargar_datos()
