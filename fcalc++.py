import re
import streamlit as st
import pint
import sympy as sp

# Configuración de la página
st.set_page_config(page_title="Calculadora Física con Unidades", layout="wide")

# --- 1. CSS PARA AUMENTAR EL TAMAÑO DE FUENTE GLOBAL ---
st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-size: 18px !important;
        }
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
            font-size: 18px !important;
        }
        label p {
            font-size: 17px !important;
            font-weight: 600 !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 2.4rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# Inicializar el registro de unidades de Pint
@st.cache_resource
def get_unit_registry():
    ureg = pint.UnitRegistry()
    ureg.formatter.default_format = "~P"
    return ureg

ureg = get_unit_registry()

import math
import numpy as np

# Diccionario de constantes matemáticas y físicas (usando Pint)
CONSTANTES_PRECARGADAS = {
    # Matemáticas (aceptamos con y sin barra invertida para mayor comodidad)
    "\\pi": math.pi * ureg.dimensionless,
    "pi": math.pi * ureg.dimensionless,
    "e": math.e * ureg.dimensionless,
    
    # Físicas (Pint las trae definidas con sus unidades exactas)
    "c": 1 * ureg.speed_of_light,               # Velocidad de la luz (m/s)
    "h": 1 * ureg.planck_constant,              # Constante de Planck (J*s)
    "\\hbar": 1 * ureg.hbar,                    # Constante de Planck reducida (J*s)
    "G": 1 * ureg.newtonian_constant_of_gravitation, # Gravitación universal
    "g_0": 1 * ureg.standard_gravity,           # Gravedad estándar (9.80665 m/s^2)
    "R": 1 * ureg.molar_gas_constant,           # Constante de gases ideales (J/(mol*K))
    "N_A": 1 * ureg.avogadro_number,            # Número de Avogadro (1/mol)
    "k_B": 1 * ureg.boltzmann_constant,         # Constante de Boltzmann (J/K)
    "e_c": 1 * ureg.elementary_charge,          # Carga elemental (C)
    "m_e": 1 * ureg.electron_mass,              # Masa del electrón (kg)
    "m_p": 1 * ureg.proton_mass,                # Masa del protón (kg)
    "\\varepsilon_0": 1 * ureg.vacuum_permittivity, # Permitividad del vacío
    "\\mu_0": 1 * ureg.vacuum_permeability,     # Permeabilidad del vacío
    "\\sigma": 1 * ureg.stefan_boltzmann_constant # Constante de Stefan-Boltzmann
}


# Diccionario de magnitudes y unidades (SI siempre primero)
MAGNITUDES = {
    "Adimensional": ["dimensionless"],
    "Longitud": ["m", "cm", "mm", "km", "in", "ft", "yd", "mi"],
    "Tiempo": ["s", "ms", "min", "h", "day"],
    "Masa": ["kg", "g", "mg", "ton", "lb", "oz"],
    "Temperatura": ["K", "degC", "degF"],
    "Presión": ["Pa", "kPa", "MPa", "bar", "atm", "psi", "mmHg"],
    "Velocidad": ["m/s", "km/h", "ft/s", "mph", "knot"],
    "Fuerza": ["N", "kN", "lbf", "dyn"],
    "Energía": ["J", "kJ", "cal", "kcal", "Wh", "kWh", "BTU"],
    "Potencia": ["W", "kW", "MW", "hp"],
    "Área": ["m**2", "cm**2", "mm**2", "km**2", "ft**2", "in**2"],
    "Volumen": ["m**3", "L", "mL", "cm**3", "ft**3", "gal"]
}

if "resultado_calculado" not in st.session_state:
    st.session_state.resultado_calculado = None

st.title("🧮 Evaluador de Fórmulas con Unidades")
st.markdown("Define tus parámetros en LaTeX, evalúa la expresión y convierte el resultado al instante.")

# --- SELECCIÓN DE CANTIDAD DE PARÁMETROS ---
num_params = st.selectbox(
    "¿Cuántos parámetros contiene la expresión?",
    options=list(range(1, 11)),
    index=1
)

st.divider()
st.subheader("1. Definición de Parámetros")

parametros_definidos = {}
etiquetas_repetidas = False

for i in range(num_params):
    with st.container(border=True):
        col_lat, col_prev, col_val, col_mag, col_uni = st.columns([2, 1.2, 1.3, 1.5, 1.5])
        
        with col_lat:
            latex_label = st.text_input(
                "Etiqueta LaTeX (usar igual en fórmula)", 
                value=f"x_{{{i+1}}}" if i > 0 else "\\rho", 
                key=f"lat_{i}",
                help="Escribe el símbolo tal como lo usarás en la fórmula (ej: \\rho, v_0, \\Delta P)"
            ).strip()
            
        with col_prev:
            st.caption("Vista previa:")
            if latex_label:
                st.latex(latex_label)
                
        with col_val:
            valor = st.number_input(
                "Valor numérico", 
                value=1.0, 
                format="%.4f", 
                key=f"val_{i}"
            )
            
        with col_mag:
            magnitud = st.selectbox(
                "Tipo de magnitud", 
                options=list(MAGNITUDES.keys()), 
                key=f"mag_{i}"
            )
            
        with col_uni:
            unidad = st.selectbox(
                "Unidad", 
                options=MAGNITUDES[magnitud], 
                key=f"uni_{i}"
            )

        if latex_label:
            if latex_label in parametros_definidos:
                st.error(f"La etiqueta '{latex_label}' está duplicada.")
                etiquetas_repetidas = True
            else:
                if unidad in ["degC", "degF"]:
                    parametros_definidos[latex_label] = ureg.Quantity(valor, ureg(unidad))
                else:
                    parametros_definidos[latex_label] = valor * ureg(unidad)

st.divider()

# --- 2. EVALUACIÓN DE LA FÓRMULA ---
st.subheader("2. Evaluación de la Fórmula")

# Mostrar catálogo de constantes disponibles al usuario
with st.expander("📚 Ver constantes matemáticas y físicas disponibles para usar directo en la fórmula"):
    col_m, col_f = st.columns(2)
    with col_m:
        st.markdown("**Matemáticas y Funciones:**")
        st.markdown("- `pi` o `\\pi` ($\\approx 3.14159$)")
        st.markdown("- `e` ($\\approx 2.71828$)")
        st.markdown("- `sqrt(x)` (ej. `sqrt(2)`, `sqrt(9.8 * h)`)")
        st.markdown("- `sin(x)`, `cos(x)`, `tan(x)`, `log(x)`, `exp(x)`")
    with col_f:
        st.markdown("**Constantes Físicas (con unidades):**")
        st.markdown("""
        - `c`: Velocidad de la luz ($2.998 \\times 10^8\\text{ m/s}$)
        - `h` / `\\hbar`: Constante de Planck ($\\text{J}\\cdot\\text{s}$)
        - `G`: Gravitación universal ($\\text{m}^3/(\\text{kg}\\cdot\\text{s}^2)$)
        - `g_0`: Gravedad estándar ($9.80665\\text{ m/s}^2$)
        - `R`: Gases ideales ($8.314\\text{ J/(mol}\\cdot\\text{K)}$)
        - `N_A`: Avogadro ($6.022 \\times 10^{23}\\text{ 1/mol}$)
        - `k_B`: Boltzmann ($1.38 \\times 10^{-23}\\text{ J/K}$)
        - `e_c`: Carga elemental ($1.602 \\times 10^{-19}\\text{ C}$)
        - `m_e` / `m_p`: Masa electrón / protón ($\\text{kg}$)
        - `\\varepsilon_0` / `\\mu_0`: Permitividad / Permeabilidad vacío
        - `\\sigma`: Stefan-Boltzmann ($\\text{W/(m}^2\\cdot\\text{K}^4)$)
        """)

etiquetas_lista = list(parametros_definidos.keys())
ejemplo_formula = " * ".join(etiquetas_lista) if etiquetas_lista else "\\rho * x_{2}"

formula_str = st.text_input(
    "Ingresa la fórmula usando tus etiquetas LaTeX, números o constantes precargadas:",
    value=ejemplo_formula,
    help="Ejemplo: 0.5 * m_e * c**2 + sqrt(2) * \\pi"
)

def formatear_formula_latex(formula: str) -> str:
    latex_expr = formula.strip()
    if not latex_expr:
        return ""
    latex_expr = re.sub(r"\*\*\s*\{([^}]+)\}", r"^{\1}", latex_expr)
    latex_expr = re.sub(r"\*\*\s*\(([^)]+)\)", r"^{\1}", latex_expr)
    latex_expr = re.sub(r"\*\*\s*([a-zA-Z0-9_.-]+)", r"^{\1}", latex_expr)
    latex_expr = latex_expr.replace("*", r" \cdot ")
    # Formateo visual básico para sqrt() en la vista previa
    latex_expr = re.sub(r"sqrt\(([^)]+)\)", r"\\sqrt{\1}", latex_expr)
    return latex_expr

vista_formula = formatear_formula_latex(formula_str)
if vista_formula:
    st.caption("Vista previa de la fórmula:")
    st.latex(vista_formula)

def evaluar_expresion_latex(formula, params_dict):
    formula_procesada = formula
    mapa_tokens = {}
    
    # 1. Combinamos constantes precargadas + parámetros del usuario.
    # Al hacer .update(params_dict) al final, los parámetros del usuario tienen prioridad
    # si llegan a usar la misma letra (ej: 'R' como radio en lugar de constante de gases).
    diccionario_completo = CONSTANTES_PRECARGADAS.copy()
    diccionario_completo.update(params_dict)
    
    # 2. Ordenamos de mayor a menor longitud para evitar reemplazos parciales
    # (ej: reemplazar 'N_A' antes que 'N', o '\pi' antes que 'pi')
    etiquetas_ordenadas = sorted(diccionario_completo.keys(), key=len, reverse=True)
    
    for idx, etiqueta in enumerate(etiquetas_ordenadas):
        token = f"__VAR_{idx}__"
        # Si la etiqueta es alfanumérica pura (ej: 'c', 'h', 'R', 'e', 'pi'), 
        # usamos límites de palabra (\b) para NO romper palabras como 'cos', 'exp', 'sqrt'
        if re.match(r"^[a-zA-Z0-9_]+$", etiqueta):
            patron = r"\b" + re.escape(etiqueta) + r"\b"
            if re.search(patron, formula_procesada):
                formula_procesada = re.sub(patron, token, formula_procesada)
                mapa_tokens[token] = diccionario_completo[etiqueta]
        else:
            # Para etiquetas con barras LaTeX o llaves (ej: '\rho', '\pi', 'x_{1}')
            if etiqueta in formula_procesada:
                formula_procesada = formula_procesada.replace(etiqueta, token)
                mapa_tokens[token] = diccionario_completo[etiqueta]
            
    expr = sp.sympify(formula_procesada)
    
    # Usamos numpy para funciones matemáticas porque opera nativamente con Pint Quantities
    # (ej: np.sqrt(4 * m**2) -> 2 * m)
    entorno = {
        "sqrt": np.sqrt,
        "sin": np.sin,
        "cos": np.cos,
        "tan": np.tan,
        "log": np.log,
        "exp": np.exp,
    }
    entorno.update(mapa_tokens)
    
    simbolos_expr = list(expr.free_symbols)
    func = sp.lambdify(simbolos_expr, expr, modules=[entorno, "numpy"])
    
    args = []
    for s in simbolos_expr:
        nombre_s = str(s)
        if nombre_s not in mapa_tokens:
            raise ValueError(f"Símbolo no reconocido en la fórmula: '{nombre_s}'. Revisa tus etiquetas o constantes disponibles.")
        args.append(mapa_tokens[nombre_s])
        
    res = func(*args)
    if not hasattr(res, "to"):
        res = res * ureg.dimensionless
    return res.to_base_units()


if st.button("Calcular Resultado", type="primary", disabled=etiquetas_repetidas):
    if not formula_str.strip():
        st.warning("Por favor ingresa una fórmula.")
    else:
        try:
            st.session_state.resultado_calculado = evaluar_expresion_latex(formula_str, parametros_definidos)
        except Exception as e:
            st.session_state.resultado_calculado = None
            st.error(f"❌ **Error al evaluar la fórmula:** {e}")

# --- 3. RESULTADO Y CONVERSIÓN DINÁMICA DE UNIDADES ---
if st.session_state.resultado_calculado is not None:
    res_base = st.session_state.resultado_calculado
    
    st.divider()
    st.subheader("3. Resultado y Conversión de Unidades")
    
    unidades_compatibles = []
    for lista_u in MAGNITUDES.values():
        for u_cand in lista_u:
            try:
                if res_base.is_compatible_with(ureg(u_cand)):
                    unidades_compatibles.append(u_cand)
            except Exception:
                pass
                
    if not unidades_compatibles:
        opciones_salida = [str(res_base.units)]
    else:
        opciones_salida = unidades_compatibles

    col_res, col_conv = st.columns([2, 1.5])
    
    with col_conv:
        unidad_elegida = st.selectbox(
            "Cambiar unidad de salida:",
            options=opciones_salida,
            index=0
        )
        
    with col_res:
        try:
            res_convertido = res_base.to(unidad_elegida)
            st.metric(
                label="Valor Calculado",
                value=f"{res_convertido.magnitude:.6g} {res_convertido.units:~P}"
            )
        except Exception as e:
            st.error(f"No se pudo convertir a {unidad_elegida}: {e}")

