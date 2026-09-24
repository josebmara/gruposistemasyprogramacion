"""
ai_engine.py
------------
Motor pedagógico de IA para el chat de Ghostie.

Cambios frente a la versión anterior:
- Antes de responder, detecta intención (duda puntual / repaso / examen /
  charla libre), materia y nivel de comprensión aproximado.
- Sigue una secuencia fija: reconocer la duda -> explicar brevemente ->
  dar una pista o ejemplo -> hacer una pregunta de comprobación ->
  proponer una fuente para verificar.
- Usa como contexto prioritario los materiales propios del estudiante
  (biblioteca), y distingue en la respuesta entre lo que viene de esos
  materiales, del conocimiento escolar general, o de una fuente externa
  sugerida (nunca inventa citas de páginas específicas).
- Devuelve también un resumen de "pasos de razonamiento" pensado para
  mostrarse en la interfaz mientras se genera la respuesta (no es una
  cadena de pensamiento cruda del modelo, es una bitácora corta y segura
  de mostrar).
- Los errores reales (de red, de formato, de la API) nunca rompen el
  chat: se capturan y se devuelven de forma comprensible para el
  estudiante, junto con el detalle técnico aparte para quien programe.

La API key NUNCA se pide ni se guarda desde el navegador/sesión del
estudiante: solo se lee del entorno del servidor (variable de entorno
o st.secrets), como exige la especificación de seguridad.
"""

import json
import os
import random
import re

import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-70b-8192"

MATERIAS_CONOCIDAS = ["Matemáticas", "Ciencias", "Lenguaje", "Historia", "General"]


class GhostieError(Exception):
    """Error comprensible para mostrar al estudiante, con el detalle
    técnico real guardado aparte (para logs / modo administrador)."""

    def __init__(self, mensaje_amigable: str, detalle_tecnico: str = ""):
        super().__init__(mensaje_amigable)
        self.mensaje_amigable = mensaje_amigable
        self.detalle_tecnico = detalle_tecnico


# ----------------------------------------------------------------------
# 1. Detección de intención / nivel antes de responder
# ----------------------------------------------------------------------
PISTAS_INTENCION = {
    "examen": ["examen", "evaluación", "prueba rápida", "quiz"],
    "repaso": ["repaso", "repasar", "resumen de", "recordar"],
    "duda_puntual": ["no entiendo", "cómo se", "qué es", "por qué", "ayuda con", "no me sale"],
}

PISTAS_NIVEL_BAJO = ["no entiendo nada", "estoy perdido", "no sé por dónde empezar", "explícamelo fácil"]
PISTAS_NIVEL_ALTO = ["ya sé lo básico", "solo quiero confirmar", "creo que es", "tengo una duda avanzada"]


def detectar_intencion(mensaje: str) -> str:
    texto = mensaje.lower()
    for intencion, pistas in PISTAS_INTENCION.items():
        if any(p in texto for p in pistas):
            return intencion
    return "duda_puntual"


def detectar_nivel(mensaje: str) -> str:
    texto = mensaje.lower()
    if any(p in texto for p in PISTAS_NIVEL_BAJO):
        return "inicial"
    if any(p in texto for p in PISTAS_NIVEL_ALTO):
        return "avanzado"
    return "intermedio"


def pasos_de_analisis(mensaje: str, materia: str):
    """Bitácora corta y segura de mostrar en la UI mientras Ghostie
    prepara la respuesta (no expone razonamiento interno del modelo)."""
    intencion = detectar_intencion(mensaje)
    nivel = detectar_nivel(mensaje)
    etiquetas_intencion = {
        "examen": "preparar un examen rápido",
        "repaso": "hacer un repaso",
        "duda_puntual": "resolver una duda puntual",
    }
    return [
        f"Leyendo tu mensaje sobre {materia}…",
        f"Detectando qué necesitas: {etiquetas_intencion[intencion]}.",
        f"Ajustando el nivel de explicación ({nivel}).",
        "Revisando tus materiales guardados para esa materia…",
        "Armando la respuesta paso a paso…",
    ], intencion, nivel


# ----------------------------------------------------------------------
# 2. Construcción del prompt con contexto priorizado
# ----------------------------------------------------------------------
SYSTEM_PROMPT = """Eres "Ghostie", el asistente virtual fantasma de la app \
educativa Adivina_Estudio, para estudiantes menores de edad.

MATERIA ACTUAL: {materia}
INTENCIÓN DETECTADA: {intencion}
NIVEL DE COMPRENSIÓN DETECTADO: {nivel}

SECUENCIA OBLIGATORIA de toda respuesta:
1. Reconoce la duda del estudiante en una frase breve y cálida.
2. Da una explicación breve (2-4 frases), adaptada al nivel detectado \
({nivel}) y con ejemplos propios de {materia}. Nunca la escribas como \
si fuera la respuesta lista de una tarea o examen puntual: siempre deja \
algo para que el estudiante complete razonando.
3. Da una pista o un ejemplo adicional que ayude a practicar la idea.
4. Termina con UNA pregunta de comprobación que el estudiante pueda \
responder para saber si entendió.
5. Sugiere una fuente para verificar (puede ser "tus apuntes de {materia}", \
"tu docente", un tipo de libro o sitio educativo general — nunca inventes \
un enlace o cita textual de un libro/sitio específico que no puedas verificar).

CONTEXTO PRIORITARIO (materiales propios del estudiante, úsalo primero si aplica):
{contexto_materiales}

REGLAS INQUEBRANTABLES:
- Nunca dependas de respuestas genéricas: adapta vocabulario, profundidad y \
ejemplos a lo que el estudiante realmente escribió, no repitas una plantilla.
- Nunca dês una respuesta final cerrada de examen/tarea sin dejar un paso de \
razonamiento para el estudiante.
- Alerta a sesgos de género, raza o cultura; ejemplos equilibrados.
- Nunca pidas datos personales sensibles (dirección, teléfono, contraseñas).
- Tono cálido, paciente, motivador y apto para menores.

FORMATO DE SALIDA: responde ÚNICAMENTE un objeto JSON válido, sin texto \
fuera de él, con estas claves exactas:
{{
  "reconocimiento": "frase breve reconociendo la duda",
  "explicacion": "explicación breve adaptada al nivel",
  "pista_o_ejemplo": "una pista o ejemplo concreto",
  "pregunta_comprobacion": "una pregunta para que el estudiante confirme que entendió",
  "fuente_sugerida": "fuente para verificar, en texto simple",
  "tipo_fuente": "material_usuario" | "conocimiento_general" | "fuente_externa_sugerida",
  "usa_material_propio": true | false
}}
"""


def _formatear_contexto_materiales(materiales: list) -> str:
    if not materiales:
        return "(El estudiante no tiene materiales propios guardados para esta materia todavía.)"
    bloques = []
    for m in materiales:
        fragmento = m["contenido"][:1200]
        bloques.append(f'- "{m["titulo"]}": {fragmento}')
    return "\n".join(bloques)


def _construir_mensajes(materia: str, intencion: str, nivel: str, materiales: list,
                         historial: list, mensaje_usuario: str):
    system = SYSTEM_PROMPT.format(
        materia=materia,
        intencion=intencion,
        nivel=nivel,
        contexto_materiales=_formatear_contexto_materiales(materiales),
    )
    mensajes = [{"role": "system", "content": system}]
    for turno in (historial or [])[-6:]:
        rol = "assistant" if turno["rol"] == "ghostie" else "user"
        contenido = turno["mensaje"]
        mensajes.append({"role": rol, "content": contenido})
    mensajes.append({"role": "user", "content": mensaje_usuario})
    return mensajes


# ----------------------------------------------------------------------
# 3. Modo sin conexión (respaldo determinista, mismo formato de salida)
# ----------------------------------------------------------------------
class GhostieOffline:
    """Respaldo sin conexión: sigue la misma secuencia pedagógica con
    banco de frases genéricas, para que el prototipo nunca se quede
    sin respuesta durante una demostración sin API key."""

    PISTAS_GENERICAS = [
        "¿Qué es lo primero que ya sabes sobre este tema?",
        "Si tuvieras que explicárselo a un compañero, ¿cómo empezarías?",
        "¿Qué pasaría si cambiamos un dato del problema? ¿La respuesta seguiría igual?",
    ]

    def responder(self, mensaje_usuario: str, materia: str, intencion: str,
                  nivel: str, materiales: list) -> dict:
        usa_material = bool(materiales)
        fuente = (
            f'tus apuntes "{materiales[0]["titulo"]}"' if usa_material
            else f"tu docente o un libro de texto de {materia}"
        )
        return {
            "reconocimiento": f"Veo que tienes una duda sobre {materia}, ¡vamos paso a paso!",
            "explicacion": (
                f"Ahora mismo estoy en modo sin conexión, así que no puedo generar una "
                f"explicación personalizada de IA, pero puedo guiarte igual: piensa en lo que "
                f"ya sabes de {materia} y en cómo se relaciona con tu pregunta."
            ),
            "pista_o_ejemplo": random.choice(self.PISTAS_GENERICAS),
            "pregunta_comprobacion": "¿Puedes contarme con tus palabras qué entendiste hasta ahora?",
            "fuente_sugerida": fuente,
            "tipo_fuente": "material_usuario" if usa_material else "conocimiento_general",
            "usa_material_propio": usa_material,
            "modo_offline": True,
        }


# ----------------------------------------------------------------------
# 4. Punto de entrada principal
# ----------------------------------------------------------------------
def _api_key_servidor() -> str | None:
    """Solo lee la clave del entorno del servidor. Nunca desde un campo
    de texto del navegador/estudiante."""
    clave = os.environ.get("GROQ_API_KEY")
    if not clave:
        try:
            import streamlit as st
            clave = st.secrets.get("GROQ_API_KEY")  # type: ignore[attr-defined]
        except Exception:
            clave = None
    return clave


def _extraer_json(texto: str) -> dict:
    texto = texto.strip()
    # Tolera que el modelo envuelva el JSON en ```json ... ```
    coincidencia = re.search(r"\{.*\}", texto, re.DOTALL)
    if not coincidencia:
        raise ValueError("La respuesta del modelo no contenía JSON.")
    return json.loads(coincidencia.group(0))


def responder_pedagogico(mensaje_usuario: str, materia: str, historial: list,
                          materiales: list) -> dict:
    """Genera la respuesta estructurada de Ghostie.

    Devuelve un dict con las claves del esquema JSON descrito arriba,
    más "modo_offline" (bool) para que la interfaz lo muestre si aplica.
    Nunca lanza una excepción hacia la UI: en caso de error real, cae en
    modo offline y adjunta el detalle técnico en "_error_tecnico" para
    quien depure, sin mostrárselo crudo al estudiante.
    """
    intencion = detectar_intencion(mensaje_usuario)
    nivel = detectar_nivel(mensaje_usuario)
    api_key = _api_key_servidor()

    if not api_key:
        return GhostieOffline().responder(mensaje_usuario, materia, intencion, nivel, materiales)

    payload = {
        "model": GROQ_MODEL,
        "messages": _construir_mensajes(materia, intencion, nivel, materiales, historial, mensaje_usuario),
        "temperature": 0.5,
        "max_tokens": 600,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        contenido = resp.json()["choices"][0]["message"]["content"]
        datos = _extraer_json(contenido)
        datos.setdefault("tipo_fuente", "conocimiento_general")
        datos.setdefault("usa_material_propio", bool(materiales))
        datos["modo_offline"] = False
        return datos
    except requests.exceptions.Timeout as e:
        resultado = GhostieOffline().responder(mensaje_usuario, materia, intencion, nivel, materiales)
        resultado["_error_tecnico"] = f"Timeout al llamar a la API: {e}"
        return resultado
    except requests.exceptions.RequestException as e:
        resultado = GhostieOffline().responder(mensaje_usuario, materia, intencion, nivel, materiales)
        resultado["_error_tecnico"] = f"Error de red/API: {e}"
        return resultado
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        resultado = GhostieOffline().responder(mensaje_usuario, materia, intencion, nivel, materiales)
        resultado["_error_tecnico"] = f"Respuesta del modelo no interpretable: {e}"
        return resultado


def formatear_respuesta_markdown(datos: dict) -> str:
    """Convierte el JSON estructurado en el texto que se muestra en el
    chat, con las fuentes siempre visibles."""
    iconos_fuente = {
        "material_usuario": "📘 de tus materiales",
        "conocimiento_general": "🧠 conocimiento escolar general",
        "fuente_externa_sugerida": "🔎 fuente externa sugerida",
    }
    etiqueta_fuente = iconos_fuente.get(datos.get("tipo_fuente"), "🧠 conocimiento escolar general")

    partes = [
        datos.get("reconocimiento", "").strip(),
        "",
        datos.get("explicacion", "").strip(),
        "",
        f"💡 **Pista:** {datos.get('pista_o_ejemplo', '').strip()}",
        "",
        f"❓ **Para comprobar:** {datos.get('pregunta_comprobacion', '').strip()}",
        "",
        f"📚 **Verifica en:** {datos.get('fuente_sugerida', '').strip()}  ·  _{etiqueta_fuente}_",
    ]
    if datos.get("modo_offline"):
        partes.insert(0, "_👻 (modo sin conexión — configura GROQ_API_KEY en el servidor para respuestas con IA)_")
    return "\n".join(partes)
