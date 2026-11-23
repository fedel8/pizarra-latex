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

# Inicializar estado de sesión para guardar el resultado calculado
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

# --- CREACIÓN DINÁMICA DE PARÁMETROS (SIN x_1 EXTRA) ---
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

etiquetas_lista = list(parametros_definidos.keys())
ejemplo_formula = " * ".join(etiquetas_lista) if etiquetas_lista else "\\rho * x_{2}"

formula_str = st.text_input(
    "Ingresa la fórmula usando exactamente las cadenas LaTeX definidas arriba:",
    value=ejemplo_formula,
    help="Ejemplo: 0.5 * \\rho * v**2. Operadores: +, -, *, /, ** (potencia), sqrt(), sin(), cos(), pi"
)

# Función auxiliar para evaluar reemplazando cadenas LaTeX por tokens internos seguros
def evaluar_expresion_latex(formula, params_dict):
    formula_procesada = formula
    mapa_tokens = {}
    
    # Ordenar etiquetas de mayor a menor longitud para evitar reemplazos parciales
    # (ej. evitar que 'v' reemplace parte de 'v_0')
    etiquetas_ordenadas = sorted(params_dict.keys(), key=len, reverse=True)
    
    for idx, etiqueta in enumerate(etiquetas_ordenadas):
        token = f"__VAR_{idx}__"
        if etiqueta in formula_procesada:
            formula_procesada = formula_procesada.replace(etiqueta, token)
            mapa_tokens[token] = params_dict[etiqueta]
            
    # Parsear con SymPy
    expr = sp.sympify(formula_procesada)
    
    entorno = {
        "sqrt": lambda x: x**0.5,
        "sin": sp.sin,
        "cos": sp.cos,
        "tan": sp.tan,
        "pi": 3.141592653589793,
        "e": 2.718281828459045
    }
    entorno.update(mapa_tokens)
    
    simbolos_expr = list(expr.free_symbols)
    func = sp.lambdify(simbolos_expr, expr, modules=[entorno, "math"])
    
    args = []
    for s in simbolos_expr:
        nombre_s = str(s)
        if nombre_s not in mapa_tokens:
            raise ValueError(f"Símbolo no reconocido en la fórmula: '{nombre_s}'. Revisa que coincida con tus etiquetas LaTeX.")
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
    
    # Buscar todas las unidades compatibles en nuestro diccionario
    unidades_compatibles = []
    for lista_u in MAGNITUDES.values():
        for u_cand in lista_u:
            try:
                if res_base.is_compatible_with(ureg(u_cand)):
                    unidades_compatibles.append(u_cand)
            except Exception:
                pass
                
    # Asegurar que la unidad base actual esté incluida
    unidad_actual_str = f"{res_base.units:~P}"
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
