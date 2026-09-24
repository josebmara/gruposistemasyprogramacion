"""
app.py
------
Adivina_Estudio - Prototipo funcional en Streamlit.

Renovación "Bosque mágico": mismas 8 pantallas del proyecto original
más una nueva (Biblioteca de materiales), con:
    1. Inicio
    2. Registro / Inicio de sesión
    3. Panel principal (misiones, progreso, puntos, accesos rápidos)
    4. Chat de Ghostie (motor pedagógico con fuentes visibles)
    5. Adivinanzas
    6. Perfil
    7. Puntaje
    8. Preferencias
    9. Biblioteca de materiales
   10. Ayuda / Acerca de Ghostie

Ejecutar con:
    streamlit run app.py
"""

import streamlit as st

import database as db
import riddles
import materials
from ai_engine import responder_pedagogico, formatear_respuesta_markdown, pasos_de_analisis

# ----------------------------------------------------------------------
# Configuración general y paleta "Bosque mágico"
# ----------------------------------------------------------------------
st.set_page_config(page_title="Adivina_Estudio", page_icon="👻", layout="centered")

PALETA = {
    "fondo": "#F7FBF4",
    "verde": "#2F7D62",
    "musgo": "#A8D672",
    "amarillo": "#F2B84B",
    "tinta": "#27364A",
    "tarjeta": "#FFFFFF",
    "verde_claro": "#E4F2E9",
    "rojo_suave": "#F4C6C1",
}

COLOR_MATERIA = {
    "Ciencias": PALETA["verde"],
    "Matemáticas": "#3E8FB0",
    "Lenguaje": "#B0679E",
    "Historia": PALETA["amarillo"],
    "General": PALETA["musgo"],
}

DESTINOS_DASHBOARD = [
    ("👤 Perfil", "perfil"),
    ("🏆 Puntaje", "puntaje"),
    ("💬 Hablar con Ghostie", "chat"),
    ("🧩 Adivinanzas", "adivinanzas"),
    ("📚 Materiales", "materiales"),
    ("⚙️ Preferencias", "preferencias"),
]

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=Manrope:wght@400;500;600;700&display=swap');

html, body, .stApp {{
    background-color: {PALETA['fondo']};
    font-family: 'Manrope', sans-serif;
}}
*, *::before, *::after {{ color: {PALETA['tinta']}; }}
.stApp h1, .stApp h2, .stApp h3, .stApp h4,
.ghostie-title, .hero-text h1, .hero-text p {{
    font-family: 'Sora', sans-serif !important;
    color: {PALETA['tinta']} !important;
}}

.stApp input, .stApp textarea,
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea {{
    color: {PALETA['tinta']} !important;
    background-color: #FFFFFF !important;
    border-radius: 12px !important;
    border: 1px solid {PALETA['musgo']} !important;
}}
[data-baseweb="select"] *, .react-aria-ComboBox * {{ color: {PALETA['tinta']} !important; }}
[data-baseweb="select"] > div, .react-aria-ComboBox,
.react-aria-ComboBox [role="group"], .react-aria-ComboBox input,
.react-aria-ComboBox button {{
    background-color: #FFFFFF !important;
    border-radius: 12px !important;
}}
[role="listbox"], [role="option"], [role="presentation"],
div[data-baseweb="popover"], div[data-baseweb="menu"] {{
    background-color: #FFFFFF !important;
    color: {PALETA['tinta']} !important;
}}
[role="option"]:hover {{ background-color: {PALETA['verde_claro']} !important; }}

[data-testid="stHeader"], [data-testid="stBottom"],
[data-testid="stBottomBlockContainer"], [data-testid="stChatInput"] {{
    background-color: {PALETA['fondo']} !important;
}}
[data-testid="stBottom"] > div, [data-testid="stChatInput"] > div {{
    background-color: transparent !important;
}}
[data-testid="stAlert"] * {{ color: {PALETA['tinta']} !important; }}

/* Botones */
div.stButton > button, [data-testid="stFormSubmitButton"] button {{
    border-radius: 999px !important;
    border: none !important;
    padding: 0.6em 1.4em !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 700 !important;
    width: 100%;
    background: {PALETA['verde']};
    color: #FFFFFF !important;
    box-shadow: 0 2px 6px rgba(47,125,98,0.18);
    transition: transform 0.12s ease, filter 0.12s ease;
}}
div.stButton > button *, [data-testid="stFormSubmitButton"] button * {{ color: #FFFFFF !important; }}
div.stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {{
    filter: brightness(1.06);
    transform: translateY(-1px);
}}

/* Insignia fantasma (identidad de Ghostie) */
.ghostie-badge {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 84px; height: 84px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 30%, #FFFFFF, {PALETA['verde_claro']} 60%, {PALETA['musgo']} 100%);
    font-size: 2.6em;
    box-shadow: 0 6px 16px rgba(47,125,98,0.25);
    animation: flotar 3s ease-in-out infinite;
}}
@keyframes flotar {{
    0%, 100% {{ transform: translateY(0px); }}
    50% {{ transform: translateY(-6px); }}
}}
.fade-in {{ animation: aparecer 0.4s ease both; }}
@keyframes aparecer {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

.pill-dark {{
    display: inline-block;
    background: {PALETA['tinta']};
    color: #FFFFFF !important;
    font-family: 'Sora', sans-serif;
    font-weight: 700;
    padding: 0.5em 1.6em;
    border-radius: 999px;
    font-size: 1.05em;
}}
.pill-dark * {{ color: #FFFFFF !important; }}

.tarjeta-blanca {{
    background: {PALETA['tarjeta']};
    border-radius: 24px;
    padding: 28px 20px;
    text-align: center;
    box-shadow: 0 6px 18px rgba(39,54,74,0.08);
    margin-bottom: 18px;
    border: 1px solid {PALETA['verde_claro']};
}}

/* Franja decorativa de bosque (reemplaza el arco arcoíris) */
.forest-bar {{
    height: 8px;
    border-radius: 999px;
    margin: 4px 0 22px 0;
    background: linear-gradient(90deg, {PALETA['musgo']}, {PALETA['verde']}, {PALETA['amarillo']});
}}

.hero-text {{ text-align: center; margin-bottom: 10px; }}
.hero-text h1 {{ font-size: 1.9em; margin: 0.2em 0 0.1em 0; }}
.hero-text p {{ margin-top: 4px; font-size: 0.95em; }}

/* Chip de materia */
.materia-chip {{
    display: inline-block;
    padding: 0.3em 0.9em;
    border-radius: 999px;
    margin-bottom: 0.6em;
    font-family: 'Sora', sans-serif;
    font-weight: 700;
    color: #FFFFFF !important;
}}
.materia-chip * {{ color: #FFFFFF !important; }}

/* Encabezado del chat */
.chat-header {{
    background: linear-gradient(135deg, {PALETA['verde']}, #245F4B);
    color: #FFFFFF !important;
    border-radius: 18px;
    padding: 14px 18px;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 10px;
}}
.chat-header * {{ color: #FFFFFF !important; }}
.chat-header .icon {{ font-size: 1.8em; }}
.chat-header .titulo {{ font-family: 'Sora', sans-serif; font-weight: 700; font-size: 1.2em; }}

/* Tarjeta de misión (panel principal) */
.mision-card {{
    background: {PALETA['tarjeta']};
    border-radius: 20px;
    padding: 16px 18px;
    margin-bottom: 14px;
    border: 1px solid {PALETA['verde_claro']};
    box-shadow: 0 4px 12px rgba(39,54,74,0.06);
}}
.mision-titulo {{
    font-family: 'Sora', sans-serif;
    font-weight: 700;
    font-size: 1.05em;
    display: flex;
    justify-content: space-between;
}}
.progreso-track {{
    background: {PALETA['verde_claro']};
    border-radius: 999px;
    height: 10px;
    margin: 8px 0 4px 0;
    overflow: hidden;
}}
.progreso-fill {{
    background: linear-gradient(90deg, {PALETA['musgo']}, {PALETA['verde']});
    height: 100%;
    border-radius: 999px;
    transition: width 0.5s ease;
}}
.progreso-label {{ font-size: 0.82em; color: {PALETA['tinta']}; opacity: 0.75; }}

.ribbon-titulo {{
    text-align: center;
    font-family: 'Sora', sans-serif;
    font-weight: 700;
    font-size: 1.4em;
    margin-bottom: 10px;
}}
.ribbon {{
    background: {PALETA['verde_claro']};
    border: 1.5px solid {PALETA['musgo']};
    color: {PALETA['tinta']} !important;
    font-weight: 600;
    text-align: center;
    padding: 22px 34px;
    border-radius: 16px;
    margin-bottom: 18px;
}}

.resultado-correcto, .resultado-incorrecto {{
    text-align: center;
    font-family: 'Sora', sans-serif;
    font-weight: 700;
    font-size: 1.1em;
    padding: 12px;
    border-radius: 14px;
    margin-top: 10px;
}}
.resultado-correcto {{
    background: {PALETA['verde_claro']};
    border: 1.5px solid {PALETA['musgo']};
    animation: acierto-pulso 0.5s ease;
}}
.resultado-incorrecto {{
    background: {PALETA['rojo_suave']};
    border: 1.5px solid #E39A92;
    animation: error-shake 0.4s ease;
}}
@keyframes acierto-pulso {{
    0% {{ transform: scale(0.97); opacity: 0.6; }}
    100% {{ transform: scale(1); opacity: 1; }}
}}
@keyframes error-shake {{
    0%, 100% {{ transform: translateX(0); }}
    25% {{ transform: translateX(-4px); }}
    75% {{ transform: translateX(4px); }}
}}

.material-item {{
    background: {PALETA['tarjeta']};
    border: 1px solid {PALETA['verde_claro']};
    border-radius: 14px;
    padding: 10px 14px;
    margin-bottom: 8px;
}}
.material-item .titulo {{ font-weight: 700; font-family: 'Sora', sans-serif; }}
.material-item .meta {{ font-size: 0.8em; opacity: 0.7; }}

.fuente-badge {{
    display: inline-block;
    font-size: 0.78em;
    padding: 0.15em 0.7em;
    border-radius: 999px;
    background: {PALETA['verde_claro']};
    margin-top: 4px;
}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def _icono_bosque_svg() -> str:
    """Insignia decorativa sencilla en SVG (reemplaza el arco arcoíris)."""
    return f"""
    <svg viewBox="0 0 200 90" width="220" style="display:block;margin:0 auto;">
      <ellipse cx="60" cy="55" rx="34" ry="30" fill="{PALETA['musgo']}" opacity="0.85"/>
      <ellipse cx="100" cy="40" rx="42" ry="38" fill="{PALETA['verde']}" opacity="0.9"/>
      <ellipse cx="145" cy="55" rx="30" ry="26" fill="{PALETA['amarillo']}" opacity="0.8"/>
    </svg>
    """


def hero_header(titulo: str, subtitulo: str = ""):
    st.markdown(
        f"""
        <div class="hero-text fade-in">
            {_icono_bosque_svg()}
            <h1>{titulo}</h1>
            {f'<p>{subtitulo}</p>' if subtitulo else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def barra_bosque():
    st.markdown('<div class="forest-bar"></div>', unsafe_allow_html=True)


db.init_db()

# ----------------------------------------------------------------------
# Estado de sesión
# ----------------------------------------------------------------------
if "pagina" not in st.session_state:
    st.session_state.pagina = "inicio"
if "usuario" not in st.session_state:
    st.session_state.usuario = None


def ir_a(pagina: str):
    st.session_state.pagina = pagina


def usuario_actual():
    if st.session_state.usuario:
        return db.obtener_usuario(st.session_state.usuario["id"])
    return None


# ----------------------------------------------------------------------
# 1. INICIO
# ----------------------------------------------------------------------
def pagina_inicio():
    st.markdown(
        f"""
        <div class="tarjeta-blanca fade-in">
            <div class="ghostie-badge">👻</div>
            <div class="pill-dark" style="margin-top:14px;">Adivina_Estudio</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    barra_bosque()
    st.caption("IA con enfoque pedagógico — piensa, no dependas.")
    st.write(
        "Ghostie es tu mascota-guía: reconoce tu duda, te explica lo justo, "
        "te da una pista, te pregunta si entendiste y te dice dónde verificarlo. "
        "Nunca hace la tarea por ti."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Iniciar sesión", use_container_width=True):
            ir_a("login")
    with col2:
        if st.button("Registrarme", use_container_width=True):
            ir_a("registro")


# ----------------------------------------------------------------------
# 2. REGISTRO / INICIO DE SESIÓN
# ----------------------------------------------------------------------
def pagina_login():
    col_hero, col_form = st.columns([1, 1.1])
    with col_hero:
        hero_header("Inicia sesión", "Utiliza tu usuario para poder ingresar.")
    with col_form:
        with st.form("form_login"):
            nombre_usuario = st.text_input("Nombre de usuario")
            password = st.text_input("Contraseña", type="password")
            enviar = st.form_submit_button("Entrar", use_container_width=True)
        if enviar:
            with st.spinner("Verificando tus datos…"):
                usuario = db.validar_login(nombre_usuario, password)
            if usuario:
                st.session_state.usuario = usuario
                ir_a("dashboard")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    st.divider()
    if st.button("¿No tienes cuenta? Regístrate"):
        ir_a("registro")


def pagina_registro():
    col_hero, col_form = st.columns([1, 1.1])
    with col_hero:
        hero_header("Regístrate", "¡Únete a esta comunidad!")
        st.caption("En caso de ya ser usuario, ¡por favor inicia sesión!")
    with col_form:
        with st.form("form_registro"):
            correo = st.text_input("Correo electrónico")
            nombre_usuario = st.text_input("Nombre de usuario")
            password = st.text_input("Contraseña", type="password")
            enviar = st.form_submit_button("Crear cuenta", use_container_width=True)
        if enviar:
            if not correo or not nombre_usuario or not password:
                st.warning("Completa todos los campos.")
            elif len(password) < 6:
                st.warning("La contraseña debe tener al menos 6 caracteres.")
            else:
                with st.spinner("Creando tu cuenta…"):
                    ok, msg = db.crear_usuario(nombre_usuario, correo, password)
                if ok:
                    st.success(msg + " Ahora inicia sesión.")
                    ir_a("login")
                    st.rerun()
                else:
                    st.error(msg)
    st.divider()
    if st.button("En caso de ya ser usuario, favor iniciar sesión"):
        ir_a("login")


# ----------------------------------------------------------------------
# 3. PANEL PRINCIPAL (misiones, progreso, puntos, accesos rápidos)
# ----------------------------------------------------------------------
def _tarjeta_mision(materia: str, usuario: dict):
    total = riddles.total_por_materia(materia)
    progreso = db.progreso_por_materia(usuario["id"], materia, total)
    color = COLOR_MATERIA.get(materia, PALETA["musgo"])
    st.markdown(
        f"""
        <div class="mision-card fade-in">
            <div class="mision-titulo">
                <span><span class="materia-chip" style="background:{color}">{materia}</span></span>
                <span>{progreso['resueltas']}/{progreso['total']} 🧩</span>
            </div>
            <div class="progreso-track">
                <div class="progreso-fill" style="width:{progreso['porcentaje']}%;"></div>
            </div>
            <div class="progreso-label">Misión completada al {progreso['porcentaje']}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def pagina_dashboard():
    usuario = usuario_actual()
    st.markdown(f"### 👻 ¡Hola, {usuario['nombre_usuario']}!")
    st.write(f"⭐ Puntos: **{usuario['puntos']}**  |  📘 Materia preferida: **{usuario['materia_preferida']}**")
    barra_bosque()

    st.markdown("#### Tus misiones por materia")
    for materia in riddles.MATERIAS:
        _tarjeta_mision(materia, usuario)

    st.markdown("#### Accesos rápidos")
    cols = st.columns(2)
    for i, (etiqueta, destino) in enumerate(DESTINOS_DASHBOARD):
        with cols[i % 2]:
            if st.button(etiqueta, use_container_width=True, key=f"dash_{destino}"):
                ir_a(destino)

    st.divider()
    if st.button("Cerrar sesión"):
        st.session_state.usuario = None
        ir_a("inicio")
        st.rerun()


def pagina_perfil():
    usuario = usuario_actual()
    st.header("👤 Perfil")
    st.write(f"**Usuario:** {usuario['nombre_usuario']}")
    st.write(f"**Correo:** {usuario['correo']}")
    st.write(f"**Miembro desde:** {usuario['fecha_registro'][:10]}")
    st.write(f"**Puntos acumulados:** {usuario['puntos']}")
    if st.button("⬅ Volver al panel"):
        ir_a("dashboard")


def pagina_puntaje():
    st.header("🏆 Puntaje y recompensas")
    tabla = db.tabla_posiciones()
    if tabla:
        for i, fila in enumerate(tabla, start=1):
            st.write(f"{i}. **{fila['nombre_usuario']}** — {fila['puntos']} pts")
    else:
        st.info("Aún no hay puntajes registrados.")
    if st.button("⬅ Volver al panel"):
        ir_a("dashboard")


def pagina_preferencias():
    usuario = usuario_actual()
    st.header("⚙️ Preferencias")
    materia = st.selectbox(
        "Materia preferida", riddles.MATERIAS,
        index=riddles.MATERIAS.index(usuario["materia_preferida"])
        if usuario["materia_preferida"] in riddles.MATERIAS else 0,
    )
    if st.button("Guardar preferencia"):
        db.actualizar_preferencia(usuario["id"], materia)
        st.success("Preferencia actualizada.")
        st.rerun()
    if st.button("⬅ Volver al panel"):
        ir_a("dashboard")


def pagina_ayuda():
    st.header("❓ Ayuda / Acerca de Ghostie")
    st.write(
        "Ghostie usa un modelo de IA (Groq) configurado por quien administra el "
        "servidor de esta app. Por seguridad, la clave de acceso a la IA nunca se "
        "pide ni se guarda desde tu navegador: solo vive en el servidor."
    )
    st.write(
        "Si la clave no está configurada, Ghostie sigue funcionando en **modo sin "
        "conexión**, con la misma estructura de respuesta pero con pistas genéricas "
        "en vez de una explicación generada por IA."
    )
    st.caption("¿Eres quien administra el servidor? Configura la variable de entorno "
               "GROQ_API_KEY o el archivo .streamlit/secrets.toml (ver README).")
    if st.button("⬅ Volver al panel"):
        ir_a("dashboard")


# ----------------------------------------------------------------------
# 4. CHAT DE GHOSTIE
# ----------------------------------------------------------------------
def _enviar_a_ghostie(usuario, materia, mensaje, historial):
    db.guardar_mensaje_chat(usuario["id"], materia, "usuario", mensaje)
    materiales = db.buscar_materiales_relevantes(usuario["id"], materia)

    pasos, _, _ = pasos_de_analisis(mensaje, materia)
    with st.status("Ghostie está pensando…", expanded=True) as status:
        for paso in pasos[:-1]:
            st.write(paso)
        datos = responder_pedagogico(mensaje, materia, historial, materiales)
        st.write(pasos[-1])
        status.update(
            label="¡Listo! Aquí tienes la respuesta." if not datos.get("_error_tecnico")
            else "Hubo un problema de conexión, respondo en modo sin conexión.",
            state="complete",
        )

    if datos.get("_error_tecnico"):
        with st.expander("Detalle técnico (para quien administra la app)"):
            st.code(datos["_error_tecnico"])

    respuesta_md = formatear_respuesta_markdown(datos)
    db.guardar_mensaje_chat(usuario["id"], materia, "ghostie", respuesta_md, datos.get("tipo_fuente", ""))
    return respuesta_md


def pagina_chat():
    usuario = usuario_actual()
    materias_disponibles = riddles.MATERIAS + ["General"]
    materia = st.selectbox(
        "Materia del chat", materias_disponibles,
        index=materias_disponibles.index(usuario["materia_preferida"])
        if usuario["materia_preferida"] in materias_disponibles else 0,
    )

    st.markdown(
        f"""
        <div class="chat-header fade-in">
            <div class="icon">👻</div>
            <div class="titulo">Ghostie · {materia}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    materiales_materia = db.listar_materiales(usuario["id"], materia)
    if materiales_materia:
        st.caption(f"📚 Ghostie está usando {len(materiales_materia)} material(es) tuyo(s) de {materia} como contexto prioritario.")

    historial = db.obtener_historial_chat(usuario["id"], materia)

    st.caption("¿Qué puedo hacer por ti hoy?")
    acciones = [
        ("🧩 Juego adivinanza", "juego"),
        ("📖 Repaso de lo visto", "repaso"),
        ("📝 Examen rápido", "examen"),
    ]
    cols = st.columns(3)
    for col, (etiqueta, accion) in zip(cols, acciones):
        with col:
            if st.button(etiqueta, use_container_width=True, key=f"accion_{accion}"):
                if accion == "juego":
                    st.session_state.materia_adivinanza = materia if materia in riddles.MATERIAS else None
                    st.session_state.adivinanza_actual = None
                    ir_a("adivinanzas")
                    st.rerun()
                elif accion == "repaso":
                    _enviar_a_ghostie(usuario, materia, f"Ayúdame a repasar lo que hemos visto de {materia}.", historial)
                    st.rerun()
                elif accion == "examen":
                    _enviar_a_ghostie(usuario, materia, f"Hazme un examen rápido de {materia}.", historial)
                    st.rerun()

    for turno in historial:
        with st.chat_message("assistant" if turno["rol"] == "ghostie" else "user"):
            st.markdown(turno["mensaje"])

    mensaje = st.chat_input("Escribe tu duda aquí…")
    if mensaje:
        with st.chat_message("user"):
            st.write(mensaje)
        with st.chat_message("assistant"):
            respuesta_md = _enviar_a_ghostie(usuario, materia, mensaje, historial)
            st.markdown(respuesta_md)

    st.divider()
    if st.button("⬅ Volver al panel"):
        ir_a("dashboard")


# ----------------------------------------------------------------------
# 5. ADIVINANZAS
# ----------------------------------------------------------------------
def pagina_adivinanzas():
    usuario = usuario_actual()

    if "materia_adivinanza" not in st.session_state:
        st.session_state.materia_adivinanza = None
    if "adivinanza_actual" not in st.session_state:
        st.session_state.adivinanza_actual = None

    if st.session_state.materia_adivinanza is None:
        hero_header("Adivinanzas", "Selecciona un tema para comenzar:")
        cols = st.columns(len(riddles.MATERIAS))
        for i, materia in enumerate(riddles.MATERIAS):
            with cols[i]:
                if st.button(materia, key=f"mat_{materia}", use_container_width=True):
                    st.session_state.materia_adivinanza = materia
                    resueltas = db.adivinanzas_resueltas(usuario["id"])
                    st.session_state.adivinanza_actual = riddles.elegir_adivinanza(materia, resueltas)
                    st.rerun()
        if st.button("⬅ Volver al panel"):
            ir_a("dashboard")
        return

    materia = st.session_state.materia_adivinanza
    adivinanza = st.session_state.adivinanza_actual
    color = COLOR_MATERIA.get(materia, PALETA["musgo"])
    st.markdown(
        f'<span class="materia-chip" style="background:{color}">🕷️ {materia}</span>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="ribbon-titulo">La adivinanza de hoy es...</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ribbon fade-in">{adivinanza["pregunta"]}</div>', unsafe_allow_html=True)

    with st.expander("🕷️ Pedir una pista"):
        st.write(adivinanza["pista"])

    respuesta = st.text_input("¿Qué soy?", key=f"resp_{adivinanza['id']}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Comprobar respuesta", use_container_width=True):
            acerto = riddles.validar_respuesta(adivinanza, respuesta)
            db.registrar_intento_adivinanza(usuario["id"], adivinanza["id"], acerto)
            if acerto:
                db.sumar_puntos(usuario["id"], 10)
                st.markdown('<div class="resultado-correcto">✅ ¡Correcto! +10 puntos</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="resultado-incorrecto">❌ No es correcto. '
                    f'La respuesta era: {adivinanza["respuesta"]}.</div>',
                    unsafe_allow_html=True,
                )
    with col2:
        if st.button("Siguiente adivinanza", use_container_width=True):
            resueltas = db.adivinanzas_resueltas(usuario["id"])
            st.session_state.adivinanza_actual = riddles.elegir_adivinanza(materia, resueltas)
            st.rerun()

    st.divider()
    if st.button("Cambiar de materia"):
        st.session_state.materia_adivinanza = None
        st.session_state.adivinanza_actual = None
        st.rerun()
    if st.button("⬅ Volver al panel"):
        ir_a("dashboard")


# ----------------------------------------------------------------------
# 6. BIBLIOTECA DE MATERIALES
# ----------------------------------------------------------------------
def pagina_materiales():
    usuario = usuario_actual()
    st.header("📚 Biblioteca de materiales")
    st.caption(
        "Sube tus guías y apuntes (.txt, .md o .pdf). Ghostie los usará como "
        "contexto prioritario cuando chatees sobre esa materia, y siempre te "
        "dirá cuándo está usando uno de tus materiales."
    )

    with st.form("form_material"):
        materia = st.selectbox("Materia", riddles.MATERIAS + ["General"])
        titulo = st.text_input("Título del material (ej. 'Apuntes de fracciones')")
        archivo = st.file_uploader("Archivo (.txt, .md, .pdf)", type=["txt", "md", "pdf"])
        enviar = st.form_submit_button("Subir a mi biblioteca", use_container_width=True)

    if enviar:
        if not titulo or not archivo:
            st.warning("Completa el título y selecciona un archivo.")
        else:
            try:
                with st.spinner("Leyendo tu archivo…"):
                    texto = materials.extraer_texto(archivo.name, archivo.getvalue())
                db.guardar_material(usuario["id"], materia, titulo, texto)
                st.success(f'"{titulo}" se guardó en tu biblioteca de {materia}.')
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    st.divider()
    st.markdown("#### Tus materiales")
    filtro = st.selectbox("Filtrar por materia", ["Todas"] + riddles.MATERIAS + ["General"], key="filtro_materiales")
    lista = db.listar_materiales(usuario["id"], None if filtro == "Todas" else filtro)

    if not lista:
        st.info("Todavía no has subido materiales para esta materia.")
    for m in lista:
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(
                f"""
                <div class="material-item fade-in">
                    <div class="titulo">{m['titulo']}</div>
                    <div class="meta">{m['materia']} · {m['fecha'][:10]} · {m['tamano']} caracteres</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col2:
            if st.button("🗑️", key=f"del_{m['id']}", help="Eliminar material"):
                db.eliminar_material(usuario["id"], m["id"])
                st.rerun()

    st.divider()
    if st.button("⬅ Volver al panel"):
        ir_a("dashboard")


# ----------------------------------------------------------------------
# Enrutador principal
# ----------------------------------------------------------------------
PAGINAS_PUBLICAS = {"inicio": pagina_inicio, "login": pagina_login, "registro": pagina_registro}
PAGINAS_PRIVADAS = {
    "dashboard": pagina_dashboard,
    "perfil": pagina_perfil,
    "puntaje": pagina_puntaje,
    "chat": pagina_chat,
    "adivinanzas": pagina_adivinanzas,
    "materiales": pagina_materiales,
    "preferencias": pagina_preferencias,
    "ayuda": pagina_ayuda,
}

pagina = st.session_state.pagina
if pagina in PAGINAS_PUBLICAS:
    PAGINAS_PUBLICAS[pagina]()
elif pagina in PAGINAS_PRIVADAS:
    if st.session_state.usuario is None:
        st.warning("Debes iniciar sesión primero.")
        ir_a("login")
        st.rerun()
    else:
        PAGINAS_PRIVADAS[pagina]()
else:
    ir_a("inicio")
    st.rerun()
