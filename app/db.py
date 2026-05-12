import sqlite3, hashlib, os

DB_PATH = os.path.join(os.path.dirname(__file__), "portal_noc.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _hash(p):
    return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS roles (
            id      INTEGER PRIMARY KEY,
            nombre  TEXT UNIQUE NOT NULL,
            descripcion TEXT
        );
        CREATE TABLE IF NOT EXISTS usuarios (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre        TEXT,
            email         TEXT,
            rol           TEXT NOT NULL DEFAULT 'usuario',
            activo        INTEGER NOT NULL DEFAULT 1,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    roles = [
        ("administrador", "Control total"),
        ("operador",      "Importar, exportar y editar datos"),
        ("usuario",       "Solo visualizacion"),
    ]
    c.executemany("INSERT OR IGNORE INTO roles(nombre,descripcion) VALUES(?,?)", roles)
    users = [
        ("admin",     _hash("admin123"),  "Administrador ATP", "admin@atp.com",  "administrador"),
        ("operador1", _hash("noc123"),    "Operador NOC",      "noc@atp.com",    "operador"),
        ("viewer1",   _hash("ver123"),    "Usuario Viewer",    "viewer@atp.com", "usuario"),
    ]
    c.executemany("INSERT OR IGNORE INTO usuarios(username,password_hash,nombre,email,rol) VALUES(?,?,?,?,?)", users)
    conn.commit()
    conn.close()

def verificar_usuario(username, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE username=? AND password_hash=? AND activo=1",
              (username.lower().strip(), _hash(password)))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def listar_usuarios():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id,username,nombre,email,rol,activo,created_at FROM usuarios ORDER BY id")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def crear_usuario(username, password, nombre, email, rol):
    conn = get_conn()
    try:
        conn.execute("INSERT INTO usuarios(username,password_hash,nombre,email,rol) VALUES(?,?,?,?,?)",
                     (username.lower().strip(), _hash(password), nombre, email, rol))
        conn.commit()
        return True, "Usuario creado correctamente."
    except sqlite3.IntegrityError:
        return False, "El nombre de usuario ya existe."
    finally:
        conn.close()

def actualizar_usuario(uid, nombre, email, rol, activo):
    conn = get_conn()
    conn.execute("UPDATE usuarios SET nombre=?,email=?,rol=?,activo=? WHERE id=?",
                 (nombre, email, rol, activo, uid))
    conn.commit()
    conn.close()

def cambiar_password(uid, nueva):
    conn = get_conn()
    conn.execute("UPDATE usuarios SET password_hash=? WHERE id=?", (_hash(nueva), uid))
    conn.commit()
    conn.close()

def eliminar_usuario(uid):
    conn = get_conn()
    conn.execute("DELETE FROM usuarios WHERE id=?", (uid,))
    conn.commit()
    conn.close()

init_db()
