"""
Diagnóstico de reputación: compara a un negocio con su competencia a partir de sus
reseñas y genera un informe en PDF de 1 a 2 páginas, pensado para entregárselo al dueño.

No incluye nombres de autores: el informe trabaja con datos agregados y citas anónimas.
"""
from collections import defaultdict
from datetime import date, datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.resena import Resena
from app.services.nlp import temas_frecuentes

PRECISIONES_MENSUALES = ("dia", "semana", "mes")
NOTA_NEGATIVA = 2  # 1 y 2 estrellas
NOTA_POSITIVA = 4  # 4 y 5 estrellas
MUESTRA_MINIMA = 20  # bajo esta cantidad de reseñas, las comparaciones son poco confiables


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------

def num(valor: float, decimales: int = 1) -> str:
    """Número con coma decimal, como se escribe en Chile: 3,8"""
    return f"{valor:.{decimales}f}".replace(".", ",")


def resumir_empresa(empresa: Empresa, resenas: list[Resena]) -> dict:
    total = len(resenas)
    notas = [r.calificacion for r in resenas]
    respondidas = sum(1 for r in resenas if (r.respuesta_dueno or "").strip())
    negativas = sum(1 for n in notas if n <= NOTA_NEGATIVA)
    return {
        "id": empresa.id,
        "nombre": empresa.nombre,
        "total": total,
        "promedio": round(sum(notas) / total, 2) if total else 0.0,
        "tasa_respuesta": round(respondidas / total * 100, 1) if total else 0.0,
        "pct_negativas": round(negativas / total * 100, 1) if total else 0.0,
    }


def tendencia_mensual(resenas: list[Resena], meses: int = 6) -> list[dict]:
    """Reseñas y promedio de los últimos `meses` meses con datos (solo fechas con precisión mensual o mejor)."""
    por_mes: dict[str, list[float]] = defaultdict(list)
    for r in resenas:
        if r.fecha_estimada and r.precision_fecha in PRECISIONES_MENSUALES:
            por_mes[r.fecha_estimada.strftime("%Y-%m")].append(r.calificacion)
    ultimos = sorted(por_mes.items())[-meses:]
    return [{"periodo": p, "total": len(n), "promedio": round(sum(n) / len(n), 2)} for p, n in ultimos]


def elegir_cita(resenas: list[Resena], positiva: bool) -> str | None:
    """La reseña más reciente con texto, positiva o negativa, recortada a un largo razonable."""
    candidatas = [
        r for r in resenas
        if r.comentario and r.comentario != "[Sin texto]" and len(r.comentario) >= 40
        and (r.calificacion >= NOTA_POSITIVA if positiva else r.calificacion <= NOTA_NEGATIVA)
    ]
    if not candidatas:
        return None
    candidatas.sort(key=lambda r: r.fecha_estimada or date.min, reverse=True)
    texto = " ".join(candidatas[0].comentario.split())
    return texto if len(texto) <= 260 else texto[:257].rsplit(" ", 1)[0] + "..."


def generar_recomendaciones(cliente: dict, competidores: list[dict], temas_pos, temas_neg,
                            total_pos: int, total_neg: int) -> list[str]:
    recomendaciones = []
    con_datos = [c for c in competidores if c["total"]]

    tasa_comp = sum(c["tasa_respuesta"] for c in con_datos) / len(con_datos) if con_datos else 0
    if cliente["tasa_respuesta"] < max(50, tasa_comp):
        if con_datos and cliente["tasa_respuesta"] > tasa_comp:
            contexto = f"Ya responde más que su competencia ({num(tasa_comp, 0)}%), pero aún queda un {num(100 - cliente['tasa_respuesta'], 0)}% sin respuesta. "
        elif con_datos:
            contexto = f"Hoy responde el {num(cliente['tasa_respuesta'], 0)}% y su competencia el {num(tasa_comp, 0)}%. "
        else:
            contexto = f"Hoy responde el {num(cliente['tasa_respuesta'], 0)}%. "
        recomendaciones.append(
            f"<b>Responda más reseñas.</b> {contexto}"
            "Responder, sobre todo las negativas, muestra a futuros clientes que el negocio escucha y corrige."
        )

    if temas_neg:
        tema, veces = temas_neg[0]
        recomendaciones.append(
            f"<b>Revise «{tema}».</b> Es el tema más mencionado en sus reseñas negativas "
            f"(en {veces} de {total_neg}). Es la mejora con más impacto directo en su nota."
        )

    if temas_pos:
        tema, veces = temas_pos[0]
        recomendaciones.append(
            f"<b>Destaque «{tema}» en su comunicación.</b> Es lo que más elogian sus clientes "
            f"(en {veces} de {total_pos} reseñas positivas): úselo en redes sociales, su sitio web y su ficha de Google."
        )

    if con_datos:
        mejor = max(con_datos, key=lambda c: c["promedio"])
        if cliente["promedio"] < mejor["promedio"]:
            recomendaciones.append(
                f"<b>Cierre la brecha con {escape(mejor['nombre'])}.</b> Tiene {num(mejor['promedio'])} estrellas "
                f"frente a sus {num(cliente['promedio'])}. Revise qué elogian de ese negocio que usted podría ofrecer."
            )
        else:
            recomendaciones.append(
                f"<b>Lidera en estrellas frente a su competencia</b> ({num(cliente['promedio'])}). "
                "Pida a sus clientes satisfechos que dejen una reseña para mantener esa ventaja."
            )

    return recomendaciones[:4]


def recolectar_datos(db: Session, cliente_id: int, competidores_ids: list[int] | None = None) -> dict:
    """
    Reúne todo lo necesario para el diagnóstico. Si no se indican competidores,
    se usan todas las demás empresas de la base de datos.
    """
    cliente = db.get(Empresa, cliente_id)
    if cliente is None:
        raise ValueError(f"No existe la empresa con id {cliente_id}")

    consulta_comp = db.query(Empresa).filter(Empresa.id != cliente_id)
    if competidores_ids:
        consulta_comp = consulta_comp.filter(Empresa.id.in_(competidores_ids))
    competidores = consulta_comp.order_by(Empresa.nombre).all()

    resenas_cliente = db.query(Resena).filter(Resena.empresa_id == cliente_id).all()
    if not resenas_cliente:
        raise ValueError(f"'{cliente.nombre}' no tiene reseñas cargadas")

    positivas = [r.comentario for r in resenas_cliente if r.calificacion >= NOTA_POSITIVA]
    negativas = [r.comentario for r in resenas_cliente if r.calificacion <= NOTA_NEGATIVA]
    # Solo sustantivos ("desayuno", "habitación" dicen más que "bueno" o "malo"), sin las palabras
    # del nombre del propio negocio ("hotel", "casino", "vendimia"), que aparecen en casi todas las reseñas
    excluir = {p for p in cliente.nombre.lower().split() if len(p) > 2}
    temas_pos = temas_frecuentes(positivas, cantidad=5, tipos=("NOUN",), excluir=excluir)
    temas_neg = temas_frecuentes(negativas, cantidad=5, tipos=("NOUN",), excluir=excluir)

    resumen_cliente = resumir_empresa(cliente, resenas_cliente)
    resumenes_comp = [
        resumir_empresa(c, db.query(Resena).filter(Resena.empresa_id == c.id).all()) for c in competidores
    ]
    plataformas = sorted({r.plataforma for r in resenas_cliente if r.plataforma})
    fechas_extraccion = [r.fecha_extraccion for r in resenas_cliente if r.fecha_extraccion]

    return {
        "cliente": resumen_cliente,
        "competidores": resumenes_comp,
        "tendencia": tendencia_mensual(resenas_cliente),
        "temas_positivos": temas_pos,
        "temas_negativos": temas_neg,
        "total_positivas": len(positivas),
        "total_negativas": len(negativas),
        "cita_positiva": elegir_cita(resenas_cliente, positiva=True),
        "cita_negativa": elegir_cita(resenas_cliente, positiva=False),
        "recomendaciones": generar_recomendaciones(
            resumen_cliente, resumenes_comp, temas_pos, temas_neg, len(positivas), len(negativas)),
        "plataformas": plataformas,
        "ultima_extraccion": max(fechas_extraccion) if fechas_extraccion else None,
        "fecha_informe": date.today(),
    }


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

VERDE = colors.HexColor("#2F5D50")
VERDE_CLARO = colors.HexColor("#E6EFEA")
VINO = colors.HexColor("#7A2E3A")
GRIS = colors.HexColor("#5A5A5A")
LINEA = colors.HexColor("#C9D5CF")

_base = ParagraphStyle("base", fontName="Helvetica", fontSize=9.5, leading=13, textColor=colors.HexColor("#222222"))
_pequeno = ParagraphStyle("pequeno", parent=_base, fontSize=7.8, leading=10, textColor=GRIS)
_celda = ParagraphStyle("celda", parent=_base, fontSize=8.8, leading=11)
_celda_titulo = ParagraphStyle("celda_titulo", parent=_celda, fontName="Helvetica-Bold", textColor=colors.white)
_h2 = ParagraphStyle("h2", parent=_base, fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=VERDE,
                     spaceBefore=8, spaceAfter=4)
_kpi_valor = ParagraphStyle("kpi_valor", parent=_base, fontName="Helvetica-Bold", fontSize=17, leading=20,
                            textColor=VERDE, alignment=1)
_kpi_texto = ParagraphStyle("kpi_texto", parent=_base, fontSize=7.8, leading=10, textColor=GRIS, alignment=1)
_cita = ParagraphStyle("cita", parent=_base, fontName="Helvetica-Oblique", fontSize=8.8, leading=12, leftIndent=8)

ANCHO = A4[0] - 3.4 * cm


def _texto(t: str) -> str:
    """Escapa para Paragraph y quita caracteres que las fuentes estándar de PDF no tienen (ej: emojis)."""
    return escape(t).encode("cp1252", "ignore").decode("cp1252")


def _p(t: str, estilo=_base, escapar: bool = False) -> Paragraph:
    return Paragraph(_texto(t) if escapar else t.encode("cp1252", "ignore").decode("cp1252"), estilo)


def _kpis(datos: dict) -> Table:
    c = datos["cliente"]
    comp = [x for x in datos["competidores"] if x["total"]]

    def promedio(campo):
        return sum(x[campo] for x in comp) / len(comp) if comp else None

    def celda(valor, etiqueta, ref):
        sub = f"{etiqueta}<br/>Competencia: {ref}" if ref is not None else etiqueta
        return [_p(valor, _kpi_valor), _p(sub, _kpi_texto)]

    p_prom, p_resp, p_neg = promedio("promedio"), promedio("tasa_respuesta"), promedio("pct_negativas")
    filas = [[
        celda(num(c["promedio"]), "Estrellas promedio", num(p_prom) if p_prom is not None else None),
        celda(str(c["total"]), "Reseñas analizadas", None),
        celda(f"{c['tasa_respuesta']:.0f}%", "Reseñas respondidas", f"{p_resp:.0f}%" if p_resp is not None else None),
        celda(f"{c['pct_negativas']:.0f}%", "Reseñas negativas (1-2)", f"{p_neg:.0f}%" if p_neg is not None else None),
    ]]
    t = Table(filas, colWidths=[ANCHO / 4] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), VERDE_CLARO),
        ("BOX", (0, 0), (-1, -1), 0.5, LINEA),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _tabla_comparativa(datos: dict) -> Table:
    filas = [[_p(t, _celda_titulo) for t in ("Negocio", "Estrellas", "Reseñas", "Respondidas", "Negativas")]]
    todas = [datos["cliente"]] + datos["competidores"]
    for e in todas:
        nombre = _texto(e["nombre"]) + (" (usted)" if e is datos["cliente"] else "")
        filas.append([
            _p(nombre, _celda),
            _p(num(e["promedio"], 2) if e["total"] else "-", _celda),
            _p(str(e["total"]), _celda),
            _p(f"{e['tasa_respuesta']:.0f}%" if e["total"] else "-", _celda),
            _p(f"{e['pct_negativas']:.0f}%" if e["total"] else "-", _celda),
        ])
    t = Table(filas, colWidths=[ANCHO * 0.40] + [ANCHO * 0.15] * 4, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VERDE),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F6E9EB")),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINEA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _grafico_estrellas(datos: dict) -> Drawing:
    empresas = [e for e in [datos["cliente"]] + datos["competidores"] if e["total"]][::-1]
    alto = 18 * len(empresas) + 26
    d = Drawing(ANCHO, alto)
    g = HorizontalBarChart()
    g.x, g.y = 150, 15
    g.width, g.height = ANCHO - 190, alto - 25
    g.data = [[e["promedio"] for e in empresas]]
    g.valueAxis.valueMin, g.valueAxis.valueMax, g.valueAxis.valueStep = 0, 5, 1
    g.valueAxis.labels.fontName = "Helvetica"
    g.valueAxis.labels.fontSize = 7
    g.categoryAxis.categoryNames = [
        (e["nombre"][:28] + "...") if len(e["nombre"]) > 30 else e["nombre"] for e in empresas
    ]
    g.categoryAxis.labels.fontName = "Helvetica"
    g.categoryAxis.labels.fontSize = 7.5
    g.categoryAxis.labels.boxAnchor = "e"
    g.barWidth = 10
    g.bars[0].fillColor = colors.HexColor("#9DB8AD")
    g.bars[0].strokeColor = None
    cliente_idx = len(empresas) - 1  # el cliente queda arriba
    g.bars[(0, cliente_idx)].fillColor = VINO
    d.add(g)
    for i, e in enumerate(empresas):
        ancho_barra = g.width * e["promedio"] / 5
        y = g.y + g.height * (i + 0.5) / len(empresas) - 3
        d.add(String(g.x + ancho_barra + 4, y, num(e["promedio"], 2), fontName="Helvetica", fontSize=7.5,
                     fillColor=GRIS))
    return d


def _temas(datos: dict) -> Table:
    def lista(temas, total, vacio):
        if not temas:
            return _p(vacio, _pequeno)
        lineas = "<br/>".join(f"• {_texto(t.capitalize())} <font color='#5A5A5A'>({n})</font>" for t, n in temas)
        return _p(lineas, _celda)

    filas = [
        [_p(f"Lo que más elogian ({datos['total_positivas']} reseñas de 4-5 estrellas)", _celda_titulo),
         _p(f"Lo que más critican ({datos['total_negativas']} reseñas de 1-2 estrellas)", _celda_titulo)],
        [lista(datos["temas_positivos"], datos["total_positivas"], "Sin reseñas positivas con texto."),
         lista(datos["temas_negativos"], datos["total_negativas"], "Sin reseñas negativas con texto: buena señal.")],
    ]
    t = Table(filas, colWidths=[ANCHO / 2] * 2)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), VERDE), ("BACKGROUND", (1, 0), (1, 0), VINO),
        ("BOX", (0, 0), (-1, -1), 0.4, LINEA), ("LINEAFTER", (0, 0), (0, -1), 0.4, LINEA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _pie(c, doc, datos):
    c.saveState()
    c.setFont("Helvetica", 7)
    c.setFillColor(GRIS)
    c.drawString(1.7 * cm, 1.0 * cm, f"CreceBit · Diagnóstico de reputación · {datos['fecha_informe']:%d-%m-%Y}")
    c.drawRightString(A4[0] - 1.7 * cm, 1.0 * cm, f"Página {doc.page}")
    c.restoreState()


def _encabezado(c, doc, datos):
    c.saveState()
    c.setFillColor(VERDE)
    c.rect(0, A4[1] - 3.3 * cm, A4[0], 3.3 * cm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 9)
    c.drawString(1.7 * cm, A4[1] - 1.2 * cm, "DIAGNÓSTICO DE REPUTACIÓN ONLINE")
    c.setFont("Helvetica-Bold", 18)
    nombre = datos["cliente"]["nombre"].encode("cp1252", "ignore").decode("cp1252")
    c.drawString(1.7 * cm, A4[1] - 2.1 * cm, nombre[:55])
    c.setFont("Helvetica", 9)
    n = len(datos["competidores"])
    c.drawString(1.7 * cm, A4[1] - 2.75 * cm,
                 f"Comparado con {n} competidor{'es' if n != 1 else ''} · {datos['fecha_informe']:%d-%m-%Y}")
    c.restoreState()
    _pie(c, doc, datos)


def generar_pdf(datos: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=1.7 * cm, rightMargin=1.7 * cm, topMargin=1.5 * cm, bottomMargin=1.6 * cm,
        title=f"Diagnóstico de reputación - {datos['cliente']['nombre']}", author="CreceBit",
    )
    historia = [Spacer(1, 2.2 * cm), _kpis(datos)]

    historia += [_p("Cómo está frente a su competencia", _h2), _tabla_comparativa(datos)]
    if sum(1 for e in [datos["cliente"]] + datos["competidores"] if e["total"]) > 1:
        historia += [Spacer(1, 6), _grafico_estrellas(datos)]

    historia += [_p("Qué dicen sus clientes", _h2), _temas(datos)]
    citas = []
    if datos["cita_positiva"]:
        citas.append(_p(f"<font color='#2F5D50'><b>Positiva:</b></font> «{_texto(datos['cita_positiva'])}»", _cita))
    if datos["cita_negativa"]:
        citas.append(_p(f"<font color='#7A2E3A'><b>Negativa:</b></font> «{_texto(datos['cita_negativa'])}»", _cita))
    if citas:
        historia += [Spacer(1, 6), _p("Reseñas recientes (sin nombres de autores):", _pequeno)]
        for cita in citas:
            historia += [Spacer(1, 3), cita]

    if datos["tendencia"]:
        meses = datos["tendencia"]
        fila_mes = [_p("Mes", _celda_titulo)] + [
            _p(datetime.strptime(m["periodo"], "%Y-%m").strftime("%m-%Y"), _celda_titulo) for m in meses]
        fila_n = [_p("Reseñas", _celda)] + [_p(str(m["total"]), _celda) for m in meses]
        fila_prom = [_p("Estrellas", _celda)] + [_p(num(m["promedio"]), _celda) for m in meses]
        ancho_mes = (ANCHO - 2.2 * cm) / max(len(meses), 1)
        t = Table([fila_mes, fila_n, fila_prom], colWidths=[2.2 * cm] + [ancho_mes] * len(meses))
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), VERDE), ("GRID", (0, 0), (-1, -1), 0.4, LINEA),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        historia += [_p("Evolución reciente", _h2), t]

    if datos["recomendaciones"]:
        historia.append(_p("Recomendaciones", _h2))
        for i, r in enumerate(datos["recomendaciones"], 1):
            historia += [_p(f"{i}. {r}", _base), Spacer(1, 3)]

    pequenas = [e["nombre"] for e in [datos["cliente"]] + datos["competidores"] if 0 < e["total"] < MUESTRA_MINIMA]
    aviso = (
        f"<font color='#7A2E3A'><b>Atención, muestra pequeña:</b></font> {_texto(', '.join(pequenas))} "
        f"tiene{'n' if len(pequenas) > 1 else ''} menos de {MUESTRA_MINIMA} reseñas analizadas; tome esas cifras "
        "como una referencia inicial, no como una conclusión. "
    ) if pequenas else ""

    extraccion = f" extraídas el {datos['ultima_extraccion']:%d-%m-%Y}" if datos["ultima_extraccion"] else ""
    plats = datos["plataformas"]
    plataformas = (", ".join(plats[:-1]) + " y " + plats[-1]) if len(plats) > 1 else (plats[0] if plats else "plataformas públicas")
    historia += [Spacer(1, 6), _p(
        f"{aviso}<b>Nota metodológica:</b> análisis basado en las reseñas públicas más recientes de {_texto(plataformas)}"
        f"{extraccion}. Las cifras corresponden a las reseñas analizadas y pueden diferir del total que muestra "
        "cada plataforma. Las fechas de Google son aproximadas (\"hace 2 meses\"). Los temas se detectan "
        "automáticamente y se cuentan una vez por reseña.", _pequeno)]

    doc.build(historia, onFirstPage=lambda c, d: _encabezado(c, d, datos), onLaterPages=lambda c, d: _pie(c, d, datos))
    return buffer.getvalue()
