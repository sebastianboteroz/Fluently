import os
import time
import json
import traceback
from difflib import SequenceMatcher
import streamlit as st
from PIL import Image

# ==========================================
# 1. IMPORTACIONES DE LIBRERÍAS
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
# 2. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Fluenty App",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 3. CSS (LÍNEA GRÁFICA & MODO CLARO FORZADO)
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

        .stApp, [data-testid="stAppViewContainer"], .main {
            background-color: #FDFBF7 !important;
            color: #1A1A1A !important;
        }

        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            max-width: 580px !important;
        }

        p, h1, h2, h3, h4, label, span {
            font-family: 'Inter', -apple-system, sans-serif !important;
            color: #1A1A1A !important;
        }

        h1, h2, h3, .stTitle {
            font-family: 'Sunborn', 'Inter', sans-serif !important;
            color: #1A1A1A !important;
            letter-spacing: 0.5px;
        }

        div[data-baseweb="input"], 
        div[data-baseweb="textarea"], 
        [data-testid="stTextInput"] input,
        [data-testid="stChatInput"] textarea {
            background-color: #FFFFFF !important;
            color: #1A1A1A !important;
            border-radius: 14px !important;
            border: 1.5px solid #E0E0E0 !important;
        }

        [data-testid="stSegmentedControl"] {
            background-color: #E8ECEF !important;
            border-radius: 18px !important;
            padding: 4px !important;
        }

        [data-testid="stSegmentedControl"] button {
            background-color: transparent !important;
            color: #1A1A1A !important;
            border: none !important;
            border-radius: 14px !important;
            font-weight: 600 !important;
        }

        [data-testid="stSegmentedControl"] button[aria-selected="true"] {
            background-color: #8EC3B0 !important;
            color: #1A1A1A !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
        }

        .app-header {
            background: linear-gradient(135deg, #A5D7E8 0%, #8EC3B0 100%);
            padding: 1.4rem;
            border-radius: 24px;
            color: #1A1A1A;
            margin-bottom: 1.2rem;
            box-shadow: 0 8px 20px rgba(142, 195, 176, 0.25);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .app-header h1 { font-size: 1.8rem; margin: 0; line-height: 1.1; }
        .app-header p { font-size: 0.9rem; margin: 4px 0 0 0; opacity: 0.95; }

        .app-card {
            background-color: #FFFFFF;
            border-radius: 22px;
            padding: 18px 20px;
            border: 1.5px solid #EAEAEA;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.03);
            margin-bottom: 15px;
        }

        .card-pink { background-color: #FDF2F4; border-color: #C7859B; }
        .card-blue { background-color: #F0F8FA; border-color: #A5D7E8; }
        .card-green { background-color: #F0F7F4; border-color: #8EC3B0; }

        .status-badge {
            display: inline-flex;
            align-items: center;
            background-color: #FFFFFF;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }

        .status-dot {
            height: 8px; width: 8px;
            background-color: #22C55E;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }

        [data-testid="stChatMessage"] {
            background-color: #FFFFFF !important;
            border-radius: 18px !important;
            border: 1px solid #EAEAEA !important;
            color: #1A1A1A !important;
            margin-bottom: 10px !important;
        }

        .word-correct {
            display: inline-block;
            background-color: #8EC3B0;
            color: #1A1A1A;
            padding: 6px 12px;
            border-radius: 12px;
            margin: 4px;
            font-weight: 700;
        }

        .word-error {
            display: inline-block;
            background-color: #C7859B;
            color: #FFFFFF;
            padding: 6px 12px;
            border-radius: 12px;
            margin: 4px;
            font-weight: 700;
        }

        #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_styles()

# ==========================================
# 4. FUNCIONES MQTT (TÓPICO PERSONALIZADO: voicesebas)
# ==========================================
BROKER_URL = "broker.mqttdashboard.com"
BROKER_PORT = 1883
MQTT_TOPIC = "voicesebas"

def send_mqtt_payload(command_text, status_code="GREEN"):
    if HAS_MQTT:
        try:
            client = paho.Client("ClienteSebas_Fluenty")
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
# 5. ESTADO DE SESIÓN
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
# 6. BANNER Y ENTRADA DE API KEY EN PANTALLA PRINCIPAL
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

with st.container():
    st.markdown('<div class="app-card card-blue" style="padding: 14px 18px; margin-bottom: 12px;">', unsafe_allow_html=True)
    api_key = st.text_input(
        "🔑 Ingrese su OpenAI API Key para activar la IA:", 
        type="password", 
        placeholder="sk-...", 
        key="main_api_key_input"
    )
    if api_key:
        os.environ['OPENAI_API_KEY'] = api_key
        st.success("API Key conectada 🟢", icon="✅")
    else:
        st.warning("⚠️ Ingrese su API Key para procesar lecturas PDF y análisis de voz.")
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 7. NAVEGACIÓN PRINCIPAL
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
        <p style="font-size: 0.9rem; margin: 0;">Carga tu lectura en PDF para traducir o resolver dudas.</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_pdf = st.file_uploader("Subir archivo PDF", type=["pdf"], label_visibility="collapsed")

    if uploaded_pdf and api_key and HAS_RAG:
        if st.session_state.pdf_name != uploaded_pdf.name or st.session_state.knowledge_base is None:
            with st.spinner("Indexando lectura con IA..."):
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
                    st.success("¡PDF procesado y listo para consultas!")
                except Exception as e:
                    st.error("Error al procesar el archivo PDF.")

    st.markdown("---")
    st.subheader("💬 Chat de Consulta")

    for msg in st.session_state.chat_messages:
        avatar_icon = "👤" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Escribe tu pregunta sobre la lectura..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            if not api_key:
                fallback = "⚠️ Por favor ingresa tu OpenAI API Key en la caja superior para continuar."
                st.warning(fallback)
                st.session_state.chat_messages.append({"role": "assistant", "content": fallback})
            elif not uploaded_pdf:
                fallback = "⚠️ Por favor sube un archivo PDF arriba para poder analizarlo."
                st.info(fallback)
                st.session_state.chat_messages.append({"role": "assistant", "content": fallback})
            elif st.session_state.knowledge_base and HAS_RAG:
                with st.spinner("Consultando al asistente..."):
                    docs = st.session_state.knowledge_base.similarity_search(prompt, k=4)
                    context = "\n\n".join([d.page_content for d in docs])
                    llm = ChatOpenAI(temperature=0.2, model_name="gpt-4o-mini")
                    messages = [
                        ("system", "Eres Fluenty, un tutor de inglés y asistente académico. Responde en español explicando los fragmentos del texto en inglés de forma clara."),
                        ("user", f"Contexto de la lectura:\n{context}\n\nPregunta: {prompt}")
                    ]
                    ans = llm.invoke(messages).content
                    st.markdown(ans)
                    st.session_state.chat_messages.append({"role": "assistant", "content": ans})

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
            st.warning("⚠️ Ingresa tu OpenAI API Key arriba para transcribir la voz.")

    manual_input = st.text_input("O ingresa una prueba de voz simulada:", placeholder="Ej: Language shapes the way we think...")
    if manual_input:
        captured_text = manual_input

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
