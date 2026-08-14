import csv
from app.core.database import SessionLocal 
from app.models import review 

def load_csv_bd():
    db = SessionLocal()
    
    try:
        with open('resenas_casino.csv', mode='r', encoding='utf-8') as archivo:
            lector = csv.reader(archivo)
            next(lector) 
            
            registros_a_insertar = []
            
            for fila in lector:
                nueva_resena = review.Review(
                    calificacion=float(fila[0][:1]),
                    fecha_publicacion=fila[1],
                    texto=fila[2],
                    plataforma="Google maps"

                )
                registros_a_insertar.append(nueva_resena)
            
            db.add_all(registros_a_insertar)
            db.commit()
            
            print(f"✅ ¡Éxito! Se insertaron {len(registros_a_insertar)} reseñas.")
            
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    load_csv_bd()