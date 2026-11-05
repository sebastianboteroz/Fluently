import os
import time
import json
import traceback
from difflib import SequenceMatcher
import streamlit as st
from PIL import Image

# ==========================================
# 1. IMPORTACIONES DE LIBRERÍAS (CON FALLBACKS)
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
    from openai import OpenAI
    HAS_OPENAI = True
except Exception:
    HAS_OPENAI = False

try:
    import paho.mqtt.client as paho
    HAS_MQTT = True
except Exception:
    HAS_MQTT = False

# ==========================================
# 2. CONFIGURACIÓN DE PÁGINA (ESTILO MOBILE APP)
# ==========================================
st.set_page_config(
    page_title="Fluenty App",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 3. CSS Y LÍNEA GRÁFICA (SUNBORN + INTER + COLORES PASTEL)
# ==========================================
def inject_custom_styles():
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

        .stApp {
            background-color: var(--bg-app) !important;
        }

        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            max-width: 580px !important;
        }

        html, body, [class*="css"], .stMarkdown, p, span, label, div {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            color: var(--text-main) !important;
        }

        h1, h2, h3, .stTitle, .stHeader {
            font-family: 'Sunborn', 'Inter', sans-serif !important;
            color: var(--text-main) !important;
            letter-spacing: 0.5px;
        }

        /* Banner Superior */
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
            opacity: 0.95;
        }

        /* Tarjetas de Diseño (Cards UI) */
        .app-card {
            background-color: var(--card-white);
            border-radius: 22px;
            padding: 20px;
            border: 1.5px solid var(--border-color);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.03);
            margin-bottom: 15px;
        }

        .card-pink { background-color: #FDF2F4; border-color: var(--dusty-pink); }
        .card-blue { background-color: #F0F8FA; border-color: var(--pastel-blue); }
        .card-green { background-color: #F0F7F4; border-color: var(--mint-green); }

        .status-badge {
            display: inline-flex;
            align-items: center;
            background-color: #FFFFFF;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        }

        .status-dot {
            height: 8px;
            width: 8px;
            background-color: #22C55E;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }

        /* Botones estilo App */
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

        .stButton>button:hover {
            background-color: var(--mint-hover) !important;
        }

        /* Badges de Pronunciación */
        .word-correct {
            display: inline-block;
            background-color: var(--mint-green);
            color: #1A1A1A;
            padding: 6px 12px;
            border-radius: 12px;
            margin: 4px;
            font-weight: 700;
            font-size: 0.95rem;
        }

        .word-error {
            display: inline-block;
            background-color: var(--dusty-pink);
            color: #FFFFFF;
            padding: 6px 12px;
            border-radius: 12px;
            margin: 4px;
            font-weight: 700;
            font-size: 0.95rem;
        }

        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_styles()

# ==========================================
# 4. FUNCIONES MQTT (TÓPICO: voicemajo)
# ==========================================
BROKER_URL = "broker.mqttdashboard.com"
BROKER_PORT = 1883
MQTT_TOPIC = "voicemajo"

def send_mqtt_payload(command_text, status_code="GREEN"):
    if HAS_MQTT:
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
# 5. ESTADO DE SESIÓN (SESSION STATE)
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
# 6. ENCABEZADO PERMANENTE
# ==========================================
st.markdown("""
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

# BARRA LATERAL (AJUSTES TÉCNICOS)
with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    if api_key:
        os.environ['OPENAI_API_KEY'] = api_key
        st.success("API Key Conectada 🟢")
    else:
        st.warning("Ingresa tu API Key para habilitar RAG y Whisper 🟡")

    st.markdown("---")
    st.caption(f"Broker MQTT: `{BROKER_URL}`")
    st.caption(f"Tópico Wokwi: `{MQTT_TOPIC}`")

# ==========================================
# 7. NAVEGACIÓN TIPO APP (SEGMENTED CONTROL)
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
        <h3 style="margin-bottom: 4px;">📄 Analizar Documento</h3>
        <p style="font-size: 0.9rem; margin: 0;">Carga una lectura académica en PDF para resolver dudas gramaticales o traducir conceptos.</p>
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
                    st.error("Error al procesar el archivo PDF.")
                    with st.expander("Detalle del error"):
                        st.code(traceback.format_exc())

    st.markdown("---")
    st.subheader("💬 Chat de Consulta")

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Escribe tu pregunta sobre la lectura..."):
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
                        ("system", "Eres Fluenty, un tutor de inglés y asistente académico. Responde en español explicando los fragmentos del texto en inglés."),
                        ("user", f"Contexto:\n{context}\n\nPregunta: {prompt}")
                    ]
                    ans = llm.invoke(messages).content
                    st.markdown(ans)
                    st.session_state.chat_messages.append({"role": "assistant", "content": ans})
            else:
                fallback = "Por favor carga un PDF e ingresa tu OpenAI API Key en la barra lateral para procesar consultas."
                st.info(fallback)
                st.session_state.chat_messages.append({"role": "assistant", "content": fallback})

# ==========================================
# TAB 2: PRONUNCIACIÓN (VOZ REAL + WHISPER AI + MQTT)
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

    # Widget de Micrófono Nativo
    audio_file = st.audio_input("Presiona para grabar tu voz", key="mic_recorder")

    captured_text = None

    if audio_file:
        st.audio(audio_file)
        if api_key and HAS_OPENAI:
            with st.spinner("Analizando tu pronunciación con Whisper AI..."):
                try:
                    client_ai = OpenAI(api_key=api_key)
                    transcript = client_ai.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="en"
                    )
                    captured_text = transcript.text.strip()
                    st.info(f"🗣️ **Lo que la IA escuchó:** *\"{captured_text}\"*")
                except Exception as e:
                    st.error(f"Error procesando el audio: {e}")
        else:
            st.warning("⚠️ Debes ingresar tu OpenAI API Key en la barra lateral para transcribir la voz.")

    # Opción manual alternativa
    manual_input = st.text_input("O ingresa una prueba de voz simulada:", placeholder="Ej: Language shapes the way we think...")
    if manual_input:
        captured_text = manual_input

    # EVALUACIÓN Y FEEDBACK VISUAL + MQTT
    if captured_text:
        target_words = st.session_state.target_phrase.lower().replace(".", "").replace(",", "").split()
        spoken_words = captured_text.lower().replace(".", "").replace(",", "").split()

        score = SequenceMatcher(None, target_words, spoken_words).ratio() * 100

        if score >= 80:
            send_mqtt_payload(captured_text, status_code="GREEN")
            st.balloons()
            st.markdown("""
            <div class="app-card card-green">
                <h3 style="color: #2E7D32;">¡Excelente Pronunciación! 🌟</h3>
                <p style="margin:0;">Pronunciaste las palabras correctamente. Señal VERDE enviada a Wokwi.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            send_mqtt_payload(captured_text, status_code="RED")
            st.markdown("""
            <div class="app-card card-pink">
                <h3 style="color: #C7859B;">Detalles por Corregir 💡</h3>
                <p style="margin:0;">Revisa las palabras marcadas en rojo para mejorar tu fluidez. Señal ROJA enviada a Wokwi.</p>
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
