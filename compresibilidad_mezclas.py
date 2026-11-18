import streamlit as st
import CoolProp.CoolProp as CP
import plotly.graph_objects as go
import numpy as np

# Configuración de la página
st.set_page_config(page_title="Simulador Termodinámico Dual", layout="wide")
st.title("📊 Simulador Termodinámico Avanzado de Alcanos")

# Constantes de conversión y condiciones estándar (1 atm, 15 °C)
PA_TO_ATM = 101325.0
PA_TO_PSI = 6894.75729
R = 8.314462618  # J/(mol*K)
T_STD = 288.15   # K (15 °C)
P_STD = 101325.0 # Pa (1 atm)
V_MOLAR_STD = (R * T_STD) / P_STD  # ~0.023645 m³/mol

# --- DICCIONARIO GLOBAL DE MAPEO DE FASES ---
MAPEO_FASES = {
    CP.iphase_gas: {"nombre": "Gas / Vapor", "color": "#2ca02c"},
    CP.iphase_liquid: {"nombre": "Líquido", "color": "#1f77b4"},
    CP.iphase_twophase: {"nombre": "Bifásico (L+V)", "color": "#ff7f0e"},
    CP.iphase_supercritical: {"nombre": "Supercrítico", "color": "#9467bd"},
    CP.iphase_supercritical_gas: {"nombre": "Gas Supercrítico", "color": "#bcbd22"},
    CP.iphase_supercritical_liquid: {"nombre": "Líquido Supercrítico", "color": "#17becf"},
    CP.iphase_critical_point: {"nombre": "Punto Crítico", "color": "#d62728"}
}

# --- BARRA LATERAL: CONFIGURACIÓN ---
st.sidebar.header("⚙️ Configuración del Sistema")

# 1. Selección de Modo de Simulación
modo = st.sidebar.radio("Selecciona el tipo de curva:", ["Isoterma (T Fija, P Variable)", "Isobara (P Fija, T Variable)"])

# 2. Selección de Especies
alcanos = ["Methane", "Ethane", "Propane", "n-Butane", "Isobutane", "n-Pentane"]
comp1 = st.sidebar.selectbox("Componente 1 (Obligatorio)", alcanos, index=0)
comp2 = st.sidebar.selectbox("Componente 2 (Opcional)", ["None"] + alcanos, index=0)
comp3 = st.sidebar.selectbox("Componente 3 (Opcional)", ["None"] + alcanos, index=0)

componentes_activos = [comp1]
if comp2 != "None": componentes_activos.append(comp2)
if comp3 != "None": componentes_activos.append(comp3)

if len(componentes_activos) != len(set(componentes_activos)):
    st.sidebar.error("❌ Por favor, elimina los componentes duplicados.")
    st.stop()

# 3. Fracciones Molares
num_gases = len(componentes_activos)
fracciones = []

if num_gases == 1:
    st.sidebar.markdown(f"**Composición:** 100% `{comp1}` (Gas Puro)")
    fracciones = [1.0]
elif num_gases == 2:
    st.sidebar.subheader("🧪 Fracciones Molares")
    x1 = st.sidebar.slider(f"Fracción molar {comp1} (x₁)", 0.0, 1.0, 0.5, step=0.01)
    x2 = round(1.0 - x1, 2)
    st.sidebar.info(f"🧬 **Mezcla Binaria:**\n* {comp1}: {x1*100:.1f}%\n* {comp2}: {x2*100:.1f}%")
    fracciones = [x1, x2]
elif num_gases == 3:
    st.sidebar.subheader("🧪 Fracciones Molares")
    x1 = st.sidebar.slider(f"Fracción molar {comp1} (x₁)", 0.0, 1.0, 0.4, step=0.01)
    max_x2 = round(1.0 - x1, 2)
    x2 = st.sidebar.slider(f"Fracción molar {comp2} (x₂)", 0.0, max_x2, min(0.3, max_x2), step=0.01)
    x3 = round(1.0 - x1 - x2, 2)
    st.sidebar.info(f"🧬 **Mezcla Ternaria:**\n* {comp1}: {x1*100:.1f}%\n* {comp2}: {x2*100:.1f}%\n* {comp3}: {x3*100:.1f}%")
    fracciones = [x1, x2, x3]

# 4. Unidades y Visualización
unidad_presion = st.sidebar.radio("Unidad de Trabajo para Presión:", ["atm", "psi"])
font_size = st.sidebar.slider("Tamaño de Fuente Gráficos", 10, 24, 14)
unidad_densidad = st.sidebar.radio("Selecciona unidad de densidad:", ["Masa (kg/m³)", "Molar (mol/L)"])

# 5. Configuración Consistente de T y P según el Modo
st.sidebar.subheader("📈 Variables de Control")

if modo == "Isoterma (T Fija, P Variable)":
    t_fija = st.sidebar.number_input("Temperatura Absoluta Fija (K)", min_value=100.0, max_value=1000.0, value=300.0, step=10.0)
    if unidad_presion == "atm":
        p_min, p_max = st.sidebar.slider("Rango de Presión (atm)", 0.1, 400.0, (1.0, 100.0), step=1.0)
        rango_p_pa = np.linspace(p_min * PA_TO_ATM, p_max * PA_TO_ATM, 200)
    else:
        p_min, p_max = st.sidebar.slider("Rango de Presión (psi)", 1.0, 3500.0, (15.0, 1500.0), step=10.0)
        rango_p_pa = np.linspace(p_min * PA_TO_PSI, p_max * PA_TO_PSI, 200)
    
    valores_bucle = [(p, t_fija) for p in rango_p_pa]
    eje_x_nombre = f"Presión ({unidad_presion})"
else:
    if unidad_presion == "atm":
        p_fija_usr = st.sidebar.number_input("Presión Fija (atm)", min_value=0.1, max_value=250.0, value=1.0, step=1.0)
        p_fija_pa = p_fija_usr * PA_TO_ATM
    else:
        p_fija_usr = st.sidebar.number_input("Presión Fija (psi)", min_value=1.0, max_value=3500.0, value=14.7, step=10.0)
        p_fija_pa = p_fija_usr * PA_TO_PSI
    t_min, t_max = st.sidebar.slider("Rango de Temperatura Absoluta (K)", 100.0, 1000.0, (200.0, 600.0), step=10.0)
    rango_t_k = np.linspace(t_min, t_max, 200)
    
    valores_bucle = [(p_fija_pa, t) for t in rango_t_k]
    eje_x_nombre = "Temperatura (K)"

# --- CÁLCULOS TERMODINÁMICOS DUALES ---
presiones_plot = []
temperaturas_plot = []
factores_z = []
densidades_plot = []
densidades_mmol_cm3 = []
fases_id = []
fases_nombres = []

# Configuración de fluidos
if num_gases > 1:
    string_fluidos = "HEOS::" + "&".join(componentes_activos)
else:
    string_fluidos = componentes_activos[0]  # String limpio ("Methane") para forzar ecuación pura

for p_pa, t_k in valores_bucle:
    try:
        # --- CASO 1: COMPONENTE PURO (Ecuación dedicada de máxima precisión NIST) ---
        if num_gases == 1:
            rho_molar = CP.PropsSI("Dmolar", "P", p_pa, "T", t_k, string_fluidos)
            if rho_molar <= 0: continue
            
            z = CP.PropsSI("Z", "P", p_pa, "T", t_k, string_fluidos)
            
            # Captura de fase segura para PropsSI puro
            try:
                id_fase = int(CP.PropsSI("phase", "P", p_pa, "T", t_k, string_fluidos))
            except:
                p_crit = CP.PropsSI("pcrit", string_fluidos)
                id_fase = CP.iphase_supercritical if p_pa > p_crit else CP.iphase_gas

            if unidad_densidad == "Masa (kg/m³)":
                rho_disp = CP.PropsSI("Dmass", "P", p_pa, "T", t_k, string_fluidos)
            else:
                rho_disp = rho_molar / 1000.0

        # --- CASO 2: MEZCLAS BINARIAS / TERNARIAS (Ecuación Helmholtz multifluido GERG) ---
        else:
            AS = CP.AbstractState("HEOS", string_fluidos)
            AS.set_mole_fractions(fracciones)
            AS.update(CP.PT_INPUTS, p_pa, t_k)
            
            rho_molar = AS.rhomolar()
            if rho_molar <= 0: continue
            
            z = p_pa / (rho_molar * R * t_k)
            id_fase = AS.phase()
            
            if unidad_densidad == "Masa (kg/m³)":
                rho_disp = AS.rhomass()
            else:
                rho_disp = rho_molar / 1000.0
        
        # --- PROCESAMIENTO COMÚN DE RESULTADOS ---
        info_fase = MAPEO_FASES.get(id_fase, {"nombre": "Supercrítico / No detectada", "color": "#7f7f7f"})
        p_disp = p_pa / PA_TO_ATM if unidad_presion == "atm" else p_pa / PA_TO_PSI
        rho_mmol_cm3 = rho_molar / 1000.0
        
        presiones_plot.append(p_disp)
        temperaturas_plot.append(t_k)
        factores_z.append(z)
        densidades_plot.append(rho_disp)
        densidades_mmol_cm3.append(rho_mmol_cm3)
        fases_id.append(id_fase)
        fases_nombres.append(info_fase["nombre"])
        
    except ValueError:
        continue


# --- ESTIMACIÓN DEL FACTOR DE VOLUMEN (B_g) EN EL EXTREMO DEL RANGO ---
factor_volumen_calculado = False
if len(densidades_plot) > 0:
    try:
        AS_extremo = CP.AbstractState(backend, string_fluidos)
        if num_gases > 1: AS_extremo.set_mole_fractions(fracciones)
        p_pa_extrema, t_k_extrema = valores_bucle[-1]
        AS_extremo.update(CP.PT_INPUTS, p_pa_extrema, t_k_extrema)
        
        v_molar_extremo = 1.0 / AS_extremo.rhomolar()
        p_extrema = presiones_plot[-1]
        t_extrema = temperaturas_plot[-1]
        fase_extrema = fases_nombres[-1]
        
        B_g = v_molar_extremo / V_MOLAR_STD
        factor_volumen_calculado = True
    except:
        factor_volumen_calculado = False

# --- RENDERIZADO GRÁFICOS ---
if len(factores_z) > 0:
    col1, col2 = st.columns(2)
    
    eje_x_data = presiones_plot if modo == "Isoterma (T Fija, P Variable)" else temperaturas_plot
    
    hover_textos_z = [f"Fase: {f}<br>P: {p:.2f} {unidad_presion}<br>T: {t:.1f} K<br>Z: {z:.4f}" 
                      for f, p, t, z in zip(fases_nombres, presiones_plot, temperaturas_plot, factores_z)]
    
    lbl_den = "kg/m³" if unidad_densidad == "Masa (kg/m³)" else "mol/L"
    hover_textos_d = [f"Fase: {f}<br>Densidad: {d:.3f} {lbl_den}<br>P: {p:.2f} {unidad_presion}<br>T: {t:.1f} K" 
                      for f, d, p, t in zip(fases_nombres, densidades_plot, presiones_plot, temperaturas_plot)]

    with col1:
        st.subheader("Factor de Compresibilidad (Z)")
        fig_z = go.Figure()
        
        fases_presentes_id = set(fases_id)
        for f_id, f_info in MAPEO_FASES.items():
            if f_id in fases_presentes_id:
                fig_z.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker=dict(size=8, color=f_info["color"]), name=f_info["nombre"]))
        
        fig_z.add_trace(go.Scatter(
            x=eje_x_data, y=factores_z, mode='lines+markers', text=hover_textos_z, hoverinfo='text', showlegend=False,
            line=dict(color='#888888', width=1.5),
            marker=dict(size=4, color=[MAPEO_FASES[fid]["color"] if fid in MAPEO_FASES else "#7f7f7f" for fid in fases_id])
        ))
        
        fig_z.update_layout(
            title="", xaxis_title=eje_x_nombre, yaxis_title="Factor de Compresibilidad Z", template="plotly_white",
            xaxis=dict(title_font=dict(size=font_size), tickfont=dict(size=font_size)),
            yaxis=dict(title_font=dict(size=font_size), tickfont=dict(size=font_size)),
            legend=dict(font=dict(size=font_size), title=dict(text="Fases", font=dict(size=font_size)))
        )
        st.plotly_chart(fig_z, use_container_width=True)

    with col2:
        fig_p = go.Figure()
        
        if modo == "Isoterma (T Fija, P Variable)":
            st.subheader("Isoterma de Presión vs Densidad")
            x_p_fig = densidades_plot
            y_p_fig = presiones_plot
            x_p_axis_title = f"Densidad ({lbl_den})"
            y_p_axis_title = f"Presión ({unidad_presion})"
            escala_x, escala_y = "linear", "linear"
        else:
            st.subheader("Efecto de la Temperatura sobre la Densidad")
            x_p_fig = temperaturas_plot
            y_p_fig = densidades_plot
            x_p_axis_title = "Temperatura (K)"
            y_p_axis_title = f"Densidad ({lbl_den})"
            escala_x, escala_y = "linear", "linear"
        
        fig_p.add_trace(go.Scatter(
            x=x_p_fig, y=y_p_fig, mode='lines+markers', text=hover_textos_d, hoverinfo='text', showlegend=False,
            line=dict(color='#888888', width=1.5),
            marker=dict(size=4, color=[MAPEO_FASES[fid]["color"] if fid in MAPEO_FASES else "#7f7f7f" for fid in fases_id])
        ))
        
        fig_p.update_layout(
            title="", xaxis_title=x_p_axis_title, yaxis_title=y_p_axis_title, template="plotly_white",
            xaxis_type=escala_x, yaxis_type=escala_y,
            xaxis=dict(title_font=dict(size=font_size), tickfont=dict(size=font_size)),
            yaxis=dict(title_font=dict(size=font_size), tickfont=dict(size=font_size)),
        )
        st.plotly_chart(fig_p, use_container_width=True)
        
    # --- NUEVO GRÁFICO 3: DENSIDAD MOLAR (mmol/cm³) VS VARIABLE DE CONTROL (PRESS O TEMP) ---
    st.markdown("---")
    st.subheader("📊 Perfil Específico: Densidad Molar (mmol/cm³)")
    
    hover_textos_d_mmol = [f"Fase: {f}<br>Densidad: {d:.4f} mmol/cm³<br>P: {p:.2f} {unidad_presion}<br>T: {t:.1f} K" 
                           for f, d, p, t in zip(fases_nombres, densidades_mmol_cm3, presiones_plot, temperaturas_plot)]
    
    fig_mmol = go.Figure()
    
    if modo == "Isoterma (T Fija, P Variable)":
        x_mmol = presiones_plot
        y_mmol = densidades_mmol_cm3
        y_axis_title = "Densidad Molar (mmol/cm³)"
    else:
        x_mmol = temperaturas_plot
        y_mmol = densidades_mmol_cm3
        y_axis_title = "Densidad Molar (mmol/cm³)"

    fig_mmol.add_trace(go.Scatter(
        x=x_mmol, y=y_mmol, mode='lines+markers', text=hover_textos_d_mmol, hoverinfo='text', showlegend=False,
        line=dict(color='#ff7f0e', width=1.5),
        marker=dict(size=4, color=[MAPEO_FASES[fid]["color"] if fid in MAPEO_FASES else "#7f7f7f" for fid in fases_id])
    ))
    
    fig_mmol.update_layout(
        xaxis_title=eje_x_nombre, yaxis_title=y_axis_title, template="plotly_white",
        xaxis=dict(title_font=dict(size=font_size), tickfont=dict(size=font_size)),
        yaxis=dict(title_font=dict(size=font_size), tickfont=dict(size=font_size)),
    )
    st.plotly_chart(fig_mmol, use_container_width=True)
    # --- IMPRESIÓN DE LA DENSIDAD MOLAR EN EL ÚLTIMO PUNTO DEL RANGO ---
    if len(densidades_mmol_cm3) > 0:
        st.markdown("---")
        st.subheader("🏁 Valor en el Extremo del Rango")
        
        ultimo_p = presiones_plot[-1]
        ultimo_t = temperaturas_plot[-1]
        ultima_rho_mmol = densidades_mmol_cm3[-1]
        
        # Formateamos el texto con exactamente dos decimales (.2f)
        st.info(
            f"📊 **Último punto calculado del barrido:**  \n"
            f"• Presión: `{ultimo_p:.2f} {unidad_presion}`  \n"
            f"• Temperatura: `{ultimo_t:.2f} K`  \n"
            f"• **Densidad Molar: {ultima_rho_mmol:.2f} mmol/cm³**"
        )

    # --- PANEL DE RESULTADOS INFERIOR ---
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        compo_str = " | ".join([f"{comp}: {frac*100:.1f}%" for comp, frac in zip(componentes_activos, fracciones)])
        st.info(f"🧬 **Composición Analizada:** {compo_str}")
        fases_str = ", ".join(sorted(list(set(fases_nombres))))
        st.success(f"📈 **Fases reales mapeadas en el rango:** {fases_str}")
        
    with c2:
        if factor_volumen_calculado:
            subcol1, subcol2 = st.columns(2)
            with subcol1:
                st.metric(
                    label="Factor de Volumen de la Mezcla (Bg)",
                    value=f"{B_g:.6f} m³/m³_std",
                    delta=f"P: {p_extrema:.1f} {unidad_presion} | T: {t_extrema:.1f} K",
                    delta_color="gray"
                )
            with subcol2:
                E_g = 1.0 / B_g if B_g > 0 else 0.0
                st.metric(
                    label="Rendimiento de Expansión (1/Bg)",
                    value=f"{E_g:.2f} m³_std / m³ in situ",
                    delta="Equivalente en superficie",
                    delta_color="normal"
                )
            st.caption(f"Fase detectada en las condiciones extremas: **{fase_extrema}**. Condición estándar de referencia: 1 atm, 15 °C.")
else:
    st.error("⚠️ CoolProp no pudo converger los estados estables en este rango. Ajustá los límites o cambia la composición.")

