import csv
from app.core.database import SessionLocal
from app.models.review import Empresa, Resena

def cargar_datos():
   
    db = SessionLocal()
    
    try:
        print("⏳ Iniciando la carga de datos (ETL)...")
        
        with open('resenas_benchmarking.csv', mode='r', encoding='utf-8') as archivo:
            # DictReader convierte la primera fila del CSV en las llaves del diccionario
            lector = csv.DictReader(archivo)
            
            contador_resenas = 0
            
            for fila in lector:
                nombre_empresa = fila['Empresa']
                
    
                empresa_db = db.query(Empresa).filter(Empresa.nombre == nombre_empresa).first()
                
                if not empresa_db:
                    print(f"🏢 Registrando nueva empresa en la BD: {nombre_empresa}")
                    empresa_db = Empresa(nombre=nombre_empresa)
                    db.add(empresa_db)
                    db.commit()
                    db.refresh(empresa_db)
                
                # --- Transformación ---
                # A: Arreglar las estrellas (de "4,5 estrellas" a 4.5)
                estrellas_str = fila['Estrellas'].replace(',', '.').split()[0]
                try:
                    calificacion = float(estrellas_str)
                except ValueError:
                    calificacion = 0.0 # Por si dice "Sin estrellas"
                    
                # B: Convertir strings a sus tipos correctos
                es_local_guide = True if fila['Local_Guide'] == 'True' else False
                me_gusta = int(fila['Me_Gusta']) if fila['Me_Gusta'].isdigit() else 0
                
            
                nueva_resena = Resena(
                    empresa_id=empresa_db.id,
                    autor=fila['Autor'],
                    es_local_guide=es_local_guide,
                    calificacion=calificacion,
                    fecha=fila['Fecha'],
                    comentario=fila['Comentario'],
                    me_gusta=me_gusta,
                    respuesta_dueno=fila['Respuesta_Dueno']
                )
                
                db.add(nueva_resena)
                contador_resenas += 1
            
            # --- Carga ---
            db.commit()
            print(f"✅ ¡Éxito! Se cargaron {contador_resenas} reseñas en MySQL.")
            
    except FileNotFoundError:
        print("❌ Error: No se encontró el archivo 'resenas_benchmarking.csv'. Corre el scraper primero.")
    except Exception as e:
        db.rollback() # Si algo falla, deshacemos los cambios para no corromper la BD
        print(f"❌ Ocurrió un error inesperado durante la carga: {e}")
    finally:
        db.close() # Siempre cerramos la conexión

if __name__ == "__main__":
    cargar_datos()