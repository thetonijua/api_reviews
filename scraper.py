import re
import csv
from datetime import datetime
from playwright.sync_api import sync_playwright

def extraer_resenas(empresas):
    with open('resenas_benchmarking.csv', mode='w', newline='', encoding='utf-8') as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(['Empresa', 'Autor', 'Local_Guide', 'Estrellas', 'Fecha', 'Comentario', 'Me_Gusta', 'Respuesta_Dueno', 'Fecha_Extraccion'])

        with sync_playwright() as p:
            print("🤖 Iniciando robot...")
            browser = p.chromium.launch(headless=False)
            
            for nombre_local in empresas:
                print(f"\n========================================")
                print(f"🏢 Analizando: {nombre_local}")
                print(f"========================================")
                
                context = browser.new_context(locale="es-CL", viewport={"width": 1280, "height": 720})
                page = context.new_page()
                page.goto("https://www.google.com/maps")
                
                # --- BUSCADOR ---
                selector_search = ".UGojuc.fontBodyMedium.EmSKud.lpggsf"
                barra_busqueda = page.locator(selector_search).first
                barra_busqueda.wait_for(state="visible", timeout=15000)
                
                barra_busqueda.click()
                barra_busqueda.press_sequentially(nombre_local, delay=50)
                page.keyboard.press("Enter")
                page.wait_for_selector("h1", timeout=15000)
                
                # --- SOLUCIÓN 1: BÚSQUEDA ROBUSTA DE LA PESTAÑA RESEÑAS ---
                print("🔍 Buscando la pestaña de 'Reseñas' (sin importar su posición)...")
                boton_resenas = page.locator('button[role="tab"]').filter(has_text=re.compile(r"Reseñas|Opiniones", re.IGNORECASE)).first
                boton_resenas.wait_for(state="visible", timeout=10000)
                boton_resenas.click()

                # --- FASE 1: EL SCROLL INFINITO MEJORADO ---
                print("📜 Iniciando el motor de scroll...")
                selector_tarjetas = ".jftiEf"
                page.wait_for_selector(selector_tarjetas, timeout=15000)
                
                meta_resenas = 100 
                
                while True:
                    tarjetas_actuales = page.locator(selector_tarjetas).all()
                    cantidad = len(tarjetas_actuales)
                    
                    if cantidad >= meta_resenas:
                        break
                    
                    # --- SOLUCIÓN 2: MANEJO DE POPUPS Y BOTONES EXTRA ---
                    # 2A: Detectar y cerrar popup de "Iniciar sesión"
                    try:
                        boton_ignorar = page.get_by_role("button", name=re.compile(r"Ignorar|Ahora no|No, gracias", re.IGNORECASE)).first
                        if boton_ignorar.is_visible():
                            print("🛡️ Popup detectado. Haciendo clic en 'Ignorar'...")
                            boton_ignorar.click()
                            page.wait_for_timeout(1000)
                    except:
                        pass
                    
                    # 2B: Detectar si Google puso un botón de "Más reseñas" al final del scroll
                    try:
                        boton_mas = page.get_by_role("button", name=re.compile(r"Más reseñas", re.IGNORECASE)).first
                        if boton_mas.is_visible():
                            print("⏬ Haciendo clic para cargar más reseñas...")
                            boton_mas.click()
                            page.wait_for_timeout(1500)
                    except:
                        pass
                        
                    # Hacemos el scroll
                    tarjetas_actuales[-1].hover()
                    page.mouse.wheel(0, 5000)
                    page.keyboard.press("PageDown")
                    page.wait_for_timeout(3000) 
                    
                    tarjetas_despues = page.locator(selector_tarjetas).all()
                    if len(tarjetas_despues) == cantidad:
                        page.mouse.wheel(0, 5000)
                        page.wait_for_timeout(3000)
                        if len(page.locator(selector_tarjetas).all()) == cantidad:
                            break

                # --- EXPANDIR TEXTOS LARGOS ---
                print("🔍 Abriendo botones de 'Ver más' para extraer textos completos...")
                botones_mas = page.locator('button.w8nwRe.kyuRq').all()
                for btn in botones_mas:
                    try:
                        if btn.is_visible():
                            btn.click()
                    except:
                        pass

                # --- FASE 2: LA EXTRACCIÓN ---
                print(f"📥 Guardando datos de {nombre_local}...")
                fecha_extraccion = datetime.now().isoformat(timespec="seconds")
                tarjetas_finales = page.locator(selector_tarjetas).all()
                
                for tarjeta in tarjetas_finales[:meta_resenas]:
                    autor_loc = tarjeta.locator(".d4r55")
                    autor = autor_loc.first.inner_text() if autor_loc.count() > 0 else "Anónimo"
                    
                    info_autor_loc = tarjeta.locator(".RfnDt")
                    es_local_guide = False
                    if info_autor_loc.count() > 0 and "Local Guide" in info_autor_loc.first.inner_text():
                        es_local_guide = True
                            
                    estrellas_loc = tarjeta.locator(".kvMYJc")
                    estrellas = estrellas_loc.first.get_attribute("aria-label") if estrellas_loc.count() > 0 else "Sin estrellas"
                    
                    fecha_loc = tarjeta.locator(".rsqaWe")
                    fecha = fecha_loc.first.inner_text() if fecha_loc.count() > 0 else "Sin fecha"
                    
                    textos_loc = tarjeta.locator(".wiI7pd").all()
                    
                    # --- LIMPIEZA DE COMENTARIOS Y RESPUESTAS ---
                    if len(textos_loc) > 0:
                        comentario_crudo = textos_loc[0].inner_text()

                        # Busca 3 o más saltos de línea (ignorando si hay espacios o tabs entre ellos)
                        # y los reduce a exactamente 2 saltos.
                        
                        comentario = re.sub(r'\n(?:[ \t\r]*\n){2,}', '\n\n', comentario_crudo).strip()
                    else:
                        comentario = "[Sin texto]"
                        
                    if len(textos_loc) > 1:
                        respuesta_cruda = textos_loc[1].inner_text()
                        respuesta_dueno = re.sub(r'\n(?:[ \t\r]*\n){2,}', '\n\n', respuesta_cruda).strip()
                    else:
                        respuesta_dueno = ""
                    
                    likes_loc = tarjeta.locator(".pkWtMe")
                    me_gusta = 0
                    if likes_loc.count() > 0:
                        texto_likes = likes_loc.first.inner_text()
                        if texto_likes.isdigit():
                            me_gusta = int(texto_likes)
                            
                    escritor.writerow([nombre_local, autor, es_local_guide, estrellas, fecha, comentario, me_gusta, respuesta_dueno, fecha_extraccion])
                    
                print(f"✅ {nombre_local} procesado con éxito.")
                context.close()
                
            browser.close()
            print("\n🎉 ¡Benchmarking completado! Revisa el archivo 'resenas_benchmarking.csv'")

if __name__ == "__main__":
    lista_competidores = [
        "Casino Colchagua Santa Cruz",
        "Hotel Santa Cruz Plaza",
        "Hotel Vendimia Santa Cruz"
    ]
    extraer_resenas(lista_competidores)