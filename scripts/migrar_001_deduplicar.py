"""
Migración 001: deduplicar reseñas y asegurar unicidad.

Actualiza una base de datos creada con la versión anterior del proyecto:
  1. Agrega la columna resenas.hash_unico si no existe.
  2. Calcula la huella de cada reseña y elimina las duplicadas (conserva la más antigua).
  3. Elimina las reseñas sin calificación válida (guardadas como 0.0).
  4. Crea los índices únicos de resenas.hash_unico y empresas.nombre.

Se puede ejecutar más de una vez sin problema. Uso, desde la raíz del proyecto:

    python -m scripts.migrar_001_deduplicar
"""
from sqlalchemy import Index, inspect, text

from app.core.database import engine
from app.models.empresa import Empresa
from app.models.resena import Resena, calcular_hash


def indice_unico_existe(inspector, tabla: str, columna: str) -> bool:
    indices = [i for i in inspector.get_indexes(tabla) if i.get("unique")]
    restricciones = inspector.get_unique_constraints(tabla)
    return any(i["column_names"] == [columna] for i in indices + restricciones)


def migrar():
    inspector = inspect(engine)
    tablas = inspector.get_table_names()
    if "resenas" not in tablas or "empresas" not in tablas:
        print("ℹ️  No hay tablas que migrar: se crearán al iniciar la API o el ETL.")
        return

    with engine.begin() as conn:
        # 1. Columna hash_unico
        columnas = [c["name"] for c in inspector.get_columns("resenas")]
        if "hash_unico" not in columnas:
            conn.execute(text("ALTER TABLE resenas ADD COLUMN hash_unico VARCHAR(64) NULL"))
            print("➕ Columna resenas.hash_unico agregada.")

        # 2. Calcular huellas y eliminar duplicadas
        filas = conn.execute(text(
            "SELECT id, empresa_id, plataforma, autor, comentario FROM resenas ORDER BY id"
        )).all()
        vistos: set[str] = set()
        duplicadas: list[int] = []
        for fila in filas:
            h = calcular_hash(fila.empresa_id, fila.plataforma, fila.autor, fila.comentario)
            if h in vistos:
                duplicadas.append(fila.id)
                continue
            vistos.add(h)
            conn.execute(text("UPDATE resenas SET hash_unico = :h WHERE id = :id"), {"h": h, "id": fila.id})

        for i in range(0, len(duplicadas), 500):
            lote = duplicadas[i:i + 500]
            conn.execute(text(f"DELETE FROM resenas WHERE id IN ({','.join(map(str, lote))})"))
        print(f"🧹 {len(duplicadas)} reseñas duplicadas eliminadas.")

        # 3. Reseñas sin calificación válida
        resultado = conn.execute(text("DELETE FROM resenas WHERE calificacion < 1 OR calificacion > 5"))
        print(f"🧹 {resultado.rowcount} reseñas sin calificación válida eliminadas.")

    # 4. Índices únicos (se vuelve a inspeccionar porque la estructura cambió)
    inspector = inspect(engine)
    with engine.begin() as conn:
        if not indice_unico_existe(inspector, "resenas", "hash_unico"):
            Index("ix_resenas_hash_unico", Resena.__table__.c.hash_unico, unique=True).create(conn)
            print("🔒 Índice único en resenas.hash_unico creado.")

        if not indice_unico_existe(inspector, "empresas", "nombre"):
            repetidas = conn.execute(text(
                "SELECT nombre, COUNT(*) FROM empresas GROUP BY nombre HAVING COUNT(*) > 1"
            )).all()
            if repetidas:
                print("⚠️  No se pudo hacer único empresas.nombre: hay nombres repetidos.")
                for nombre, cantidad in repetidas:
                    print(f"     - {nombre} ({cantidad} veces)")
                print("     Unifícalas manualmente y vuelve a ejecutar este script.")
            else:
                if any(i["name"] == "ix_empresas_nombre" for i in inspector.get_indexes("empresas")):
                    Index("ix_empresas_nombre", Empresa.__table__.c.nombre).drop(conn)
                Index("ix_empresas_nombre", Empresa.__table__.c.nombre, unique=True).create(conn)
                print("🔒 Índice único en empresas.nombre creado.")

    print("✅ Migración 001 completada.")


if __name__ == "__main__":
    migrar()
