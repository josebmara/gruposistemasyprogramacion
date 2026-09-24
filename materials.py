"""
materials.py
------------
Utilidades para la "Biblioteca de materiales": convierte archivos que
sube el estudiante (guías, apuntes) a texto plano para guardarlos en
la base de datos y usarlos como contexto prioritario de Ghostie.

Formatos soportados: .txt, .md, .pdf
Límite de tamaño para mantener el prototipo liviano y evitar que un
archivo enorme se cuele entero en cada prompt de IA.
"""

MAX_CARACTERES = 20_000


def extraer_texto(nombre_archivo: str, datos_binarios: bytes) -> str:
    """Devuelve el texto plano de un archivo subido, recortado a un
    tamaño razonable. Lanza ValueError si el formato no es soportado."""
    extension = nombre_archivo.lower().rsplit(".", 1)[-1] if "." in nombre_archivo else ""

    if extension in ("txt", "md"):
        texto = datos_binarios.decode("utf-8", errors="ignore")
    elif extension == "pdf":
        texto = _extraer_texto_pdf(datos_binarios)
    else:
        raise ValueError(
            "Formato no soportado. Sube un archivo .txt, .md o .pdf."
        )

    texto = texto.strip()
    if not texto:
        raise ValueError("No se encontró texto legible en el archivo.")
    return texto[:MAX_CARACTERES]


def _extraer_texto_pdf(datos_binarios: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError(
            "Falta la librería 'pypdf' para leer PDF. Agrégala a requirements.txt."
        ) from exc
    import io

    lector = PdfReader(io.BytesIO(datos_binarios))
    partes = [pagina.extract_text() or "" for pagina in lector.pages]
    return "\n".join(partes)


def resumen_corto(texto: str, longitud: int = 160) -> str:
    """Vista previa corta para listar materiales en la biblioteca."""
    limpio = " ".join(texto.split())
    return limpio[:longitud] + ("…" if len(limpio) > longitud else "")
