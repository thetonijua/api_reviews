"""
Migración 002: fechas estimadas de las reseñas.

  1. Agrega las columnas fecha_estimada, precision_fecha y fecha_extraccion.
  2. Calcula la fecha estimada de las reseñas que no la tienen, a partir del
     texto original ("hace 2 meses") y de la fecha en que se hizo el scraping.

Como las reseñas antiguas no guardaron cuándo se extrajeron, hay que indicar esa
fecha (aproximada está bien). Si no se indica, se usa la fecha de hoy.

    python -m scripts.migrar_002_fechas --fecha-extraccion 2026-10-15

Se puede ejecutar más de una vez: solo completa las reseñas sin fecha estimada.
"""
import argparse
from datetime import date, datetime

from sqlalchemy import Index, inspect, text

from app.core.database import engine
from app.models.resena import Resena
from app.services.fechas import estimar_fecha

COLUMNAS = {
    "fecha_estimada": "DATE NULL",
    "precision_fecha": "VARCHAR(10) NULL",
    "fecha_extraccion": "DATETIME NULL",
}


def migrar(fecha_extraccion: datetime):
    inspector = inspect(engine)
    if "resenas" not in inspector.get_table_names():
        print("ℹ️  No hay tablas que migrar: se crearán al iniciar la API o el ETL.")
        return

    with engine.begin() as conn:
        # 1. Columnas nuevas
        existentes = {c["name"] for c in inspector.get_columns("resenas")}
        for nombre, tipo in COLUMNAS.items():
            if nombre not in existentes:
                conn.execute(text(f"ALTER TABLE resenas ADD COLUMN {nombre} {tipo}"))
                print(f"➕ Columna resenas.{nombre} agregada.")

        # 2. Completar fechas
        filas = conn.execute(text("SELECT id, fecha FROM resenas WHERE fecha_estimada IS NULL")).all()
        completadas = sin_formato = 0
        for fila in filas:
            estimada, precision = estimar_fecha(fila.fecha, fecha_extraccion)
            if estimada is None:
                sin_formato += 1
                continue
            conn.execute(
                text("UPDATE resenas SET fecha_estimada = :f, precision_fecha = :p, "
                     "fecha_extraccion = COALESCE(fecha_extraccion, :e) WHERE id = :id"),
                {"f": estimada, "p": precision, "e": fecha_extraccion, "id": fila.id},
            )
            completadas += 1
        print(f"📅 {completadas} reseñas con fecha estimada calculada.")
        if sin_formato:
            print(f"⚠️  {sin_formato} reseñas con un formato de fecha no reconocido quedaron sin fecha estimada.")

    # 3. Índice para consultar por fecha
    inspector = inspect(engine)
    if not any(i["column_names"] == ["fecha_estimada"] for i in inspector.get_indexes("resenas")):
        with engine.begin() as conn:
            Index("ix_resenas_fecha_estimada", Resena.__table__.c.fecha_estimada).create(conn)
        print("🔎 Índice en resenas.fecha_estimada creado.")

    print("✅ Migración 002 completada.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula las fechas estimadas de las reseñas existentes.")
    parser.add_argument(
        "--fecha-extraccion",
        type=date.fromisoformat,
        default=date.today(),
        help="Fecha aproximada en que se hizo el scraping de las reseñas existentes (AAAA-MM-DD). Por defecto: hoy.",
    )
    args = parser.parse_args()
    if args.fecha_extraccion == date.today():
        print("ℹ️  Usando la fecha de hoy como fecha de extracción. Si el scraping fue otro día, "
              "indícalo con --fecha-extraccion AAAA-MM-DD.")
    migrar(datetime.combine(args.fecha_extraccion, datetime.min.time()))
