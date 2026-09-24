"""
riddles.py
----------
Banco de adivinanzas usado en la sección de "Adivinanzas": acertijos
ligados a materias, con pistas dadas por Ghostie y sistema de puntos.
"""

import random

ADIVINANZAS = [
    {
        "id": "cie_01",
        "materia": "Ciencias",
        "pregunta": "Soy consistente, pero puedo cambiar; me componen "
                    "sustancias que fases tienen y pueden acabar. ¿Qué soy?",
        "pista": "Piensa en los tres estados en los que se presenta la materia.",
        "respuesta": "un sólido",
    },
    {
        "id": "cie_02",
        "materia": "Ciencias",
        "pregunta": "Vivo dentro de tus células, guardo tu información; "
                    "en espiral doble me enrollo, soy tu propia identificación. ¿Qué soy?",
        "pista": "Está formado por una doble hélice.",
        "respuesta": "el adn",
    },
    {
        "id": "mat_01",
        "materia": "Matemáticas",
        "pregunta": "Tengo tres lados y tres ángulos, y si los tres son "
                    "iguales, dicen que soy perfecto. ¿Qué figura soy?",
        "pista": "Es el polígono con menos lados que existe.",
        "respuesta": "un triangulo equilatero",
    },
    {
        "id": "mat_02",
        "materia": "Matemáticas",
        "pregunta": "Soy un número que solo se puede dividir entre 1 y "
                    "entre mí mismo. ¿Qué tipo de número soy?",
        "pista": "El 2, el 3 y el 7 son ejemplos míos.",
        "respuesta": "un numero primo",
    },
    {
        "id": "len_01",
        "materia": "Lenguaje",
        "pregunta": "Nombro personas, animales, lugares o cosas, pero "
                    "nunca hago una acción por mi cuenta. ¿Qué soy?",
        "pista": "Es una de las categorías gramaticales básicas.",
        "respuesta": "un sustantivo",
    },
    {
        "id": "len_02",
        "materia": "Lenguaje",
        "pregunta": "Sin mí, las oraciones no tendrían acción; te digo "
                    "qué hace el sujeto, en presente, pasado o futuro. ¿Qué soy?",
        "pista": "Se conjuga.",
        "respuesta": "un verbo",
    },
    {
        "id": "his_01",
        "materia": "Historia",
        "pregunta": "En 1492 crucé el mar, buscando otra ruta llegué a "
                    "encontrar un continente sin querer. ¿Quién soy?",
        "pista": "Zarpó desde España con tres carabelas.",
        "respuesta": "cristobal colon",
    },
]

MATERIAS = sorted({a["materia"] for a in ADIVINANZAS})


def adivinanzas_por_materia(materia: str):
    return [a for a in ADIVINANZAS if a["materia"] == materia]


def total_por_materia(materia: str) -> int:
    return len(adivinanzas_por_materia(materia))


def elegir_adivinanza(materia: str, ya_resueltas: set):
    """Devuelve una adivinanza de la materia dada que el usuario no
    haya resuelto todavía; si ya las resolvió todas, elige cualquiera."""
    disponibles = [a for a in adivinanzas_por_materia(materia) if a["id"] not in ya_resueltas]
    if not disponibles:
        disponibles = adivinanzas_por_materia(materia)
    return random.choice(disponibles) if disponibles else None


def validar_respuesta(adivinanza: dict, respuesta_usuario: str) -> bool:
    limpia = respuesta_usuario.strip().lower()
    correcta = adivinanza["respuesta"].strip().lower()
    # Coincidencia flexible: acepta si el usuario incluye la palabra clave
    palabra_clave = correcta.split()[-1]
    return limpia == correcta or palabra_clave in limpia
