"""
database.py
------------
Capa de persistencia de Adivina_Estudio.

Usa SQLite (motor gratuito, sin servidor) como reemplazo local de un
backend tipo Supabase/Lovable Cloud. El esquema está pensado para
migrar después a Postgres casi sin cambios de lógica.

Seguridad:
- Las contraseñas se guardan con PBKDF2-HMAC-SHA256 y una sal
  aleatoria distinta por usuario (nunca en texto plano).
- Todas las consultas están parametrizadas (sin f-strings con datos
  del usuario) para evitar inyección SQL.
- Cada función de lectura/escritura de datos "propios" exige el
  usuario_id como filtro, así un estudiante nunca puede leer ni
  modificar el progreso, chat o materiales de otro.
"""

import sqlite3
import hashlib
import os
import secrets
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "adivina_estudio.db")

PBKDF2_ITERACIONES = 260_000


def _hash_password(password: str, sal: str | None = None) -> tuple[str, str]:
    """Genera (hash, sal). Si no se da sal, crea una aleatoria nueva."""
    sal = sal or secrets.token_hex(16)
    derivado = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), sal.encode("utf-8"), PBKDF2_ITERACIONES
    )
    return derivado.hex(), sal


def _verificar_password(password: str, hash_guardado: str, sal: str) -> bool:
    calculado, _ = _hash_password(password, sal)
    return secrets.compare_digest(calculado, hash_guardado)


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Crea las tablas si no existen. Llamar una vez al iniciar la app."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_usuario TEXT UNIQUE NOT NULL,
                correo TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                password_sal TEXT NOT NULL,
                puntos INTEGER NOT NULL DEFAULT 0,
                materia_preferida TEXT DEFAULT 'General',
                fecha_registro TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historial_adivinanzas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                adivinanza_id TEXT NOT NULL,
                acerto INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historial_chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                materia TEXT NOT NULL,
                rol TEXT NOT NULL,
                mensaje TEXT NOT NULL,
                fuentes TEXT DEFAULT '',
                fecha TEXT NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS materiales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                materia TEXT NOT NULL,
                titulo TEXT NOT NULL,
                contenido TEXT NOT NULL,
                fecha TEXT NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
            """
        )
        # Migración suave: si la base ya existía sin las columnas nuevas.
        columnas_usuarios = {f["name"] for f in conn.execute("PRAGMA table_info(usuarios)")}
        if "password_sal" not in columnas_usuarios:
            conn.execute("ALTER TABLE usuarios ADD COLUMN password_sal TEXT NOT NULL DEFAULT ''")
        columnas_chat = {f["name"] for f in conn.execute("PRAGMA table_info(historial_chat)")}
        if "fuentes" not in columnas_chat:
            conn.execute("ALTER TABLE historial_chat ADD COLUMN fuentes TEXT DEFAULT ''")


# --------------------------------------------------------------------
# Usuarios
# --------------------------------------------------------------------
def crear_usuario(nombre_usuario: str, correo: str, password: str) -> tuple[bool, str]:
    hash_pw, sal = _hash_password(password)
    try:
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO usuarios
                   (nombre_usuario, correo, password_hash, password_sal, fecha_registro)
                   VALUES (?, ?, ?, ?, ?)""",
                (nombre_usuario, correo, hash_pw, sal, datetime.now().isoformat()),
            )
        return True, "Cuenta creada con éxito."
    except sqlite3.IntegrityError:
        return False, "El usuario o correo ya existe."


def validar_login(nombre_usuario: str, password: str):
    with get_connection() as conn:
        fila = conn.execute(
            "SELECT * FROM usuarios WHERE nombre_usuario = ?", (nombre_usuario,)
        ).fetchone()
    if fila is None:
        return None
    if not _verificar_password(password, fila["password_hash"], fila["password_sal"]):
        return None
    return dict(fila)


def obtener_usuario(usuario_id: int):
    with get_connection() as conn:
        fila = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return dict(fila) if fila else None


def actualizar_preferencia(usuario_id: int, materia: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET materia_preferida = ? WHERE id = ?", (materia, usuario_id)
        )


def sumar_puntos(usuario_id: int, puntos: int):
    with get_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET puntos = puntos + ? WHERE id = ?", (puntos, usuario_id)
        )


def tabla_posiciones(limite: int = 10):
    with get_connection() as conn:
        filas = conn.execute(
            "SELECT nombre_usuario, puntos FROM usuarios ORDER BY puntos DESC LIMIT ?",
            (limite,),
        ).fetchall()
    return [dict(f) for f in filas]


# --------------------------------------------------------------------
# Adivinanzas / misiones
# --------------------------------------------------------------------
def registrar_intento_adivinanza(usuario_id: int, adivinanza_id: str, acerto: bool):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO historial_adivinanzas (usuario_id, adivinanza_id, acerto, fecha)
               VALUES (?, ?, ?, ?)""",
            (usuario_id, adivinanza_id, int(acerto), datetime.now().isoformat()),
        )


def adivinanzas_resueltas(usuario_id: int) -> set:
    with get_connection() as conn:
        filas = conn.execute(
            """SELECT DISTINCT adivinanza_id FROM historial_adivinanzas
               WHERE usuario_id = ? AND acerto = 1""",
            (usuario_id,),
        ).fetchall()
    return {f["adivinanza_id"] for f in filas}


# --------------------------------------------------------------------
# Chat / Ghostie
# --------------------------------------------------------------------
def guardar_mensaje_chat(usuario_id: int, materia: str, rol: str, mensaje: str, fuentes: str = ""):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO historial_chat (usuario_id, materia, rol, mensaje, fuentes, fecha)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (usuario_id, materia, rol, mensaje, fuentes, datetime.now().isoformat()),
        )


def obtener_historial_chat(usuario_id: int, materia: str, limite: int = 30):
    with get_connection() as conn:
        filas = conn.execute(
            """SELECT rol, mensaje, fuentes FROM historial_chat
               WHERE usuario_id = ? AND materia = ?
               ORDER BY id ASC LIMIT ?""",
            (usuario_id, materia, limite),
        ).fetchall()
    return [dict(f) for f in filas]


# --------------------------------------------------------------------
# Biblioteca de materiales (propios del estudiante)
# --------------------------------------------------------------------
def guardar_material(usuario_id: int, materia: str, titulo: str, contenido: str):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO materiales (usuario_id, materia, titulo, contenido, fecha)
               VALUES (?, ?, ?, ?, ?)""",
            (usuario_id, materia, titulo, contenido, datetime.now().isoformat()),
        )


def listar_materiales(usuario_id: int, materia: str | None = None):
    with get_connection() as conn:
        if materia:
            filas = conn.execute(
                """SELECT id, materia, titulo, fecha, length(contenido) AS tamano
                   FROM materiales WHERE usuario_id = ? AND materia = ?
                   ORDER BY id DESC""",
                (usuario_id, materia),
            ).fetchall()
        else:
            filas = conn.execute(
                """SELECT id, materia, titulo, fecha, length(contenido) AS tamano
                   FROM materiales WHERE usuario_id = ? ORDER BY id DESC""",
                (usuario_id,),
            ).fetchall()
    return [dict(f) for f in filas]


def eliminar_material(usuario_id: int, material_id: int):
    """Borra un material solo si pertenece al usuario que lo pide."""
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM materiales WHERE id = ? AND usuario_id = ?",
            (material_id, usuario_id),
        )


def buscar_materiales_relevantes(usuario_id: int, materia: str, limite: int = 3):
    """Devuelve los materiales de esa materia para usarlos como contexto
    prioritario en el chat de Ghostie. Siempre acotado al propio usuario."""
    with get_connection() as conn:
        filas = conn.execute(
            """SELECT titulo, contenido FROM materiales
               WHERE usuario_id = ? AND materia = ?
               ORDER BY id DESC LIMIT ?""",
            (usuario_id, materia, limite),
        ).fetchall()
    return [dict(f) for f in filas]


# --------------------------------------------------------------------
# Progreso por misión (materia)
# --------------------------------------------------------------------
def progreso_por_materia(usuario_id: int, materia: str, total_adivinanzas: int) -> dict:
    with get_connection() as conn:
        resueltas = conn.execute(
            """SELECT COUNT(DISTINCT adivinanza_id) AS n FROM historial_adivinanzas
               WHERE usuario_id = ? AND acerto = 1 AND adivinanza_id LIKE ?""",
            (usuario_id, _prefijo_materia(materia)),
        ).fetchone()["n"]
    porcentaje = int(round(100 * resueltas / total_adivinanzas)) if total_adivinanzas else 0
    return {"resueltas": resueltas, "total": total_adivinanzas, "porcentaje": min(porcentaje, 100)}


def _prefijo_materia(materia: str) -> str:
    # Los ids de riddles.py usan un prefijo de 3 letras por materia (cie_, mat_, len_, his_...)
    mapa = {
        "Ciencias": "cie_%", "Matemáticas": "mat_%", "Lenguaje": "len_%",
        "Historia": "his_%",
    }
    return mapa.get(materia, "%")
