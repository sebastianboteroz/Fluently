import os
import time
import json
import traceback
from difflib import SequenceMatcher
import streamlit as st
from PIL import Image

# ==========================================
# 1. IMPORTACIONES TÉCNICAS (RAG + VOZ + MQTT)
# ==========================================
try:
    from PyPDF2 import PdfReader
    from langchain_text_splitters import CharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    HAS_RAG = True
except Exception:
    HAS_RAG = False

try:
    import paho.mqtt.client as paho
    from bokeh.models.widgets import Button
    from bokeh.models import CustomJS
    from streamlit_bokeh_events import streamlit_bokeh_events
    HAS_VOICE = True
except Exception:
    HAS_VOICE = False

# ==========================================
# 2. CONFIGURACIÓN DE PÁGINA MÓVIL
# ==========================================
st.set_page_config(
    page_title="Fluenty App",
    page_icon="🎙️",
    layout="centered",  # Centrado para simular la proporción de teléfono/tablet
    initial_sidebar_state="collapsed"
)

# ==========================================
# 3. CSS APP SHELL & LÍNEA GRÁFICA (UX/UI)
# ==========================================
def inject_mobile_app_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        @font-face {
            font-family: 'Sunborn';
            src: url('sunborn-sans-one.otf') format('opentype');
            font-weight: normal;
            font-style: normal;
        }

        :root {
            --bg-app: #FDFBF7;
            --card-white: #FFFFFF;
            --text-main: #1A1A1A;
            --mint-green: #8EC3B0;
            --mint-hover: #7AB4A1;
            --dusty-pink: #C7859B;
            --pastel-blue: #A5D7E8;
            --soft-coral: #FA9884;
            --border-color: #EAEAEA;
        }

        /* Fondo de pantalla general */
        .stApp {
            background-color: var(--bg-app) !important;
        }

        /* Reducir márgenes externos para efecto App Shell */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            max-width: 550px !important; /* Ancho máximo estándar de tablet/móvil */
        }

        /* Tipografía general */
        html, body, [class*="css"], .stMarkdown, p, span, label, div {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            color: var(--text-main) !important;
        }

        /* Tipografía de Títulos */
        h1, h2, h3, .stTitle, .stHeader {
            font-family: 'Sunborn', 'Inter', sans-serif !important;
            color: var(--text-main) !important;
            letter-spacing: 0.5px;
        }

        /* Header de la App */
        .app-header {
            background: linear-gradient(135deg, var(--pastel-blue) 0%, var(--mint-green) 100%);
            padding: 1.4rem;
            border-radius: 24px;
            color: #1A1A1A;
            margin-bottom: 1.2rem;
            box-shadow: 0 8px 20px rgba(142, 195, 176, 0.25);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .app-header h1 {
            font-size: 1.8rem;
            margin: 0;
            line-height: 1.1;
        }

        .app-header p {
            font-size: 0.9rem;
            margin: 4px 0 0 0;
            opacity: 0.9;
        }

        /* Tarjetas de Contenido (Cards UI) */
        .app-card {
            background-color: var(--card-white);
            border-radius: 22px;
            padding: 18px 20px;
            border: 1.5px solid var(--border-color);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.03);
            margin-bottom: 15px;
        }

        .card-pink { background-color: #FDF2F4; border-color: var(--dusty-pink); }
        .card-blue { background-color: #F0F8FA; border-color: var(--pastel-blue); }
        .card-green { background-color: #F0F7F4; border-color: var(--mint-green); }

        /* Indicador de Estado en Vivo */
        .status-badge {
            display: inline-flex;
            align-items: center;
            background-color: #FFFFFF;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }

        .status-dot {
            height: 8px;
            width: 8px;
            background-color: #22C55E;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }

        /* Rediseño del Botón Bokeh para que parezca botón de App */
        div[data-testid="stBokehChart"], .bk-root, .bk {
            background-color: transparent !important;
            width: 100% !important;
        }

        .bk-btn, button.bk-btn-default {
            background: linear-gradient(135deg, var(--soft-coral) 0%, var(--dusty-pink) 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 700 !important;
            font-size: 1.05rem !important;
            border-radius: 16px !important;
            padding: 0.9rem 1.2rem !important;
            box-shadow: 0 6px 18px rgba(250, 152, 132, 0.35) !important;
            width: 100% !important;
            cursor: pointer !important;
            transition: transform 0.15s ease !important;
        }

        .bk-btn:active {
            transform: scale(0.97) !important;
        }

        /* Botones de Streamlit Estilo App */
        .stButton>button {
            background-color: var(--mint-green) !important;
            color: var(--text-main) !important;
            font-weight: 700 !important;
            border-radius: 16px !important;
            padding: 0.75rem 1.5rem !important;
            border: none !important;
            box-shadow: 0 4px 12px rgba(142, 195, 176, 0.3) !important;
            width: 100% !important;
        }

        /* Badges para evaluación de palabras */
        .word-correct {
            display: inline-block;
            background-color: var(--mint-green);
            color: #1A1A1A;
            padding: 6px 12px;
            border-radius: 12px;
            margin: 3px;
            font-weight: 700;
            font-size: 0.9rem;
        }

        .word-error {
            display: inline-block;
            background-color: var(--dusty-pink);
            color: #FFFFFF;
            padding: 6px 12px;
            border-radius: 12px;
            margin: 3px;
            font-weight: 700;
            font-size: 0.9rem;
        }

        /* Ocultar barra superior por defecto de Streamlit */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

inject_mobile_app_css()

# ==========================================
# 4. CONFIGURACIÓN MQTT (TOPIC: voicemajo)
# ==========================================
BROKER_URL = "broker.mqttdashboard.com"
BROKER_PORT = 1883
MQTT_TOPIC = "voicemajo"

def send_mqtt_payload(command_text, status_code="GREEN"):
    """Envía la trama JSON al broker MQTT para el circuito Wokwi."""
    if HAS_VOICE:
        try:
            client = paho.Client("Fluenty_Mobile_Client")
            client.connect(BROKER_URL, BROKER_PORT, 60)
            payload = json.dumps({
                "Act1": command_text,
                "status": status_code,
                "timestamp": time.time()
            })
            client.publish(MQTT_TOPIC, payload)
            client.disconnect()
            return True
        except Exception:
            return False
    return False

# ==========================================
# 5. SESSION STATE
# ==========================================
if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = None

if "pdf_name" not in st.session_state:
    st.session_state.pdf_name = None

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "target_phrase" not in st.session_state:
    st.session_state.target_phrase = (
        "Language shapes the way we think and determines the things we can think about."
    )

# ==========================================
# 6. HEADER PERMANENTE DE LA APP
# ==========================================
st.markdown(f"""
<div class="app-header">
    <div>
        <h1>FLUENTY</h1>
        <p>Asistente Multimodal de Idiomas</p>
    </div>
    <div class="status-badge">
        <span class="status-dot"></span> Wokwi MQTT
    </div>
</div>
""", unsafe_allow_html=True)

# BARRA LATERAL (CONFIGURACIÓN TÉCNICA Y API KEY)
with st.sidebar:
    st.markdown("### ⚙️ Ajustes de la App")
    api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    if api_key:
        os.environ['OPENAI_API_KEY'] = api_key
        st.success("API Key Conectada 🟢")
    st.markdown("---")
    st.caption(f"Broker MQTT: `{BROKER_URL}`")
    st.caption(f"Tópico Wokwi: `{MQTT_TOPIC}`")

# ==========================================
# 7. NAVEGACIÓN PRINCIPAL (TAB BAR ESTILO MÓVIL)
# ==========================================
selected_tab = st.segmented_control(
    "Navegación",
    options=["📚 Lectura PDF", "🎙️ Pronunciación"],
    default="🎙️ Pronunciación",
    label_visibility="collapsed"
)

# ==========================================
# TAB 1: ASISTENTE DE LECTURA (RAG + PDF)
# ==========================================
if selected_tab == "📚 Lectura PDF":
    st.markdown("""
    <div class="app-card card-blue">
        <h3>📄 Analizar Documento</h3>
        <p style="font-size: 0.9rem; margin-bottom: 8px;">Carga un PDF académico para traducir o aclarar conceptos complejos.</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_pdf = st.file_uploader("Subir archivo PDF", type=["pdf"], label_visibility="collapsed")

    if uploaded_pdf and api_key and HAS_RAG:
        if st.session_state.pdf_name != uploaded_pdf.name:
            with st.spinner("Procesando lectura..."):
                try:
                    pdf_reader = PdfReader(uploaded_pdf)
                    full_text = ""
                    for page in pdf_reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            full_text += extracted

                    text_splitter = CharacterTextSplitter(
                        separator="\n",
                        chunk_size=600,
                        chunk_overlap=50,
                        length_function=len
                    )
                    chunks = text_splitter.split_text(full_text)
                    embeddings = OpenAIEmbeddings()
                    st.session_state.knowledge_base = FAISS.from_texts(chunks, embeddings)
                    st.session_state.pdf_name = uploaded_pdf.name
                    st.success("¡PDF Indexado correctamente!")
                except Exception as e:
                    st.error("Error al procesar el PDF.")
                    with st.expander("Detalle del error"):
                        st.code(traceback.format_exc())

    st.markdown("---")
    st.subheader("💬 Chat de Consulta")

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Haz una pregunta sobre el PDF..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if st.session_state.knowledge_base and api_key and HAS_RAG:
                with st.spinner("Consultando al asistente..."):
                    docs = st.session_state.knowledge_base.similarity_search(prompt, k=4)
                    context = "\n\n".join([d.page_content for d in docs])
                    llm = ChatOpenAI(temperature=0.2, model_name="gpt-4o-mini")
                    messages = [
                        ("system", "Eres Fluenty, un tutor de inglés y asistente académico. Responde en español explicando los fragmentos del texto."),
                        ("user", f"Contexto:\n{context}\n\nPregunta: {prompt}")
                    ]
                    ans = llm.invoke(messages).content
                    st.markdown(ans)
                    st.session_state.chat_messages.append({"role": "assistant", "content": ans})
            else:
                fallback = "Por favor carga un PDF e ingresa tu OpenAI API Key en la barra lateral."
                st.info(fallback)
                st.session_state.chat_messages.append({"role": "assistant", "content": fallback})

# ==========================================
# TAB 2: LABORATORIO DE PRONUNCIACIÓN (VOZ + MQTT)
# ==========================================
else:
    st.markdown(f"""
    <div class="app-card card-green">
        <h3 style="margin-bottom: 6px;">📖 Lectura a Practicar</h3>
        <p style="font-size: 1.15rem; font-weight: 600; line-height: 1.4; color: #1A1A1A; margin: 0;">
            "{st.session_state.target_phrase}"
        </p>
    </div>
    """, unsafe_allow_html=True)

    edited_phrase = st.text_input("Editar frase de práctica:", value=st.session_state.target_phrase)
    if edited_phrase != st.session_state.target_phrase:
        st.session_state.target_phrase = edited_phrase
        st.rerun()

    st.markdown("<h3 style='margin-top: 15px;'>🎙️ Captura de Voz</h3>", unsafe_allow_html=True)

    captured_text = None

    if HAS_VOICE:
        # Botón Bokeh con WebSpeechAPI (Reconocimiento continuo y captura precisa)
        stt_button = Button(label="🎤 Toca para Hablar", width=280)
        stt_button.js_on_event("button_click", CustomJS(code="""
            var recognition = new webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';
            
            recognition.onresult = function (e) {
                var value = "";
                for (var i = e.resultIndex; i < e.results.length; ++i) {
                    if (e.results[i].isFinal) {
                        value += e.results[i][0].transcript;
                    }
                }
                if (value != "") {
                    document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: value}));
                }
            }
            recognition.start();
        """))

        result = streamlit_bokeh_events(
            stt_button,
            events="GET_TEXT",
            key="voice_input",
            refresh_on_update=False,
            override_height=70,
            debounce_time=0
        )

        if result and "GET_TEXT" in result:
            captured_text = result.get("GET_TEXT").strip()

    manual_input = st.text_input("O ingresa tu audio simulado:", placeholder="Ej: Language shapes the way we think...")

    if manual_input:
        captured_text = manual_input

    # EVALUACIÓN DE PRONUNCIACIÓN Y ENVÍO A WOKWI
    if captured_text:
        st.markdown(f"**Voz Detectada:** *\"{captured_text}\"*")

        target_words = st.session_state.target_phrase.lower().replace(".", "").replace(",", "").split()
        spoken_words = captured_text.lower().replace(".", "").replace(",", "").split()

        score = SequenceMatcher(None, target_words, spoken_words).ratio() * 100

        if score >= 80:
            send_mqtt_payload(captured_text, status_code="GREEN")
            st.balloons()
            st.markdown("""
            <div class="app-card card-green">
                <h3 style="color: #2E7D32;">¡Excelente Pronunciación! 🌟</h3>
                <p style="margin:0;">Tu fluidez es adecuada. Se envió señal VERDE a Wokwi.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            send_mqtt_payload(captured_text, status_code="RED")
            st.markdown("""
            <div class="app-card card-pink">
                <h3 style="color: #C7859B;">Detalles por Corregir 💡</h3>
                <p style="margin:0;">Revisa las palabras en rojo. Se envió señal ROJA a Wokwi.</p>
            </div>
            """, unsafe_allow_html=True)

        st.write("**Desglose de Términos:**")
        badges_html = ""
        for word in target_words:
            if word in spoken_words:
                badges_html += f'<span class="word-correct">✓ {word}</span> '
            else:
                badges_html += f'<span class="word-error">✗ {word}</span> '

        st.markdown(badges_html, unsafe_allow_html=True)
        st.metric("Puntaje de Fluidez", f"{score:.1f}%")
