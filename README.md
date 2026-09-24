# Adivina_Estudio — Renovación "Bosque mágico"

Aplicación educativa web (prototipo Streamlit) con Ghostie, un asistente de
IA de enfoque pedagógico, adivinanzas por materia, biblioteca de materiales
propios y un panel de misiones con progreso y puntos.

## Qué cambió en esta renovación

- **Visual:** paleta "Bosque mágico" (`#F7FBF4`, `#2F7D62`, `#A8D672`,
  `#F2B84B`, `#27364A`), tipografía Sora (títulos) + Manrope (lectura),
  identidad propia de Ghostie, animaciones sutiles y estados claros de
  carga / acierto / error.
- **Panel de misiones:** una tarjeta por materia con barra de progreso,
  puntos y accesos rápidos.
- **Ghostie más inteligente:** antes de responder detecta intención
  (duda puntual, repaso, examen), materia y nivel de comprensión; sigue
  una secuencia fija (reconocer → explicar → pista/ejemplo → pregunta de
  comprobación → fuente para verificar); muestra un resumen de los pasos
  mientras piensa; y nunca deja de responder aunque falle la conexión
  (cae a un modo sin conexión con la misma estructura).
- **Biblioteca de materiales:** sube tus apuntes (.txt, .md, .pdf),
  organizados por materia; Ghostie los usa como contexto prioritario y
  siempre indica si una respuesta viene de tus materiales, de
  conocimiento escolar general, o de una fuente externa sugerida.
- **Seguridad:** contraseñas con PBKDF2-HMAC-SHA256 y sal por usuario;
  todo el acceso a datos (progreso, chat, materiales) queda filtrado por
  `usuario_id`; la clave de IA **ya no se pide a los estudiantes** —
  solo se lee del servidor (variable de entorno o `secrets.toml`).

## Instalación local

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Configurar la IA de Ghostie (Groq)

Ghostie funciona sin clave configurada (modo sin conexión, con pistas
genéricas). Para respuestas generadas con IA, configura una clave de
[Groq](https://console.groq.com/) de una de estas dos formas:

**Opción A — variable de entorno**

```bash
export GROQ_API_KEY="tu_clave_aqui"
streamlit run app.py
```

**Opción B — `secrets.toml` (recomendado en Streamlit Community Cloud)**

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edita .streamlit/secrets.toml y pega tu clave
```

`\.streamlit/secrets.toml` está en `.gitignore`: nunca se sube a GitHub.

## Subir este proyecto a GitHub

```bash
git init
git add .
git commit -m "Renovación Bosque mágico: visual, Ghostie pedagógico y biblioteca de materiales"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
git push -u origin main
```

Si ya tenías un repositorio con el prototipo anterior, reemplaza los
archivos por los de esta carpeta, revisa el `git diff`, y luego:

```bash
git add .
git commit -m "Renovación Bosque mágico"
git push
```

## Estructura del proyecto

```
app.py            # Interfaz Streamlit (10 pantallas) y enrutador
ai_engine.py       # Motor pedagógico de Ghostie (Groq + modo sin conexión)
database.py        # SQLite: usuarios, chat, adivinanzas, materiales, progreso
materials.py        # Extracción de texto de archivos subidos (.txt/.md/.pdf)
riddles.py          # Banco de adivinanzas por materia
requirements.txt
.streamlit/secrets.toml.example
```

## Notas para producción

- SQLite es local a la instancia; para varios usuarios concurrentes en
  producción, migra a Postgres (el esquema de `database.py` está pensado
  para portarse casi sin cambios de lógica).
- Antes de desplegar, revisa los límites de la API de Groq y el tamaño
  máximo de materiales (`materials.MAX_CARACTERES`).
