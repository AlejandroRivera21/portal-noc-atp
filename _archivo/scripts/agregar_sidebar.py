"""
agregar_sidebar.py
Ejecutar desde: C:\repos\portal-noc\app
Agrega sidebar_comun() al inicio de render() en cada pagina.
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(BASE, "pages")

cambios = {
    "dashboard.py":         "sidebar_comun()",
    "alertas.py":           "sidebar_comun()",
    "reportes.py":          "sidebar_comun()",
    "historico_timeouts.py":"sidebar_comun(mostrar_timeouts=True)",
}

IMPORT_LINE = "from modules.styles import sidebar_comun"

for archivo, llamada in cambios.items():
    ruta = os.path.join(PAGES, archivo)
    if not os.path.exists(ruta):
        print(f"NO ENCONTRADO: {ruta}")
        continue

    with open(ruta, "r", encoding="utf-8") as f:
        content = f.read()

    # Si ya tiene el import, no duplicar
    if IMPORT_LINE in content:
        print(f"SKIP (ya tiene import): {archivo}")
    else:
        # Agregar import antes de "from modules.data_processor" o "def render"
        if "from modules.data_processor" in content:
            content = content.replace(
                "from modules.data_processor",
                f"{IMPORT_LINE}\nfrom modules.data_processor",
                1
            )
        elif "from modules.kibana_client" in content:
            content = content.replace(
                "from modules.kibana_client",
                f"{IMPORT_LINE}\nfrom modules.kibana_client",
                1
            )
        else:
            content = f"{IMPORT_LINE}\n\n" + content

    # Agregar llamada al inicio de render()
    if f"    {llamada}" in content:
        print(f"SKIP (ya tiene llamada): {archivo}")
        continue

    # Insertar justo despues de "def render():"
    target = "def render():\n"
    if target in content:
        content = content.replace(
            target,
            f"{target}    {llamada}\n",
            1
        )
        print(f"OK: {archivo} — agregado {llamada}")
    else:
        print(f"WARNING: No encontre 'def render():' en {archivo}")
        continue

    with open(ruta, "w", encoding="utf-8") as f:
        f.write(content)

print("\nListo. Reinicia Streamlit.")