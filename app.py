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
    import paho.mqtt.publish as publish
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

        /* Forzar fondo claro general */
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

        /* Adaptación de campos de texto */
        div[data-baseweb="input"], 
        div[data-baseweb="textarea"], 
        [data-testid="stTextInput"] input,
        [data-testid="stChatInput"] textarea {
            background-color: #FFFFFF !important;
            color: #1A1A1A !important;
            border-radius: 14px !important;
            border: 1.5px solid #E0E0E0 !important;
        }

        /* Grabador de audio nativo */
        [data-testid="stAudioInput"] {
            background-color: #FFFFFF !important;
            border-radius: 18px !important;
            border: 1.5px solid #EAEAEA !important;
            padding: 12px !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.03) !important;
        }

        [data-testid="stSegmentedControl"] {
            background-color: #E8ECEF !important;
            border-radius: 18px !important;
            padding: 4px !important;
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
# 4. CONFIGURACIÓN MQTT SINCRÓNICA (Garantiza entrega de trama)
# ==========================================
broker = "broker.mqttdashboard.com"
port = 1883
mqtt_topic = "voicesebas"

def publish_to_wokwi(command_text, status_code="GREEN"):
    if HAS_MQTT:
        try:
            message = json.dumps({
                "Act1": command_text,
                "status": status_code
            })
            publish.single(
                topic=mqtt_topic,
                payload=message,
                hostname=broker,
                port=port
            )
            return True
        except Exception as e:
            st.error(f"Error al enviar mensaje por MQTT: {e}")
            return False
    return False

# ==========================================
# 5. GESTIÓN DE SESIÓN
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
# 6. ENCABEZADO Y CLAVE DE API
# ==========================================
st.markdown("""
<div class="app-header">
    <div>
        <h1 style="font-size: 1.8rem; margin: 0;">FLUENTY</h1>
        <p style="margin: 0; font-size: 0.9rem;">Asistente Multimodal de Idiomas</p>
    </div>
    <div style="background: white; padding: 4px 12px; border-radius: 20px; font-weight:600; font-size:0.8rem;">
        🟢 MQTT: voicesebas
    </div>
</div>
""", unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="app-card card-blue" style="padding: 14px 18px; margin-bottom: 12px;">', unsafe_allow_html=True)
    api_key = st.text_input(
        "🔑 Ingrese su OpenAI API Key para habilitar la IA:", 
        type="password", 
        placeholder="sk-...", 
        key="main_api_key_input"
    )
    if api_key:
        os.environ['OPENAI_API_KEY'] = api_key
        st.success("API Key vinculada correctamente ✅")
    else:
        st.warning("⚠️ Ingrese su API Key para el análisis de voz y lecturas PDF.")
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 7. NAVEGACIÓN
# ==========================================
selected_tab = st.segmented_control(
    "Navegación",
    options=["📚 Lectura PDF", "🎙️ Pronunciación"],
    default="🎙️ Pronunciación",
    label_visibility="collapsed"
)

# ==========================================
# TAB 1: ASISTENTE DE LECTURA (PDF + RAG)
# ==========================================
if selected_tab == "📚 Lectura PDF":
    st.markdown("""
    <div class="app-card card-blue">
        <h3 style="margin-bottom: 4px;">📄 Analizar Documento</h3>
        <p style="font-size: 0.9rem; margin: 0;">Carga tu lectura en PDF para hacer consultas gramaticales o de concepto.</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_pdf = st.file_uploader("Subir archivo PDF", type=["pdf"], label_visibility="collapsed")

    if uploaded_pdf and api_key and HAS_RAG:
        if st.session_state.pdf_name != uploaded_pdf.name or st.session_state.knowledge_base is None:
            with st.spinner("Procesando e indexando lectura..."):
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
                    st.success("¡PDF indexado con éxito!")
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
                fallback = "⚠️ Ingrese su API Key de OpenAI en la casilla superior para consultar."
                st.warning(fallback)
                st.session_state.chat_messages.append({"role": "assistant", "content": fallback})
            elif not uploaded_pdf:
                fallback = "⚠️ Cargue un archivo PDF primero para realizar la búsqueda."
                st.info(fallback)
                st.session_state.chat_messages.append({"role": "assistant", "content": fallback})
            elif st.session_state.knowledge_base and HAS_RAG:
                with st.spinner("Analizando la información..."):
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

# ==========================================
# TAB 2: PRONUNCIACIÓN (VOZ REAL + WHISPER + MQTT)
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
    st.write("Presiona el botón para iniciar, detener y revisar tu grabación de voz:")

    audio_file = st.audio_input("Grabar pronunciación", key="mic_recorder")

    captured_text = None

    if audio_file:
        if api_key and HAS_OPENAI:
            with st.spinner("Analizando pronunciación con Whisper AI..."):
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
            st.warning("⚠️ Ingrese su OpenAI API Key en la casilla superior para analizar el audio con Whisper.")

    manual_input = st.text_input("O ingresa una prueba de voz simulada:", placeholder="Ej: Language shapes the way we think...")
    if manual_input:
        captured_text = manual_input

    # EVALUACIÓN Y PUBLICACIÓN EN WOKWI
    if captured_text:
        target_words = st.session_state.target_phrase.lower().replace(".", "").replace(",", "").split()
        spoken_words = captured_text.lower().replace(".", "").replace(",", "").split()

        score = SequenceMatcher(None, target_words, spoken_words).ratio() * 100

        if score >= 70:
            publish_to_wokwi(captured_text, status_code="GREEN")
            st.balloons()
            st.markdown("""
            <div class="app-card card-green">
                <h3 style="color: #2E7D32;">¡Excelente Pronunciación! 🌟</h3>
                <p style="margin:0;">Se envió la trama al tópico <b>voicesebas</b> -> LED VERDE encendido en Wokwi.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            publish_to_wokwi(captured_text, status_code="RED")
            st.markdown("""
            <div class="app-card card-pink">
                <h3 style="color: #C7859B;">Detalles por Corregir 💡</h3>
                <p style="margin:0;">Se envió la trama al tópico <b>voicesebas</b> -> LED ROJO encendido en Wokwi.</p>
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
