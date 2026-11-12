import csv

from app.core.database import Base, SessionLocal, engine
from app.models.empresa import Empresa
from app.models.resena import Resena, calcular_hash

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


def cargar_datos(ruta_csv: str = ARCHIVO_CSV):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    insertadas = duplicadas = sin_calificacion = 0

    try:
        print("⏳ Iniciando la carga de datos (ETL)...")

        # Huellas de las reseñas que ya están en la BD
        hashes_existentes = {h for (h,) in db.query(Resena.hash_unico).filter(Resena.hash_unico.isnot(None))}
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

                hash_unico = calcular_hash(empresa_db.id, PLATAFORMA, fila["Autor"], fila["Comentario"])
                if hash_unico in hashes_existentes:
                    duplicadas += 1
                    continue
                hashes_existentes.add(hash_unico)

                db.add(Resena(
                    empresa_id=empresa_db.id,
                    plataforma=PLATAFORMA,
                    autor=fila["Autor"],
                    es_local_guide=fila["Local_Guide"] == "True",
                    calificacion=calificacion,
                    fecha=fila["Fecha"],
                    comentario=fila["Comentario"],
                    me_gusta=int(fila["Me_Gusta"]) if fila["Me_Gusta"].isdigit() else 0,
                    respuesta_dueno=fila["Respuesta_Dueno"],
                    hash_unico=hash_unico,
                ))
                insertadas += 1

        # --- Carga: todo o nada ---
        db.commit()
        print(f"✅ Carga completada: {insertadas} reseñas nuevas.")
        print(f"   ↪ {duplicadas} duplicadas omitidas (ya estaban en la BD o repetidas en el CSV).")
        print(f"   ↪ {sin_calificacion} descartadas por no tener una calificación válida.")

    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo '{ruta_csv}'. Corre el scraper primero.")
    except Exception as e:
        db.rollback()  # Si algo falla, deshacemos los cambios para no corromper la BD
        print(f"❌ Ocurrió un error inesperado durante la carga: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    cargar_datos()
