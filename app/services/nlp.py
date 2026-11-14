"""Carga del modelo de spaCy y extracción de temas frecuentes en reseñas."""
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache

import spacy


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def obtener_modelo():
    # Se carga una sola vez y solo cuando se necesita (tarda unos segundos)
    return spacy.load("es_core_news_sm")


# Palabras muy frecuentes en reseñas que no dicen nada concreto al dueño del negocio
PALABRAS_GENERICAS = {
    "lugar", "sitio", "cosa", "vez", "día", "año", "mes", "hora", "momento", "gente", "persona",
    "experiencia", "parte", "tipo", "verdad", "nada", "algo", "general", "estrella", "punto",
}


def temas_frecuentes(textos: list[str], cantidad: int = 10, tipos: tuple[str, ...] = ("NOUN", "ADJ"),
                     excluir: set[str] | None = None) -> list[tuple[str, int]]:
    """
    Palabras más mencionadas (por defecto sustantivos y adjetivos, en su forma base)
    en una lista de textos. Cada palabra se cuenta una vez por reseña, para que una
    reseña larga que repite "desayuno" cinco veces no pese más que cinco reseñas.
    """
    nlp = obtener_modelo()
    excluir = PALABRAS_GENERICAS | {e.lower() for e in (excluir or set())}
    # Se cuenta sin tildes para unir "máquina" y "maquina" (faltas frecuentes en reseñas),
    # y se muestra la forma más usada
    conteo: Counter[str] = Counter()
    formas: dict[str, Counter[str]] = defaultdict(Counter)
    for doc in nlp.pipe(t for t in textos if t and t != "[Sin texto]"):
        palabras = {
            token.lemma_.lower()
            for token in doc
            if token.pos_ in tipos and not token.is_stop and token.is_alpha and len(token.text) > 2
            and token.lemma_.lower() not in excluir and token.text.lower() not in excluir
        }
        for palabra in palabras:
            clave = _sin_tildes(palabra)
            formas[clave][palabra] += 1
        conteo.update({_sin_tildes(p) for p in palabras})
    return [(formas[clave].most_common(1)[0][0], n) for clave, n in conteo.most_common(cantidad)]
