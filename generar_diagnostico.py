"""
Genera el diagnóstico de reputación en PDF para un negocio.

    python generar_diagnostico.py --cliente "Hotel Vendimia Santa Cruz"
    python generar_diagnostico.py --cliente "Hotel Vendimia Santa Cruz" --competidores "Hotel Santa Cruz Plaza" "Casino Colchagua Santa Cruz"

Si no se indican competidores, se compara con todas las demás empresas de la base de datos.
"""
import argparse
import re

from app.core.database import SessionLocal
from app.models.empresa import Empresa
from app.services.diagnostico import generar_pdf, recolectar_datos


def buscar_empresa(db, nombre: str) -> Empresa:
    empresa = db.query(Empresa).filter(Empresa.nombre == nombre).first()
    if empresa is None:
        disponibles = ", ".join(n for (n,) in db.query(Empresa.nombre).order_by(Empresa.nombre))
        raise SystemExit(f"❌ No existe la empresa '{nombre}'. Empresas disponibles: {disponibles}")
    return empresa


def main():
    parser = argparse.ArgumentParser(description="Genera el diagnóstico de reputación en PDF.")
    parser.add_argument("--cliente", required=True, help="Nombre exacto del negocio a diagnosticar.")
    parser.add_argument("--competidores", nargs="*", help="Nombres de los competidores (por defecto, todos los demás).")
    parser.add_argument("--salida", help="Archivo PDF de salida (por defecto, diagnostico_<cliente>.pdf).")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        cliente = buscar_empresa(db, args.cliente)
        ids_comp = [buscar_empresa(db, n).id for n in args.competidores] if args.competidores else None
        print("⏳ Analizando reseñas...")
        try:
            datos = recolectar_datos(db, cliente.id, ids_comp)
        except ValueError as e:
            raise SystemExit(f"❌ {e}")
        salida = args.salida or f"diagnostico_{re.sub(r'[^\w]+', '_', cliente.nombre).strip('_')}.pdf"
        with open(salida, "wb") as f:
            f.write(generar_pdf(datos))
        print(f"✅ Diagnóstico generado: {salida}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
