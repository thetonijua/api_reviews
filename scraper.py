import argparse
import csv
import re
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

COLUMNAS = ['Empresa', 'Autor', 'Local_Guide', 'Estrellas', 'Fecha', 'Comentario', 'Me_Gusta',
            'Respuesta_Dueno', 'Fecha_Extraccion']

# Tarjetas de reseña (funciona tanto en fichas de negocios como de hoteles)
SELECTOR_TARJETAS = ".jftiEf"

CARPETA_DIAGNOSTICO = Path("diagnostico_scraper")
MAX_ARCHIVOS_DIAGNOSTICO = 5

# Extrae la nota y la fecha de una tarjeta buscando por patrones de texto y
# atributos de accesibilidad, no por clases CSS. Así funciona tanto en fichas
# de negocios comunes ("4 estrellas") como en fichas de hoteles ("4/5").
JS_NOTA_Y_FECHA = r"""
(tarjeta) => {
    const limpiar = s => (s || '').replace(/\s+/g, ' ').trim();
    const reEstrellas = /^(\d(?:[.,]\d)?)\s*estrellas?\b/i;
    const reSobre5 = /^(\d(?:[.,]\d)?)\s*(?:\/|de)\s*5$/i;
    const reFecha = /^(?:editad[oa]:?\s+)?(?:hace\s+(?:un|una|\d+)\s+\S+|(?:un|una|\d+)\s+\S+\s+atr[áa]s)/i;

    let estrellas = null, sobre5 = null, fecha = null;
    for (const el of tarjeta.querySelectorAll('*')) {
        if (el.closest('.CDe7pd')) continue;  // bloque de respuesta del dueño
        const aria = limpiar(el.getAttribute('aria-label'));
        // Texto completo del elemento, aunque venga dividido en varios <span>
        // (ej: "Hace 3 semanas <span>en Google</span>"). Solo textos cortos, para no
        // tomar contenedores grandes ni comentarios.
        const textoCompleto = limpiar(el.textContent);
        const texto = textoCompleto.length <= 60 ? textoCompleto : '';

        if (!estrellas) {
            const m = aria.match(reEstrellas);
            if (m) estrellas = m[1];
        }
        if (!sobre5) {
            const m = aria.match(reSobre5) || texto.match(reSobre5);
            if (m) sobre5 = m[1];
        }
        // Texto corto: evita confundir la fecha con un comentario que empieza con "Hace..."
        if (!fecha && texto && reFecha.test(texto)) {
            fecha = texto;
        }
    }
    return { estrellas: estrellas || sobre5, fecha };
}
"""


def limpiar_saltos(texto: str) -> str:
    # Reduce 3 o más saltos de línea (aunque tengan espacios entre ellos) a exactamente 2
    return re.sub(r'\n(?:[ \t\r]*\n){2,}', '\n\n', texto).strip()


def guardar_diagnostico(tarjeta, nombre_local: str, contador: list[int]):
    """Guarda el HTML de una tarjeta en la que no se encontró la nota o la fecha."""
    if contador[0] >= MAX_ARCHIVOS_DIAGNOSTICO:
        return
    CARPETA_DIAGNOSTICO.mkdir(exist_ok=True)
    nombre = re.sub(r'[^\w]+', '_', nombre_local).strip('_')
    ruta = CARPETA_DIAGNOSTICO / f"{nombre}_{contador[0] + 1}.html"
    ruta.write_text(tarjeta.evaluate("el => el.outerHTML"), encoding="utf-8")
    contador[0] += 1


def extraer_tarjeta(tarjeta) -> dict:
    autor_loc = tarjeta.locator(".d4r55")
    autor = autor_loc.first.inner_text() if autor_loc.count() > 0 else "Anónimo"

    info_autor_loc = tarjeta.locator(".RfnDt")
    es_local_guide = info_autor_loc.count() > 0 and "Local Guide" in info_autor_loc.first.inner_text()

    nota_fecha = tarjeta.evaluate(JS_NOTA_Y_FECHA)

    # --- Comentario y respuesta del dueño ---
    # La respuesta del dueño está en su propio bloque (.CDe7pd); el comentario es el texto
    # que queda fuera de ese bloque. Así una reseña sin comentario no toma la respuesta como comentario.
    textos = tarjeta.evaluate("""(t) => {
        const respuesta = t.querySelector('.CDe7pd .wiI7pd');
        const comentario = [...t.querySelectorAll('.wiI7pd')].find(el => !el.closest('.CDe7pd'));
        return {
            comentario: comentario ? comentario.innerText : null,
            respuesta: respuesta ? respuesta.innerText : null,
        };
    }""")
    comentario = limpiar_saltos(textos["comentario"]) if textos["comentario"] else "[Sin texto]"
    respuesta_dueno = limpiar_saltos(textos["respuesta"]) if textos["respuesta"] else ""

    likes_loc = tarjeta.locator(".pkWtMe")
    me_gusta = 0
    if likes_loc.count() > 0:
        texto_likes = likes_loc.first.inner_text()
        if texto_likes.isdigit():
            me_gusta = int(texto_likes)

    return {
        "Autor": autor,
        "Local_Guide": es_local_guide,
        # Se guarda como "4 estrellas" para mantener el mismo formato en todo el CSV
        "Estrellas": f"{nota_fecha['estrellas']} estrellas" if nota_fecha["estrellas"] else "Sin estrellas",
        "Fecha": nota_fecha["fecha"] or "Sin fecha",
        "Comentario": comentario,
        "Me_Gusta": me_gusta,
        "Respuesta_Dueno": respuesta_dueno,
    }


def expandir_textos(page):
    """Abre los botones "Ver más" para obtener el texto completo de las reseñas."""
    # Solo los botones que aún no se abrieron (aria-expanded="false")
    botones_ver_mas = page.locator(
        'button.w8nwRe.kyuRq[aria-expanded="false"], button[aria-label="Ver más"][aria-expanded="false"]').all()
    for btn in botones_ver_mas:
        try:
            # Clic normal; si la ventana de "iniciar sesión" lo tapa, se activa el botón
            # directamente. Solo expande el texto de una reseña que ya está en pantalla.
            try:
                btn.click(timeout=2000)
            except Exception:
                btn.evaluate("b => b.click()")
            page.wait_for_timeout(150)
        except Exception:
            pass


def extraer_resenas(empresas: list[str], meta_resenas: int = 100, salida: str = "resenas_benchmarking.csv",
                    headless: bool = False, diagnostico: bool = False):
    with open(salida, mode='w', newline='', encoding='utf-8') as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        escritor.writeheader()

        with sync_playwright() as p:
            print("🤖 Iniciando robot...")
            browser = p.chromium.launch(headless=headless)

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

                # --- PESTAÑA RESEÑAS (sin importar su posición) ---
                print("🔍 Buscando la pestaña de 'Reseñas'...")
                boton_resenas = page.locator('button[role="tab"]').filter(
                    has_text=re.compile(r"Reseñas|Opiniones", re.IGNORECASE)).first
                boton_resenas.wait_for(state="visible", timeout=10000)
                boton_resenas.click()

                # --- FASE 1: SCROLL INFINITO ---
                print("📜 Iniciando el motor de scroll...")
                page.wait_for_selector(SELECTOR_TARJETAS, timeout=15000)

                while True:
                    tarjetas_actuales = page.locator(SELECTOR_TARJETAS).all()
                    cantidad = len(tarjetas_actuales)

                    if cantidad >= meta_resenas:
                        break

                    # Cerrar popup de "Iniciar sesión"
                    try:
                        boton_ignorar = page.get_by_role(
                            "button", name=re.compile(r"Ignorar|Ahora no|No, gracias", re.IGNORECASE)).first
                        if boton_ignorar.is_visible():
                            print("🛡️ Popup detectado. Haciendo clic en 'Ignorar'...")
                            boton_ignorar.click()
                            page.wait_for_timeout(1000)
                    except Exception:
                        pass

                    # Botón de "Más reseñas" al final del scroll
                    try:
                        boton_mas = page.get_by_role("button", name=re.compile(r"Más reseñas", re.IGNORECASE)).first
                        if boton_mas.is_visible():
                            print("⏬ Haciendo clic para cargar más reseñas...")
                            boton_mas.click()
                            page.wait_for_timeout(1500)
                    except Exception:
                        pass

                    tarjetas_actuales[-1].hover()
                    page.mouse.wheel(0, 5000)
                    page.keyboard.press("PageDown")
                    page.wait_for_timeout(3000)

                    if len(page.locator(SELECTOR_TARJETAS).all()) == cantidad:
                        page.mouse.wheel(0, 5000)
                        page.wait_for_timeout(3000)
                        if len(page.locator(SELECTOR_TARJETAS).all()) == cantidad:
                            break

                # --- EXPANDIR TEXTOS LARGOS ---
                print("🔍 Abriendo botones de 'Ver más' para extraer textos completos...")
                expandir_textos(page)

                # --- FASE 2: EXTRACCIÓN ---
                print(f"📥 Guardando datos de {nombre_local}...")
                fecha_extraccion = datetime.now().isoformat(timespec="seconds")
                diagnosticos = [0]
                sin_nota = sin_fecha = 0
                tarjetas_finales = page.locator(SELECTOR_TARJETAS).all()[:meta_resenas]

                for tarjeta in tarjetas_finales:
                    fila = extraer_tarjeta(tarjeta)
                    falta_nota = fila["Estrellas"] == "Sin estrellas"
                    falta_fecha = fila["Fecha"] == "Sin fecha"
                    sin_nota += falta_nota
                    sin_fecha += falta_fecha
                    if diagnostico or falta_nota or falta_fecha:
                        guardar_diagnostico(tarjeta, nombre_local, diagnosticos)
                    escritor.writerow({"Empresa": nombre_local, **fila, "Fecha_Extraccion": fecha_extraccion})

                print(f"✅ {nombre_local}: {len(tarjetas_finales)} reseñas guardadas.")
                if sin_nota or sin_fecha:
                    print(f"   ⚠️ {sin_nota} sin estrellas y {sin_fecha} sin fecha. "
                          f"Se guardó el HTML de ejemplo en la carpeta '{CARPETA_DIAGNOSTICO}/'.")
                context.close()

            browser.close()
            print(f"\n🎉 ¡Extracción completada! Revisa el archivo '{salida}'")


if __name__ == "__main__":
    lista_competidores = [
        "Casino Colchagua Santa Cruz",
        "Hotel Santa Cruz Plaza",
        "Hotel Vendimia Santa Cruz",
    ]

    parser = argparse.ArgumentParser(description="Extrae reseñas de Google Maps a un CSV.")
    parser.add_argument("empresas", nargs="*", default=lista_competidores,
                        help="Nombres de los negocios a buscar (por defecto, la lista del script).")
    parser.add_argument("--max", type=int, default=100, help="Cantidad máxima de reseñas por negocio.")
    parser.add_argument("--salida", default="resenas_benchmarking.csv", help="Archivo CSV de salida.")
    parser.add_argument("--headless", action="store_true", help="Ejecutar sin abrir la ventana del navegador.")
    parser.add_argument("--diagnostico", action="store_true",
                        help=f"Guardar el HTML de las primeras {MAX_ARCHIVOS_DIAGNOSTICO} tarjetas en '{CARPETA_DIAGNOSTICO}/', aunque no tengan errores.")
    args = parser.parse_args()

    extraer_resenas(args.empresas, meta_resenas=args.max, salida=args.salida, headless=args.headless,
                    diagnostico=args.diagnostico)
