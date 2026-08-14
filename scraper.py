import re
import csv
from playwright.sync_api import sync_playwright

def buscar_y_abrir_opiniones(nombre_local):
    with sync_playwright() as p:
        print("🤖 Iniciando robot...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            locale="es-CL",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        print("🗺️ Yendo a Google Maps...")
        page.goto("https://www.google.com/maps")
        
        # --- TU SELECTOR MAESTRO ---
        selector_search = ".UGojuc.fontBodyMedium.EmSKud.lpggsf"
        
        print("🔍 Buscando la barra...")
        barra_busqueda = page.locator(selector_search).first
        barra_busqueda.wait_for(state="visible", timeout=15000)
        
        print("🖱️ Haciendo clic y escribiendo...")
        barra_busqueda.click()
        barra_busqueda.press_sequentially(nombre_local, delay=100)
        page.keyboard.press("Enter")
        
        print("⏳ Esperando que cargue la ficha del local...")
        page.wait_for_selector("h1", timeout=15000)
        

        print("🔍 Buscando la pestaña de 'Reseñas' u 'Opiniones'...")
        # El símbolo | significa OR. Busca una u otra ignorando mayúsculas.
     
        boton_resenas = page.locator('button[data-tab-index="1"]')
        boton_resenas.wait_for(state="visible", timeout=10000)
        
        print(f"🖱️ ¡Botón encontrado! Haciendo clic...")
        boton_resenas.click()


    # --- FASE 1: EL SCROLL INFINITO ---
        print("📜 Iniciando el motor de scroll...")
        selector_tarjetas = ".jftiEf"
        page.wait_for_selector(selector_tarjetas, timeout=15000)
        
        meta_resenas = 1000  # Cuántas reseñas queremos extraer 
        
        while True:
            tarjetas_actuales = page.locator(selector_tarjetas).all()
            cantidad = len(tarjetas_actuales)
            print(f"🔄 Llevamos {cantidad} reseñas cargadas...")
            
            if cantidad >= meta_resenas:
                print("🎯 ¡Meta alcanzada!")
                break
                
            # --- EL NUEVO TRUCO DE SCROLL: MODO HUMANO ---
            # 1. Ponemos el cursor invisible exactamente sobre la última reseña
            tarjetas_actuales[-1].hover()
            
            # 2. Giramos la rueda del mouse fuertemente hacia abajo (5000 pixeles)
            page.mouse.wheel(0, 5000)
            
            # 3. Por si el mouse falla, simulamos presionar la tecla "Avance de Página"
            page.keyboard.press("PageDown")
            
            # Le damos 3 segundos a Google para que la animación de carga termine
            page.wait_for_timeout(5000) 
            
            tarjetas_despues = page.locator(selector_tarjetas).all()
            if len(tarjetas_despues) == cantidad:
                # A veces Google se pone lento, le damos un intento extra de scroll
                print("⚠️ Parece que se atascó. Intentando un scroll extra...")
                page.mouse.wheel(0, 5000)
                page.wait_for_timeout(3000)
                
                # Si de verdad ya no cargó más, rompemos el bucle
                if len(page.locator(selector_tarjetas).all()) == cantidad:
                    print("🛑 Llegamos al final real de las reseñas.")
                    break

        # --- FASE 2: LA EXTRACCIÓN (esto ya funciona) ---
        print("\n🔍 Extrayendo los datos de las tarjetas...")
        tarjetas_finales = page.locator(selector_tarjetas).all()
        
        # --- FASE 1: LA EXTRACCIÓN Y GUARDADO ---
        print("\n🔍 Extrayendo y guardando en CSV...")
        tarjetas_finales = page.locator(selector_tarjetas).all()
        
        # 1. Abrimos un archivo CSV en modo escritura ('w')
        with open('resenas_casino.csv', mode='w', newline='', encoding='utf-8') as archivo:
            escritor = csv.writer(archivo)
            
            # 2. Escribimos los encabezados de las columnas
            escritor.writerow(['Estrellas', 'Fecha', 'Comentario'])
            
            for i, tarjeta in enumerate(tarjetas_finales[:meta_resenas]):
                estrellas_loc = tarjeta.locator(".kvMYJc")
                estrellas = estrellas_loc.first.get_attribute("aria-label") if estrellas_loc.count() > 0 else "Sin estrellas"
                
                fecha_loc = tarjeta.locator(".rsqaWe")
                fecha = fecha_loc.first.inner_text() if fecha_loc.count() > 0 else "Sin fecha"
                
                texto_loc = tarjeta.locator(".wiI7pd")
                comentario = texto_loc.first.inner_text() if texto_loc.count() > 0 else "[Sin texto]"
                
                # 3. Guardamos la fila directamente en el archivo
                escritor.writerow([estrellas, fecha, comentario])
                
        print("\n✅ ¡Proceso completado! Revisa el archivo 'resenas_casino.csv'")
        #page.pause()
        browser.close()


if __name__ == "__main__":
    buscar_y_abrir_opiniones("Casino Colchagua Santa Cruz")