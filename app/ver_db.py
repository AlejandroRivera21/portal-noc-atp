import db
users = db.listar_usuarios()
print("=== USUARIOS ===")
for u in users:
    print(u["id"], u["username"], u["nombre"], u["rol"], "activo:", u["activo"])

import sqlite3
conn = sqlite3.connect("portal_noc.db")
print("\n=== ROLES ===")
for r in conn.execute("SELECT * FROM roles"):
    print(r)
conn.close()
