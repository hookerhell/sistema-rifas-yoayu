import streamlit as st
import pandas as pd
import random
from streamlit_confetti import confetti
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime

# ---------------- CONFIGURACIÓN ----------------
if 'sidebar_state' not in st.session_state:
    st.session_state.sidebar_state = "expanded"

st.set_page_config(
    page_title="Sorteo Mega Bono Yoayu 2026", 
    page_icon="🏆", 
    layout="wide",
    initial_sidebar_state=st.session_state.sidebar_state
)

COLOR_PRIMARIO = "#00873E"  
TEXTO_NEGRO = "#1E1E1E"
TEXTO_GRIS = "#666666"

st.markdown(f"""
    <style>
    .stButton>button {{ background-color: {COLOR_PRIMARIO}; color: white; border-radius: 10px; height: 3.5em; font-weight: bold; width: 100%; }}
    .stButton>button:disabled {{ background-color: #cccccc !important; color: #666666 !important; }}
    [data-testid="stMetricValue"] {{ color: {COLOR_PRIMARIO}; font-weight: bold; }}
    .ganador-card {{
        background-color: white !important;
        border-left: 8px solid {COLOR_PRIMARIO} !important;
        padding: 15px !important;
        border-radius: 10px !important;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1) !important;
        margin-bottom: 15px !important;
        min-height: 140px !important;
        color: {TEXTO_NEGRO} !important;
    }}
    .ganador-card .nro-premio {{ color: {TEXTO_GRIS} !important; font-size: 12px; font-weight: bold; }}
    .ganador-card .rifa-highlight {{ color: {COLOR_PRIMARIO} !important; font-size: 19px; display: block; font-weight: 900 !important; margin: 2px 0; }}
    .ganador-card .nombre-txt {{ color: {TEXTO_NEGRO} !important; font-weight: bold; display: block; margin: 3px 0; font-size: 14px; }}
    .ganador-card .detalle-txt {{ color: {TEXTO_GRIS} !important; display: block; font-size: 12px; }}
    </style>
    """, unsafe_allow_html=True)

# ---------------- SESSION STATE ----------------
if 'df_original' not in st.session_state: st.session_state.df_original = None
if 'df_participantes' not in st.session_state: st.session_state.df_participantes = None
if 'ganadores_lista' not in st.session_state: st.session_state.ganadores_lista = []
if 'cantidad_a_sortear' not in st.session_state: st.session_state.cantidad_a_sortear = 1
if 'contador_ronda' not in st.session_state: st.session_state.contador_ronda = 0
if 'ultimo_ganador' not in st.session_state: st.session_state.ultimo_ganador = None
if 'tanda_actual_lista' not in st.session_state: st.session_state.tanda_actual_lista = []
if 'acta_descargada' not in st.session_state: st.session_state.acta_descargada = False

# ---------------- FUNCIÓN PDF ----------------
def generar_pdf_profesional(lista_ganadores):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elementos = []
    elementos.append(Paragraph(f"<b>REPORTE: SORTEO MEGA BONO YOAYU 2026</b>", styles['Title']))
    elementos.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
    elementos.append(Spacer(1, 25))
    datos = [["Cant.", "Nro Rifa", "Nombre y Apellido", "Socio", "Agencia", "Hora"]]
    for i, g in enumerate(lista_ganadores, 1):
        datos.append([str(i), str(g['nro']), g['nombre'], str(g['socio']), g['agencia'], g['hora']])
    tabla = Table(datos, colWidths=[40, 60, 180, 60, 90, 60])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLOR_PRIMARIO)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), 
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 80))
    datos_firmas = [
        ["__________________________", "__________________________"],
        ["Firma del Auditor Interno", "Firma Junta de Vigilancia"]
    ]
    tabla_firmas = Table(datos_firmas, colWidths=[240, 240])
    tabla_firmas.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTSIZE', (0, 0), (-1, -1), 10)]))
    elementos.append(tabla_firmas)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("⚙️ Panel de Control")
    bloqueo_seguridad = len(st.session_state.ganadores_lista) > 0 and not st.session_state.acta_descargada
    archivo_subido = st.file_uploader("1. Cargar Excel", type=["xlsx", "xls"])

    if bloqueo_seguridad:
        st.warning("⚠️ Debe descargar el acta antes de reiniciar o filtrar.")

    if archivo_subido and st.button("🚀 Cargar / Reiniciar Base", disabled=bloqueo_seguridad):
        df = pd.read_excel(archivo_subido)
        df.columns = df.columns.str.strip().str.lower()
        m_nom = next((c for c in ['apellidos y nombres', 'apellidos y nombre'] if c in df.columns), None)
        if m_nom: df = df.rename(columns={m_nom: 'apellidos y nombre'})
        for c in ['socio', 'rifa nro']:
            if c in df.columns:
                df[c] = df[c].astype(str).apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x).str.strip()
        st.session_state.df_original = df
        st.session_state.df_participantes = df.copy()
        st.session_state.ganadores_lista = []
        st.session_state.tanda_actual_lista = []
        st.session_state.contador_ronda = 0
        st.session_state.ultimo_ganador = None
        st.session_state.acta_descargada = False
        st.success("¡Base cargada!")

    if st.session_state.df_original is not None:
        st.write("---")
        st.header("🎯 Configurar Ronda")
        
        # LIMITADO A 20 MÁXIMO AQUÍ
        st.session_state.cantidad_a_sortear = st.number_input("Premios a sortear (Máx. 20):", 1, 20, st.session_state.cantidad_a_sortear)
        
        if 'agencia' in st.session_state.df_original.columns:
            opc = ["Todas"] + sorted(st.session_state.df_original['agencia'].dropna().unique().tolist())
            sel = st.selectbox("Agencia:", opc)
            if st.button("Aplicar Filtro", disabled=bloqueo_seguridad):
                st.session_state.df_participantes = st.session_state.df_original.copy() if sel == "Todas" else st.session_state.df_original[st.session_state.df_original['agencia'] == sel].copy()
                st.session_state.tanda_actual_lista = []
                st.session_state.contador_ronda = 0
                st.session_state.acta_descargada = False
                st.rerun()

    if st.session_state.ganadores_lista:
        st.write("---")
        pdf_file = generar_pdf_profesional(st.session_state.ganadores_lista)
        if st.download_button("📥 DESCARGAR ACTA", data=pdf_file, file_name=f"acta_yoayu_{datetime.now().strftime('%H%M')}.pdf", mime="application/pdf", use_container_width=True):
            st.session_state.acta_descargada = True
            st.rerun()

# ---------------- MAIN ----------------
st.markdown(f"<h1 style='text-align: center; color: {COLOR_PRIMARIO};'>🏆 Sorteo Mega Bono Yoayu 2026🏆</h1>", unsafe_allow_html=True)

if st.session_state.df_participantes is not None:
    # SE ASEGURA EL LÍMITE DE 20 EN LA LÓGICA
    limite = min(st.session_state.cantidad_a_sortear, 20)
    actual = st.session_state.contador_ronda
    
    c1, c2, c3 = st.columns(3)
    c1.metric("En Tómbola", len(st.session_state.df_participantes))
    c2.metric("Tanda Actual", f"{actual} de {limite}")
    c3.metric("Total General", len(st.session_state.ganadores_lista))

    if actual < limite:
        if st.button("🔴 ¡REALIZAR SORTEO!", type="primary"):
            df = st.session_state.df_participantes
            if not df.empty:
                idx = random.choice(df.index)
                f = df.loc[idx]
                ganador = {
                    'nro': f.get('rifa nro', 'N/A'),
                    'nombre': f.get('apellidos y nombre', 'Desconocido'),
                    'socio': f.get('socio', '-'),
                    'agencia': f.get('agencia', '-'),
                    'hora': datetime.now().strftime("%H:%M:%S")
                }
                st.session_state.ganadores_lista.append(ganador)
                st.session_state.tanda_actual_lista.append(ganador)
                st.session_state.ultimo_ganador = ganador
                st.session_state.df_participantes = df.drop(idx)
                st.session_state.contador_ronda += 1
                st.session_state.acta_descargada = False
                st.rerun()
    else:
        st.error(f"⛔ Ronda completada (Límite 20). Descargue el acta para continuar.")

    if st.session_state.ultimo_ganador:
        g = st.session_state.ultimo_ganador
        st.balloons()
        confetti(emojis=["🏆", "⭐"])
        st.markdown(f"""
            <div style="text-align: center; background-color: white; border: 10px solid {COLOR_PRIMARIO}; padding: 40px; border-radius: 30px; margin-bottom: 40px; color: {TEXTO_NEGRO};">
                <h2 style="color: {TEXTO_GRIS}; margin: 0; font-weight: normal;">RIFA PREMIADA</h2>
                <h1 style="color: {COLOR_PRIMARIO}; font-size: 140px; margin: 0; font-weight: bold;">{g['nro']}</h1>
                <h2 style="font-size: 50px; margin: 10px 0;">{g['nombre']}</h2>
                <hr style="border: 1px solid {COLOR_PRIMARIO}; width: 30%; margin: 20px auto;">
                <p style="font-size: 28px; margin-bottom: 20px;"><b>SOCIO:</b> {g['socio']} | <b>AGENCIA:</b> {g['agencia']}</p>
                <h3 style="color: {COLOR_PRIMARIO}; font-style: italic; margin-top: 20px;">¡Cooperativa Yoayu Ltda. - Creciendo Juntos!</h3>
            </div>
        """, unsafe_allow_html=True)

    if st.session_state.tanda_actual_lista:
        st.write("---")
        st.subheader("📋 RESUMEN DE LA TANDA")
        cols = st.columns(4)
        for i, g_hist in enumerate(st.session_state.tanda_actual_lista, 1):
            with cols[(i-1) % 4]:
                st.markdown(f"""
                    <div class="ganador-card">
                        <span class="nro-premio">Nº {i}</span>
                        <span class="rifa-highlight"><b>Rifa: {g_hist['nro']}</b></span>
                        <span class="nombre-txt">{g_hist['nombre']}</span>
                        <span class="detalle-txt">Socio: {g_hist['socio']} | {g_hist['agencia']}</span>
                    </div>
                """, unsafe_allow_html=True)
else:
    st.info("👈 Cargue el Excel para comenzar.")