import io
import numpy as np
import plotly.graph_objects as go
import scipy.io.wavfile as wavfile
import streamlit as st

st.set_page_config(page_title="Sintetizador de Fourier", layout="wide")

st.title("Sintetizador Aditivo de Fourier")

# --- Parámetros en la barra lateral ---
st.sidebar.header("Parámetros de Síntesis")

tipo_senal = st.sidebar.selectbox(
    "Tipo de señal / timbre",
    [
        "Onda Cuadrada",
        "Onda Triangular",
        "Diente de Sierra",
        "Tipo Violín",
        "Tipo Piano",
        "Tipo Clarinete",
    ],
)

n_armonicos = st.sidebar.slider(
    "Número de armónicos (N)", min_value=1, max_value=60, value=8, step=1
)

f0 = st.sidebar.number_input(
    "Frecuencia fundamental f₀ (Hz)",
    min_value=50.0,
    max_value=2000.0,
    value=440.0,
    step=10.0,
)

duracion = st.sidebar.slider(
    "Duración del audio (s)", min_value=1.0, max_value=10.0, value=5.0, step=0.5
)

st.sidebar.divider()
st.sidebar.header("Normalización y Envolvente")

modo_norm = st.sidebar.radio(
    "Tipo de normalización (valor medio = 0)",
    options=[
        "Por pico (amplitud máx. = 1)",
        "Por RMS (volumen percibido parejo)",
    ],
    index=0,
)

usar_adsr = st.sidebar.radio(
    "Envolvente temporal ADSR",
    options=["Desactivada", "Activada"],
    index=0,
)

if usar_adsr == "Activada":
    with st.sidebar.expander("Ajustar tiempos ADSR", expanded=False):
        t_attack = st.slider("Attack (s)", 0.005, 1.0, 0.05, 0.005)
        t_decay = st.slider("Decay (s)", 0.01, 2.0, 0.15, 0.01)
        sustain_lvl = st.slider("Sustain (nivel 0–1)", 0.0, 1.0, 0.7, 0.05)
        t_release = st.slider("Release (s)", 0.01, 2.0, 0.25, 0.01)


# --- Definición de coeficientes de Fourier ---
def obtener_coeficientes(tipo: str, N: int):
    """Devuelve arrays con los índices k, coeficientes a_k (cos) y b_k (sen) para k = 1, ..., N."""
    k = np.arange(1, N + 1)
    a_k = np.zeros(N)
    b_k = np.zeros(N)

    if tipo == "Onda Cuadrada":
        impares = k % 2 == 1
        b_k[impares] = 4.0 / (np.pi * k[impares])

    elif tipo == "Onda Triangular":
        impares = k % 2 == 1
        signo = (-1.0) ** ((k[impares] - 1) // 2)
        b_k[impares] = 8.0 * signo / ((np.pi**2) * (k[impares] ** 2))

    elif tipo == "Diente de Sierra":
        b_k = 2.0 * ((-1.0) ** (k + 1)) / (np.pi * k)

    elif tipo == "Tipo Violín":
        b_k = (1.0 / k) * np.exp(-0.04 * (k - 1))
        if N >= 3:
            b_k[2] *= 1.3

    elif tipo == "Tipo Piano":
        b_k = np.exp(-0.35 * (k - 1)) / (k**0.8)
        a_k = 0.15 * np.exp(-0.5 * (k - 1))

    elif tipo == "Tipo Clarinete":
        for idx, ki in enumerate(k):
            if ki % 2 == 1:
                b_k[idx] = 1.0 / (ki**0.9)
            else:
                b_k[idx] = 0.08 / (ki**1.5)

    return k, a_k, b_k


# --- Señal "original" de referencia (valor medio = 0) ---
def senal_original_ac(tipo: str, t_arr: np.ndarray, freq0: float):
    """Define una señal periódica de referencia con valor medio 0."""
    fase = (freq0 * t_arr) % 1.0

    if tipo == "Onda Cuadrada":
        return np.where(fase < 0.5, 1.0, -1.0)

    elif tipo == "Onda Triangular":
        return 1.0 - 4.0 * np.abs(fase - 0.5)

    elif tipo == "Diente de Sierra":
        return 2.0 * fase - 1.0

    else:
        _, a_ref, b_ref = obtener_coeficientes(tipo, 250)
        k_ref = np.arange(1, 251)
        s_ref = np.zeros_like(t_arr)
        for idx, ki in enumerate(k_ref):
            if a_ref[idx] != 0.0:
                s_ref += a_ref[idx] * np.cos(2.0 * np.pi * ki * freq0 * t_arr)
            if b_ref[idx] != 0.0:
                s_ref += b_ref[idx] * np.sin(2.0 * np.pi * ki * freq0 * t_arr)
        max_ref = np.max(np.abs(s_ref))
        return s_ref / max_ref if max_ref > 0 else s_ref


def normalizar_senal(senal: np.ndarray, modo: str, rms_objetivo: float = 0.30) -> np.ndarray:
    """Normaliza una señal de media cero por pico o por valor RMS."""
    if modo.startswith("Por pico"):
        pico = np.max(np.abs(senal))
        return senal / pico if pico > 0 else senal
    else:
        rms = np.sqrt(np.mean(senal**2))
        if rms <= 0:
            return senal
        esc = rms_objetivo / rms
        senal_rms = senal * esc
        # Evita superar [-1, 1] si el pico queda alto (por ej., onda triangular con RMS objetivo alto)
        pico_rms = np.max(np.abs(senal_rms))
        if pico_rms > 1.0:
            senal_rms = senal_rms / pico_rms
        return senal_rms


# --- Envolvente temporal ADSR ---
def generar_envolvente_adsr(
    t_arr: np.ndarray,
    dur: float,
    att: float,
    dec: float,
    sus: float,
    rel: float,
) -> np.ndarray:
    """Construye una envolvente ADSR en [0, 1] a lo largo de la duración total."""
    env = np.zeros_like(t_arr)
    t_rel_start = max(0.0, dur - rel)

    ad_total = att + dec
    if ad_total > t_rel_start and t_rel_start > 0:
        escala = t_rel_start / ad_total
        att *= escala
        dec *= escala

    t_dec_end = att + dec

    m_att = t_arr < att
    if att > 0:
        env[m_att] = t_arr[m_att] / att

    m_dec = (t_arr >= att) & (t_arr < t_dec_end)
    if dec > 0:
        env[m_dec] = 1.0 - (1.0 - sus) * ((t_arr[m_dec] - att) / dec)

    m_sus = (t_arr >= t_dec_end) & (t_arr < t_rel_start)
    env[m_sus] = sus

    m_rel = t_arr >= t_rel_start
    if rel > 0:
        if t_rel_start >= t_dec_end:
            nivel_inicio_rel = sus
        elif dec > 0:
            nivel_inicio_rel = 1.0 - (1.0 - sus) * ((t_rel_start - att) / dec)
        else:
            nivel_inicio_rel = 1.0
        progreso_rel = np.clip((t_arr[m_rel] - t_rel_start) / rel, 0.0, 1.0)
        env[m_rel] = nivel_inicio_rel * (1.0 - progreso_rel)

    return env


# --- Síntesis ---
fs = 44100
t = np.linspace(0, duracion, int(fs * duracion), endpoint=False)

k, a_k, b_k = obtener_coeficientes(tipo_senal, n_armonicos)

fourier_ac = np.zeros_like(t)
for idx, ki in enumerate(k):
    if a_k[idx] != 0.0:
        fourier_ac += a_k[idx] * np.cos(2.0 * np.pi * ki * f0 * t)
    if b_k[idx] != 0.0:
        fourier_ac += b_k[idx] * np.sin(2.0 * np.pi * ki * f0 * t)

orig_ac = senal_original_ac(tipo_senal, t, f0)

# Para señales estándar conservamos la escala relativa de convergencia antes de normalizar
if tipo_senal not in ["Onda Cuadrada", "Onda Triangular", "Diente de Sierra"]:
    max_ref_global = np.max(np.abs(orig_ac))
    if max_ref_global > 0:
        fourier_ac = fourier_ac / max_ref_global

fourier_norm = normalizar_senal(fourier_ac, modo_norm)
orig_norm = normalizar_senal(orig_ac, modo_norm)

if usar_adsr == "Activada":
    envolvente = generar_envolvente_adsr(
        t, duracion, t_attack, t_decay, sustain_lvl, t_release
    )
else:
    envolvente = np.ones_like(t)

fourier_final = fourier_norm * envolvente
orig_final = orig_norm * envolvente

# --- Audio WAV ---
pico_audio = np.max(np.abs(fourier_final))
audio_ac = fourier_final / pico_audio if pico_audio > 1.0 else fourier_final
audio_pcm = np.int16(np.clip(audio_ac * 32767 * 0.9, -32768, 32767))

if usar_adsr == "Desactivada":
    fade_samples = int(0.005 * fs)
    if len(audio_pcm) > 2 * fade_samples:
        audio_pcm[:fade_samples] = np.int16(
            audio_pcm[:fade_samples] * np.linspace(0.0, 1.0, fade_samples)
        )
        audio_pcm[-fade_samples:] = np.int16(
            audio_pcm[-fade_samples:] * np.linspace(1.0, 0.0, fade_samples)
        )

buffer_wav = io.BytesIO()
wavfile.write(buffer_wav, fs, audio_pcm)
buffer_wav.seek(0)

# --- Interfaz principal ---
etiqueta_norm = "Pico" if modo_norm.startswith("Por pico") else "RMS"
rms_actual = float(np.sqrt(np.mean(fourier_final**2)))
pico_actual = float(np.max(np.abs(fourier_final)))

st.subheader(
    f"{tipo_senal} — N = {n_armonicos} armónicos | f₀ = {f0:.0f} Hz | Norm: {etiqueta_norm} | ADSR: {usar_adsr}"
)
st.audio(buffer_wav, format="audio/wav")
st.caption(f"Amplitud pico: {pico_actual:.2f} | Valor RMS: {rms_actual:.2f} | Valor medio: 0.00")

col_izq, col_der = st.columns([2, 1])

with col_izq:
    n_periodos = 4
    t_ventana = n_periodos / f0
    mask_t = t <= t_ventana

    fig_onda = go.Figure()
    fig_onda.add_trace(
        go.Scatter(
            x=t[mask_t] * 1000.0,
            y=orig_final[mask_t],
            mode="lines",
            name="Señal original",
            line=dict(color="#2ca02c", width=2, dash="dash"),
        )
    )
    fig_onda.add_trace(
        go.Scatter(
            x=t[mask_t] * 1000.0,
            y=fourier_final[mask_t],
            mode="lines",
            name=f"Aprox. Fourier (N={n_armonicos})",
            line=dict(color="#1f77b4", width=2.5),
        )
    )
    fig_onda.add_hline(
        y=0.0,
        line_dash="dot",
        line_color="gray",
        annotation_text="Valor medio = 0",
    )

    fig_onda.update_layout(
        title=f"Señal original vs. Aproximación de Fourier ({n_periodos} períodos)",
        xaxis_title="Tiempo (ms)",
        yaxis_title="Amplitud (valor medio = 0)",
        yaxis=dict(range=[-1.3, 1.3]),
        template="plotly_white",
        height=390,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_onda, use_container_width=True)

with col_der:
    magnitudes = np.sqrt(a_k**2 + b_k**2)
    max_mag = np.max(magnitudes) if len(magnitudes) > 0 else 1.0
    magnitudes_norm = magnitudes / max_mag if max_mag > 0 else magnitudes

    fig_esp = go.Figure()
    fig_esp.add_trace(
        go.Bar(
            x=k,
            y=magnitudes_norm,
            marker_color="#ff7f0e",
            name="|cₖ| normalizado",
        )
    )
    fig_esp.update_layout(
        title="Espectro de Armónicos (normalizado al mayor)",
        xaxis_title="Armónico k",
        yaxis_title="Amplitud relativa",
        template="plotly_white",
        height=390,
    )
    st.plotly_chart(fig_esp, use_container_width=True)

st.markdown("### Envolvente temporal a lo largo de la duración total")
fig_env = go.Figure()
fig_env.add_trace(
    go.Scatter(
        x=t,
        y=envolvente,
        mode="lines",
        name="Envolvente ADSR",
        line=dict(color="#9467bd", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(148, 103, 189, 0.15)",
    )
)
fig_env.update_layout(
    xaxis_title="Tiempo (s)",
    yaxis_title="Ganancia",
    yaxis=dict(range=[-0.05, 1.15]),
    template="plotly_white",
    height=250,
)
st.plotly_chart(fig_env, use_container_width=True)
