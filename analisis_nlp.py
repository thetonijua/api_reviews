import spacy
from collections import Counter
from app.core.database import SessionLocal
from app.models.empresa import Empresa
from app.models.resena import Resena

# Cargamos el modelo de lenguaje en español
print("🧠 Cargando modelo de Inteligencia Artificial (español)...")
nlp = spacy.load("es_core_news_sm")

def analizar_palabras_clave(nombre_empresa):
    db = SessionLocal()
    
    try:
        # 1. Buscamos la empresa
        empresa = db.query(Empresa).filter(Empresa.nombre == nombre_empresa).first()
        if not empresa:
            print(f"❌ No se encontró la empresa: {nombre_empresa}")
            return
            
        # 2. Obtenemos todas sus reseñas que tengan texto
        resenas = db.query(Resena).filter(
            Resena.empresa_id == empresa.id,
            Resena.comentario != "[Sin texto]",
            Resena.comentario != None
        ).all()
        
        print(f"\n📊 Analizando {len(resenas)} comentarios de '{nombre_empresa}'...")
        
        textos_completos = " ".join([r.comentario for r in resenas])
        
        # 3. Procesamos el texto con spaCy
        doc = nlp(textos_completos.lower())
        
        # 4. Filtramos: Solo queremos Sustantivos (NOUN) y Adjetivos (ADJ)
        # Y descartamos las "Stop words" (palabras vacías) y signos de puntuación
        palabras_clave = [
            token.lemma_ for token in doc 
            if token.pos_ in ["NOUN", "ADJ"] 
            and not token.is_stop 
            and token.is_alpha
            and len(token.text) > 2 # Ignorar palabras de 1 o 2 letras
        ]
        
        # 5. Contamos las palabras más comunes
        frecuencia = Counter(palabras_clave)
        top_10 = frecuencia.most_common(10)
        
        print("\n🏆 TOP 10 CONCEPTOS MÁS MENCIONADOS:")
        print("-" * 40)
        for palabra, cantidad in top_10:
            print(f"🔸 {palabra.capitalize()}: {cantidad} menciones")
            
    finally:
        db.close()

if __name__ == "__main__":
    # Prueba con una de las empresas que ya scrapeaste
    analizar_palabras_clave("Hotel Santa Cruz Plaza")