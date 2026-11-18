import streamlit as st

st.set_page_config(page_title="Launcher de apps", page_icon="🚀", layout="wide")

# 1. Catálogo centralizado: agregá o editá tus apps acá
APPS = [
    {
        "nombre": "Pizarra LaTeX",
        "categoria": "Gráficas",
        "icono": "✍️",
        "descripcion": "Renderiza fórmulas LaTeX y permite agregar trazos a mano alzada.",
        "url": "https://pizarra-latex.streamlit.app/",
    },
    {
        "nombre": "Multiplot - MultiCSV",
        "categoria": "Gráficas",
        "icono": "📈",
        "descripcion": "Permite cargar y graficar múltiples dataset de diferentes csv.",
        "url": "https://multiplot-multicsv.streamlit.app/",
    },    
    {
        "nombre": "Graficador de Funciones 3D",
        "categoria": "Matemáticas",
        "icono": "🪡️",
        "descripcion": "Visualización interactiva de curvas paramétricas.",
        "url": "https://curvas-param.streamlit.app/",
    },
    {
        "nombre": "Compresibilidad - Mezclas",
        "categoria": "Física",
        "icono": "🏮️",
        "descripcion": "Computa la compresibilidad en mezclas de alcanos",
        "url": "https://compresibilidad-mezclas.streamlit.app/",
    },        
   
]

# 2. Encabezado y barra de búsqueda
st.title("🚀 Launcher de Aplicaciones")
st.write("Explorá las herramientas organizadas por área o filtrá por nombre.")

busqueda = st.text_input("🔍 Buscar aplicación...", placeholder="Ej: LaTeX, funciones, etc...")

# 3. Función para dibujar la grilla de tarjetas
def mostrar_tarjetas(lista_apps):
    if not lista_apps:
        st.info("No se encontraron aplicaciones que coincidan con tu búsqueda.")
        return

    columnas = st.columns(3)  # Muestra 3 tarjetas por fila
    for indice, app in enumerate(lista_apps):
        with columnas[indice % 3]:
            with st.container(border=True):
                st.subheader(f"{app['icono']} {app['nombre']}")
                st.caption(f"Categoría: **{app['categoria']}**")
                st.write(app["descripcion"])
                st.link_button("Abrir aplicación", app["url"], use_container_width=True)

# 4. Filtrado por texto y organización en pestañas
apps_filtradas = [
    app for app in APPS
    if busqueda.lower() in app["nombre"].lower() or busqueda.lower() in app["descripcion"].lower()
]

categorias = ["Todas", "Matemáticas", "Física", "Gráficas"]
pestanas = st.tabs(categorias)

for tab, cat in zip(pestanas, categorias):
    with tab:
        if cat == "Todas":
            mostrar_tarjetas(apps_filtradas)
        else:
            apps_cat = [a for a in apps_filtradas if a["categoria"] == cat]
            mostrar_tarjetas(apps_cat)

