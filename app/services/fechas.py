"""
Conversión de fechas relativas de Google Maps ("hace 2 meses") a fechas estimadas.

Google solo muestra cuánto tiempo pasó desde la reseña, redondeado. Por eso,
además de la fecha estimada, se guarda su precisión: una reseña de "hace 3 días"
tiene fecha casi exacta, pero una de "hace 2 años" solo es confiable a nivel de año.
"""
import calendar
import re
from datetime import date, datetime, timedelta

# Precisión de menor a mayor incertidumbre
PRECISIONES = ("dia", "semana", "mes", "anio")

_UNIDADES = {
    "minuto": "dia", "minutos": "dia",
    "hora": "dia", "horas": "dia",
    "día": "dia", "días": "dia", "dia": "dia", "dias": "dia",
    "semana": "semana", "semanas": "semana",
    "mes": "mes", "meses": "mes",
    "año": "anio", "años": "anio", "ano": "anio", "anos": "anio",
}

# "hace 2 meses", "Editado hace un año" o "4 semanas atrás"
_PATRON = re.compile(r"hace\s+(un|una|\d+)\s+(\w+)|(un|una|\d+)\s+(\w+)\s+atr[áa]s", re.IGNORECASE)


def _restar_meses(d: date, meses: int) -> date:
    total = d.year * 12 + (d.month - 1) - meses
    anio, mes = divmod(total, 12)
    mes += 1
    return date(anio, mes, min(d.day, calendar.monthrange(anio, mes)[1]))


def estimar_fecha(texto: str | None, referencia: datetime | date) -> tuple[date | None, str | None]:
    """
    Devuelve (fecha_estimada, precision) a partir de un texto como "hace 2 meses"
    o "Editado hace un año". Si el texto no se reconoce, devuelve (None, None).

    `referencia` es el momento en que se hizo la extracción, no la fecha actual.
    """
    if not texto:
        return None, None
    m = _PATRON.search(texto)
    if not m:
        return None, None

    numero, unidad = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
    cantidad = 1 if numero.lower() in ("un", "una") else int(numero)
    unidad = unidad.lower()
    precision = _UNIDADES.get(unidad)
    if precision is None:
        return None, None

    ref = referencia.date() if isinstance(referencia, datetime) else referencia
    if unidad.startswith(("minuto", "hora")):
        if isinstance(referencia, datetime):
            delta = timedelta(hours=cantidad) if unidad.startswith("hora") else timedelta(minutes=cantidad)
            return (referencia - delta).date(), precision
        return ref, precision
    if precision == "dia":
        return ref - timedelta(days=cantidad), precision
    if precision == "semana":
        return ref - timedelta(weeks=cantidad), precision
    if precision == "mes":
        return _restar_meses(ref, cantidad), precision
    return _restar_meses(ref, cantidad * 12), precision


def es_mas_precisa(nueva: str | None, actual: str | None) -> bool:
    """True si la precisión `nueva` es mejor (más fina) que la `actual`."""
    if nueva is None:
        return False
    if actual is None:
        return True
    return PRECISIONES.index(nueva) < PRECISIONES.index(actual)
