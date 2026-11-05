import os
import time
import json
import traceback
import platform
from difflib import SequenceMatcher
import streamlit as st
from PIL import Image

# Importaciones RAG (LangChain + OpenAI + PyPDF)
try:
    from PyPDF2 import PdfReader
    from langchain_text_splitters import CharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    HAS_RAG = True
except Exception:
    HAS_RAG = False

# Importaciones Control por Voz & Hardware (Bokeh + MQTT)
try:
    import paho.mqtt.client as paho
    from bokeh.models.widgets import Button
    from bokeh.models import CustomJS
    from streamlit_bokeh_events import streamlit_bokeh_events
    HAS_VOICE_MQTT = True
except Exception:
    HAS_VOICE_MQTT = False

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA & RESPONSIVE UX/UI
# ==========================================
st.set_page_config(
    page_title="Fluenty | Lectura & Pronunciación Multimodal",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"  # Optimizado para móviles y iPads
)

def inject_custom_styles():
    st.markdown("""
    <style>
        /* Importar fuente Inter desde Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* Cargar fuente Sunborn local */
        @font-face {
            font-family: 'Sunborn';
            src: url('sunborn-sans-one.otf') format('opentype');
            font-weight: normal;
            font-style: normal;
        }

        /* Variables de Paleta de Color */
        :root {
            --bg-cream: #FDFBF7;
            --text-dark: #1A1A1A;
            --mint-green: #8EC3B0;
            --mint-hover: #7AB4A1;
            --dusty-pink: #C7859B;
            --pastel-blue: #A5D7E8;
            --soft-coral: #FA9884;
            --card-border: #EAEAEA;
        }

        /* Estructura Global Responsive */
        .stApp {
            background-color: var(--bg-cream) !important;
        }

        html, body, [class*="css"], .stMarkdown, p, span, label, div {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            color: var(--text-dark) !important;
        }

        /* Encabezados con Sunborn */
        h1, h2, h3, .stTitle, .stHeader {
            font-family: 'Sunborn', 'Inter', sans-serif !important;
            color: var(--text-dark) !important;
            letter-spacing: 0.5px;
        }

        /* Header de la App */
        .fluenty-header {
            background: linear-gradient(135deg, #A5D7E8 0%, #8EC3B0 100%);
            padding: 1.8rem;
            border-radius: 20px;
            color: #1A1A1A;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.6);
        }

        .fluenty-header h1 {
            font-size: 2rem;
            margin-bottom: 0.3rem;
        }

        /* Cards Personalizadas */
        .custom-card {
            background-color: #FFFFFF;
            border-radius: 20px;
            padding: 20px;
            border: 1.5px solid var(--card-border);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
            margin-bottom: 15px;
        }

        .card-pink { background-color: #FDF2F4; border-color: var(--dusty-pink); }
        .card-blue { background-color: #F0F8FA; border-color: var(--pastel-blue); }
        .card-green { background-color: #F0F7F4; border-color: var(--mint-green); }

        /* Botones Streamlit Estilo Pill */
        .stButton>button {
            background-color: var(--mint-green) !important;
            color: var(--text-dark) !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            border-radius: 14px !important;
            padding: 0.6rem 1.8rem !important;
            border: none !important;
            box-shadow: 0 4px 10px rgba(142, 195, 176, 0.3) !important;
            width: 100% !important;
            transition: all 0.2s ease-in-out !important;
        }

        .stButton>button:hover {
            background-color: var(--mint-hover) !important;
            transform: translateY(-2px) !important;
        }

        /* Override de Estilos para Botón Bokeh en Celular/Tablet */
        div[data-testid="stBokehChart"], .bk-root, .bk {
            background-color: transparent !important;
            width: 100% !important;
        }

        .bk-btn, button.bk-btn-default {
            background: linear-gradient(135deg, #FA9884 0%, #C7859B 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 700 !important;
            font-size: 1.05rem !important;
            border-radius: 14px !important;
            padding: 0.8rem 1.5rem !important;
            box-shadow: 0 4px 14px rgba(250, 152, 132, 0.4) !important;
            width: 100% !important;
            cursor: pointer !important;
        }

        /* Badges de Pronunciación */
        .word-badge-correct {
            display: inline-block;
            background-color: var(--mint-green);
            color: #1A1A1A;
            padding: 5px 12px;
            border-radius: 10px;
            margin: 4px;
            font-weight: 700;
        }

        .word-badge-error {
            display: inline-block;
            background-color: var(--dusty-pink);
            color: #FFFFFF;
            padding: 5px 12px;
            border-radius: 10px;
            margin: 4px;
            font-weight: 700;
        }

        /* Adaptación Responsive para Pantallas Pequeñas (Smartphones & Tablets) */
        @media (max-width: 768px) {
            .fluenty-header { padding: 1.2rem; }
            .fluenty-header h1 { font-size: 1.5rem; }
            .custom-card { padding: 15px; }
        }

        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_styles()

# ==========================================
# 2. CONFIGURACIÓN MQTT
# ==========================================
MQTT_BROKER = "broker.mqttdashboard.com"
MQTT_PORT = 1883
MQTT_TOPIC = "fluenty/controlvozz"

def publish_mqtt_event(action_name, payload_data):
    if HAS_VOICE_MQTT:
        try:
            client = paho.Client("Fluenty_Mobile_App")
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            message = json.dumps({"action": action_name, "data": payload_data})
            client.publish(MQTT_TOPIC, message)
            client.disconnect()
            return True
        except Exception:
            return False
    return False

# ==========================================
# 3. GESTIÓN DE ESTADO (SESSION STATE)
# ==========================================
if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = None

if "pdf_filename" not in st.session_state:
    st.session_state.pdf_filename = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "practice_text" not in st.session_state:
    st.session_state.practice_text = (
        "Language shapes the way we think and determines the things we can think about."
    )

# ==========================================
# 4. BARRA LATERAL (AUTENTICACIÓN & NAVEGACIÓN)
# ==========================================
with st.sidebar:
    st.markdown("## 🎙️ FLUENTY")
    st.caption("Asistente Multimodal de Idiomas | por Sebastián Botero")
    st.divider()

    ambiente = st.radio(
        "Selecciona el ambiente:",
        [
            "1. Asistente de Lectura (RAG + PDF)",
            "2. Laboratorio de Pronunciación (Voz + Hardware)"
        ]
    )

    st.divider()
    st.subheader("🔑 Autenticación OpenAI")
    api_key = st.text_input(
        "API Key",
        type="password",
        placeholder="sk-...",
        help="Requerida para el análisis RAG de lecturas universitarias."
    )

    if api_key:
        os.environ['OPENAI_API_KEY'] = api_key
        st.success("API Key vinculada 🟢")
    else:
        st.warning("Ingresa tu API Key para habilitar la IA completa 🟡")

    st.divider()
    st.subheader("📡 Conexión Wokwi (MQTT)")
    st.code(f"Broker: {MQTT_BROKER}\nTópico: {MQTT_TOPIC}", language="yaml")

# ==========================================
# 5. AMBIENTE 1: ASISTENTE DE LECTURA (RAG + PDF)
# ==========================================
if ambiente == "1. Asistente de Lectura (RAG + PDF)":
    st.markdown("""
    <div class="fluenty-header">
        <h1>Asistente de Lectura 📚</h1>
        <p>Carga tus lecturas académicas en PDF para desmenuzar conceptos, traducir párrafos y resolver dudas gramaticales.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="medium")

    with col1:
        st.subheader("📁 Cargar PDF Académico")
        pdf_file = st.file_uploader("Selecciona tu lectura en inglés", type=["pdf"])

        if pdf_file and api_key and HAS_RAG:
            if st.session_state.pdf_filename != pdf_file.name:
                try:
                    with st.spinner("Procesando e indexando el documento..."):
                        pdf_reader = PdfReader(pdf_file)
                        text = ""
                        for page in pdf_reader.pages:
                            extracted = page.extract_text()
                            if extracted:
                                text += extracted

                        text_splitter = CharacterTextSplitter(
                            separator="\n",
                            chunk_size=600,
                            chunk_overlap=50,
                            length_function=len
                        )
                        chunks = text_splitter.split_text(text)

                        embeddings = OpenAIEmbeddings()
                        st.session_state.knowledge_base = FAISS.from_texts(chunks, embeddings)
                        st.session_state.pdf_filename = pdf_file.name
                        st.success(f"¡Lectura indexada! ({len(chunks)} bloques procesados)")
                except Exception as e:
                    st.error("Ocurrió un error al procesar el archivo PDF.")
                    with st.expander("Detalle técnico del error"):
                        st.code(traceback.format_exc())

    with col2:
        st.subheader("💡 Ejemplos de Consultas")
        st.markdown("""
        <div class="custom-card card-blue">
            <ul>
                <li><i>"¿Cuál es el argumento central del autor en este capítulo?"</i></li>
                <li><i>"Explícame este párrafo complejo en español de forma sencilla."</i></li>
                <li><i>"¿Qué vocabulario clave debo dominar para debatir este tema?"</i></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Chat Interactivo
    st.subheader("💬 Consulta a tu Asistente")

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_question := st.chat_input("Escribe tu pregunta sobre la lectura..."):
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            if st.session_state.knowledge_base and api_key and HAS_RAG:
                with st.spinner("Analizando la lectura..."):
                    docs = st.session_state.knowledge_base.similarity_search(user_question, k=4)
                    context_text = "\n\n".join([doc.page_content for doc in docs])

                    llm = ChatOpenAI(temperature=0.2, model_name="gpt-4o-mini")
                    messages = [
                        ("system", "Eres Fluenty, un tutor de inglés y asistente académico. Responde la consulta en español explicando el texto en inglés de forma clara y accesible."),
                        ("user", f"Contexto de la lectura:\n{context_text}\n\nPregunta: {user_question}")
                    ]
                    response = llm.invoke(messages).content
                    st.markdown(response)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    publish_mqtt_event("query_processed", "SUCCESS")
            else:
                fallback_msg = "Por favor carga un archivo PDF e ingresa tu OpenAI API Key en la barra lateral para procesar consultas con inteligencia artificial."
                st.info(fallback_msg)
                st.session_state.chat_history.append({"role": "assistant", "content": fallback_msg})

# ==========================================
# 6. AMBIENTE 2: LABORATORIO DE PRONUNCIACIÓN (VOZ + HARDWARE)
# ==========================================
else:
    st.markdown("""
    <div class="fluenty-header">
        <h1>Laboratorio de Pronunciación 🎙️</h1>
        <p>Lee fragmentos en voz alta, evalúa tu fluidez en tiempo real y recibe retroalimentación física a través de Wokwi.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="custom-card card-green">
        <h3>📖 Texto a Practicar:</h3>
        <p style="font-size: 1.25rem; font-weight: 500; line-height: 1.6; color: #1A1A1A;">
            "{st.session_state.practice_text}"
        </p>
    </div>
    """, unsafe_allow_html=True)

    new_target = st.text_input("Editar o reemplazar texto a practicar:", value=st.session_state.practice_text)
    if new_target != st.session_state.practice_text:
        st.session_state.practice_text = new_target
        st.rerun()

    st.divider()

    col_mic, col_eval = st.columns([1, 1], gap="medium")

    with col_mic:
        st.subheader("1. Captura de Voz")
        st.write("Toca el botón a continuación y pronuncia la frase en voz alta:")

        if HAS_VOICE_MQTT:
            stt_button = Button(label="🎙️ Presionar para Hablar", width=280)
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
                key="speech_recognition",
                refresh_on_update=False,
                override_height=70,
                debounce_time=0
            )
        else:
            result = None
            st.warning("Librerías de voz no disponibles. Usa la entrada de texto de simulación.")

        simulated_voice = st.text_input(
            "O ingresa tu prueba de voz manual:",
            placeholder="Ejemplo: Language shapes the way we think..."
        )

    with col_eval:
        st.subheader("2. Evaluación de Fluidez")

        spoken_text = None
        if result and "GET_TEXT" in result:
            spoken_text = result.get("GET_TEXT")
        elif simulated_voice:
            spoken_text = simulated_voice

        if spoken_text:
            st.success(f"🗣️ Texto detectado: **\"{spoken_text}\"**")

            # Evaluación por similitud de palabras
            target_words = st.session_state.practice_text.lower().replace(".", "").replace(",", "").split()
            spoken_words = spoken_text.lower().replace(".", "").replace(",", "").split()

            score = SequenceMatcher(None, target_words, spoken_words).ratio() * 100

            if score >= 80:
                publish_mqtt_event("pronunciation_result", "GREEN")
                st.balloons()
                st.markdown("""
                <div class="custom-card card-green">
                    <h3 style="color: #2E7D32;">¡Excelente Fluidez! 🌟</h3>
                    <p>Tu pronunciación es adecuada y comprensible.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                publish_mqtt_event("pronunciation_result", "RED")
                st.markdown("""
                <div class="custom-card card-pink">
                    <h3 style="color: #C7859B;">Hay palabras por mejorar 💡</h3>
                    <p>Revisa la pronunciación de los términos resaltados.</p>
                </div>
                """, unsafe_allow_html=True)

            # Badges de palabras
            st.write("**Desglose de Términos:**")
            badges = ""
            for word in target_words:
                if word in spoken_words:
                    badges += f'<span class="word-badge-correct">✓ {word}</span> '
                else:
                    badges += f'<span class="word-badge-error">✗ {word}</span> '
            
            st.markdown(badges, unsafe_allow_html=True)
            st.metric("Puntaje de Coincidencia", f"{score:.1f}%")
        else:
            st.info("Esperando captura de voz o simulación...")
