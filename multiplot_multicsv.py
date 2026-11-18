import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

st.set_page_config(page_title="Dashboard de datos Pro", layout="wide")

if "dataframes" not in st.session_state:
    st.session_state.dataframes = {}

st.title("🚀 Dashboard de datos")

# --- 1. CARGA DE DATOS ---
with st.sidebar:
    st.header("1. Datos de Entrada")
    uploaded_files = st.file_uploader("Sube tus archivos", type=["csv", "dat", "txt"], accept_multiple_files=True)
    formato = st.radio("Formato:", ["CSV (Comas)", "DAT (Espacios/Tabs)"], index=0)
    separador = ',' if formato == "CSV (Comas)" else r'\s+'
    
    if uploaded_files:
        for f in uploaded_files:
            if f.name not in st.session_state.dataframes:
                try:
                    raw_content = f.read().decode('latin-1')
                    clean_content = raw_content.replace('\xa0', ' ')
                    f_clean = io.StringIO(clean_content)
                    df = pd.read_csv(f_clean, sep=separador, engine='python', 
                                     na_values=['-', 'NA', 'null'], comment='#', header=None)
                    
                    first_row_values = df.iloc[0].values
                    numeric_check = pd.to_numeric(first_row_values, errors='coerce')
                    
                    if pd.Series(numeric_check).notnull().sum() >= (len(first_row_values) / 2):
                        df.columns = [f"Col {i+1}" for i in range(len(df.columns))]
                    else:
                        df.columns = [str(c).strip() for c in df.iloc[0]]
                        df = df[1:].reset_index(drop=True)

                    df['archivo_origen'] = f.name
                    st.session_state.dataframes[f.name] = df
                except Exception as e:
                    st.error(f"Error en {f.name}: {e}")

    if st.session_state.dataframes:
        if st.button("🗑️ Borrar todo"):
            st.session_state.dataframes = {}
            st.rerun()

# --- 2. ESTILO GLOBAL ---
with st.sidebar:
    st.divider()
    st.header("2. Estilo Reporte")
    f1 = st.number_input("Fila 1 (columnas):", 0, 3, 1)
    f2 = st.number_input("Fila 2 (columnas):", 0, 3, 0)
    f3 = st.number_input("Fila 3 (columnas):", 0, 3, 0)
    layout_config = [f1, f2, f3]
    tema_reporte = st.selectbox("Tema Visual:", ["plotly_white", "plotly_dark", "ggplot2", "seaborn"], index=0)
    font_size = st.slider("Tamaño Fuente:", 10, 45, 18)
    g_line_width = st.slider("Ancho Global Línea:", 0.5, 8.0, 2.0, 0.5)

if not st.session_state.dataframes:
    st.info("Cargá archivos para comenzar.")
    st.stop()

# --- 3. CONFIGURACIÓN ---
st.header("🛠️ Configuración de Gráficos")
dataframes = st.session_state.dataframes
plot_configs = []
plot_counter = 1

def parse_range(txt):
    try: return [float(x.strip()) for x in txt.split(',')] if ',' in txt else None
    except: return None

for row_idx, n_cols in enumerate(layout_config):
    if n_cols == 0: continue
    ui_cols = st.columns(n_cols)
    for col_idx, col_ui in enumerate(ui_cols):
        with col_ui:
            p_idx = plot_counter
            with st.expander(f"Configurar Gráfico {p_idx}", expanded=True):
                p_title = st.text_input("Título:", f"Ensayo {p_idx}", key=f"t_{p_idx}")
                
                c_m1, c_m2, c_m3 = st.columns([1, 1, 1])
                with c_m1: p_mode = st.radio("Modo:", ["Líneas", "Histograma"], horizontal=True, key=f"m_{p_idx}")
                with c_m2: show_p = st.radio("Mostrar:", ["On", "Off"], horizontal=True, key=f"pvis_{p_idx}")
                with c_m3: show_leg = st.checkbox("Ver Leyenda", value=True, key=f"shl_{p_idx}")
                
                st.markdown("**Ejes y Leyenda:**")
                cl1, cl2 = st.columns([1, 1])
                with cl1: leg_pos = st.selectbox("Posición Leyenda:", ["Arriba", "Derecha", "Abajo"], key=f"lpos_{p_idx}")
                with cl2: bin_s = st.number_input("Bin Hist (0=auto):", 0.0, 100.0, 0.0, key=f"b_{p_idx}") if p_mode == "Histograma" else 0

                c_rx, c_ry1, c_ry2 = st.columns(3)
                with c_rx: xminmax = st.text_input("X Min, Max:", key=f"rx_{p_idx}", placeholder="ej: 0, 100")
                with c_ry1: y1minmax = st.text_input("Y1 Min, Max:", key=f"ry1_{p_idx}", placeholder="ej: -1, 1")
                with c_ry2: y2minmax = st.text_input("Y2 Min, Max:", key=f"ry2_{p_idx}", placeholder="ej: 0, 1000")

                s_files = st.multiselect("Archivos:", list(dataframes.keys()), key=f"ms_{p_idx}")
                
                x_col = None
                if s_files:
                    common = sorted(list(set.intersection(*[set(dataframes[f].columns) for f in s_files])))
                    x_col = st.selectbox("Eje X común:", common, key=f"x_{p_idx}")
                    
                    c_sx, c_sy1, c_sy2 = st.columns(3)
                    with c_sx: sx = st.radio("X escala", ["linear", "log"], horizontal=True, key=f"sx_{p_idx}")
                    with c_sy1: sy1 = st.radio("Y1 escala", ["linear", "log"], horizontal=True, key=f"sy1_{p_idx}")
                    with c_sy2: sy2 = st.radio("Y2 escala", ["linear", "log"], horizontal=True, key=f"sy2_{p_idx}")

                    lx = st.text_input("Eje X label:", "Eje X", key=f"lx_{p_idx}")
                    ly1 = st.text_input("Eje Y1 label:", "Principal", key=f"ly1_{p_idx}")
                    ly2 = st.text_input("Eje Y2 label:", "Secundario", key=f"ly2_{p_idx}")

                    series_setup = []
                    for fname in s_files:
                        n_s = st.number_input(f"Series en {fname}:", 1, 10, 1, key=f"ns_{p_idx}_{fname}")
                        for i in range(int(n_s)):
                            t_id = f"{p_idx}_{fname}_{i}"
                            st.markdown(f"--- Serie {i+1} ({fname})")
                            c1, c2, c3 = st.columns([2, 2, 1])
                            with c1: cy = st.selectbox("Col Y:", [c for c in dataframes[fname].columns if c != 'archivo_origen'], key=f"cy_{t_id}")
                            with c2: clbl = st.text_input("Etiqueta:", value=cy, key=f"lbl_{t_id}")
                            with c3: clr = st.color_picker("Color", "#1f77b4", key=f"clr_{t_id}")
                            
                            c4, c5, c6, c7 = st.columns(4)
                            with c4: dash = st.selectbox("Línea:", ["solid", "dash", "dot", "dashdot"], key=f"dash_{t_id}")
                            with c5: sm = st.selectbox("Símb:", ["none", "circle", "square", "diamond", "cross", "x"], key=f"sym_{t_id}")
                            with c6: sz = st.number_input("Tam:", 1, 40, 8, key=f"sz_{t_id}")
                            with c7: side = st.selectbox("Eje:", ["Izq", "Der"], key=f"side_{t_id}")
                            
                            series_setup.append({
                                'file': fname, 'y': cy, 'side': side, 'color': clr, 
                                'label': clbl, 'dash': dash, 'symbol': sm, 's_size': sz
                            })

                plot_configs.append({
                    'id': p_idx, 'title': p_title, 'row_idx': row_idx, 'col_idx': col_idx, 
                    'files': s_files, 'x': x_col, 'lx': lx if s_files else "X", 
                    'ly1': ly1 if s_files else "Y1", 'ly2': ly2 if s_files else "Y2", 
                    'series': series_setup if s_files else [], 'show': show_p, 'mode': p_mode, 
                    'bin_size': bin_s, 'sx': sx if s_files else "linear", 
                    'sy1': sy1 if s_files else "linear", 'sy2': sy2 if s_files else "linear",
                    'show_legend': show_leg, 'leg_pos': leg_pos,
                    'r_x': parse_range(xminmax), 'r_y1': parse_range(y1minmax), 'r_y2': parse_range(y2minmax)
                })
            plot_counter += 1

# --- 4. REPORTE FINAL ---
st.divider()
st.header("🖼️ Vista de Reporte")
active_plots = [p for p in plot_configs if p['files'] and p['show'] == "On"]

if active_plots:
    report_fig = go.Figure()
    rows_data = {}
    for p in active_plots: rows_data.setdefault(p['row_idx'], []).append(p)
    n_rows_total = len(rows_data)
    v_space, h_space = 0.25, 0.12 
    row_height = (1.0 - (v_space * (n_rows_total - 1))) / n_rows_total

    for r_count, (r_idx, plots_in_row) in enumerate(reversed(list(rows_data.items()))):
        n_plots = len(plots_in_row)
        plot_width = (1.0 - (h_space * (n_plots - 1))) / n_plots
        y_s, y_e = r_count * (row_height + v_space), (r_count * (row_height + v_space)) + row_height
        
        for p_count, p in enumerate(plots_in_row):
            x_s, x_e = p_count * (plot_width + h_space), (p_count * (plot_width + h_space)) + plot_width
            ax_id = p['id']
            xaxis_ref, yaxis_ref, yaxis_ref2 = f"x{ax_id}", f"y{ax_id}", f"y{ax_id + 50}"
            leg_ref = "legend" if ax_id == 1 else f"legend{ax_id}"

            for s in p['series']:
                y_vals = pd.to_numeric(dataframes[s['file']][s['y']], errors='coerce')
                is_der = (s['side'] == "Der")
                
                t_mode = "lines"
                m_dict = dict(size=s['s_size'])
                if s['symbol'] != "none":
                    t_mode = "lines+markers"
                    m_dict['symbol'] = s['symbol']

                trace_kwargs = {
                    "name": s['label'], "xaxis": xaxis_ref, 
                    "yaxis": yaxis_ref2 if is_der else yaxis_ref,
                    "showlegend": p['show_legend'], "legend": leg_ref 
                }

                if p['mode'] == "Histograma":
                    report_fig.add_trace(go.Histogram(
                        x=y_vals, marker=dict(color=s['color']),
                        opacity=0.7, xbins=dict(size=p['bin_size']) if p['bin_size'] > 0 else None,
                        **trace_kwargs
                    ))
                else:
                    report_fig.add_trace(go.Scatter(
                        x=dataframes[s['file']][p['x']], y=y_vals, mode=t_mode,
                        connectgaps=True, line=dict(color=s['color'], width=g_line_width, dash=s['dash']),
                        marker=m_dict, **trace_kwargs
                    ))

            l_coords = {
                "Arriba": dict(x=(x_s+x_e)/2, y=y_e+0.05, xanchor="center", yanchor="bottom", orientation="h"),
                "Derecha": dict(x=x_e+0.01, y=(y_s+y_e)/2, xanchor="left", yanchor="middle", orientation="v"),
                "Abajo": dict(x=(x_s+x_e)/2, y=y_s-0.15, xanchor="center", yanchor="top", orientation="h")
            }
            
            report_fig.layout[leg_ref] = dict(
                font=dict(size=font_size-4), bgcolor="rgba(0,0,0,0)",
                bordercolor="rgba(0,0,0,0)", **l_coords[p['leg_pos']]
            )

            f_style, tk_style = dict(size=font_size), dict(size=font_size-2)
            report_fig.layout[f"xaxis{ax_id}"] = dict(domain=[x_s, x_e], anchor=yaxis_ref, type=p['sx'], tickfont=tk_style, title=dict(text=p['lx'], font=f_style), range=p['r_x'])
            report_fig.layout[f"yaxis{ax_id}"] = dict(domain=[y_s, y_e], anchor=xaxis_ref, type=p['sy1'], tickfont=tk_style, title=dict(text=p['ly1'], font=f_style), range=p['r_y1'])
            report_fig.layout[f"yaxis{ax_id+50}"] = dict(domain=[y_s, y_e], anchor=xaxis_ref, type=p['sy2'], overlaying=yaxis_ref, side="right", showgrid=False, tickfont=tk_style, title=dict(text=p['ly2'], font=f_style), range=p['r_y2'])
            
            report_fig.add_annotation(dict(x=(x_s+x_e)/2, y=y_e, xref="paper", yref="paper", text=f"<b>{p['title']}</b>", showarrow=False, yshift=35, font=dict(size=font_size+4)))

    report_fig.update_layout(
        template=tema_reporte, height=580 + (n_rows_total * 350), 
        margin=dict(t=150, b=120, l=80, r=120), barmode='overlay'
    )
    
    st.plotly_chart(report_fig, use_container_width=True)
    st.download_button("📥 Descargar Reporte HTML", report_fig.to_html(include_plotlyjs='cdn'), "reporte.html", "text/html")

