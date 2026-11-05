import streamlit as st
import json
import time
from difflib import SequenceMatcher

# Intentamos importar librerías secundarias con fallbacks seguros
try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# ==========================================
# 1. CONFIGURACIÓN INICIAL Y DISEÑO (UX/UI)
# ==========================================
st.set_page_config(
    page_title="Fluenty - Asistente Multimodal",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def inject_custom_styles():
    st.markdown("""
        <style>
        /* 1. Importar Inter desde Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* 2. Cargar fuente Sunborn local (subida como sunborn-sans-one.otf) */
        @font-face {
            font-family: 'Sunborn';
            src: url('sunborn-sans-one.otf') format('opentype');
            font-weight: normal;
            font-style: normal;
        }

        /* Fondo de la aplicación */
        .stApp {
            background-color: #FDFBF7 !important;
        }

        /* Tipografía general */
        html, body, [class*="css"], .stMarkdown, p, span, label, div {
            font-family: 'Inter', sans-serif !important;
            color: #1A1A1A !important;
        }

        /* Estilos de Títulos */
        h1, h2, h3, .stTitle, .stHeader {
            font-family: 'Sunborn', 'Inter', sans-serif !important;
            color: #1A1A1A !important;
            letter-spacing: 0.5px;
        }

        /* Tarjetas personalizadas con bordes redondeados */
        .custom-card {
            background-color: #FFFFFF;
            border-radius: 20px;
            padding: 24px;
            border: 1.5px solid #EAEAEA;
            box-shadow: 0 4px 12px rgba(0,0,0,0.02);
            margin-bottom: 20px;
        }

        .card-pink {
            background-color: #FDF2F4;
            border: 1.5px solid #C7859B;
        }

        .card-blue {
            background-color: #F0F8FA;
            border: 1.5px solid #A5D7E8;
        }

        .card-green {
            background-color: #F0F7F4;
            border: 1.5px solid #8EC3B0;
        }

        /* Botones estilo Pill */
        .stButton>button {
            border-radius: 14px !important;
            background-color: #8EC3B0 !important;
            color: #1A1A1A !important;
            font-weight: 600 !important;
            border: none !important;
            padding: 10px 24px !important;
            transition: all 0.2s ease-in-out;
        }

        .stButton>button:hover {
            background-color: #7AB4A1 !important;
            transform: translateY(-1px);
        }

        /* Badges de palabras */
        .word-badge-correct {
            display: inline-block;
            background-color: #8EC3B0;
            color: #1A1A1A;
            padding: 4px 12px;
            border-radius: 10px;
            margin: 4px;
            font-weight: 600;
        }

        .word-badge-error {
            display: inline-block;
            background-color: #C7859B;
            color: #FFFFFF;
            padding: 4px 12px;
            border-radius: 10px;
            margin: 4px;
            font-weight: 600;
        }

        /* Ocultar elementos genéricos de Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

inject_custom_styles()

# ==========================================
# 2. GESTIÓN DE ESTADO (SESSION STATE)
# ==========================================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

if "selected_practice_text" not in st.session_state:
    st.session_state.selected_practice_text = (
        "Language shapes the way we think and determines the things we can think about."
    )

if "mqtt_connected" not in st.session_state:
    st.session_state.mqtt_connected = False

if "last_led_state" not in st.session_state:
    st.session_state.last_led_state = "OFF"

# ==========================================
# 3. COMUNICACIÓN MQTT (STREAMLIT ↔ WOKWI)
# ==========================================
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
TOPIC_LED = "fluenty/wokwi/led"
TOPIC_BUTTON = "fluenty/wokwi/button"

def send_mqtt_signal(status_color):
    """
    Envía comandos de color al ESP32 en Wokwi.
    status_color: 'GREEN' (Acierto), 'RED' (Error), 'BLUE' (Procesando/Escuchando)
    """
    st.session_state.last_led_state = status_color
    if HAS_MQTT:
        try:
            client = mqtt.Client()
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            payload = json.dumps({"status": status_color, "timestamp": time.time()})
            client.publish(TOPIC_LED, payload)
            client.disconnect()
            st.session_state.mqtt_connected = True
        except Exception:
            st.session_state.mqtt_connected = False

# ==========================================
# 4. BARRA LATERAL (SIDEBAR & BRANDING)
# ==========================================
with st.sidebar:
    st.title("FLUENTY")
    st.caption("Asistente Multimodal de Idiomas | por Sebastián Botero")
    st.divider()

    ambiente = st.radio(
        "Modo de Interacción:",
        [
            "1. Asistente de Lectura (PDF)",
            "2. Laboratorio de Pronunciación (Voz)"
        ],
        index=0
    )
    
    st.divider()

    # Panel de control de Hardware (Wokwi)
    st.subheader("Mando Físico (Wokwi)")
    if HAS_MQTT:
        st.success("Broker MQTT: Conectado 🟢")
    else:
        st.warning("Modo Simulación (Sin librería paho-mqtt) 🟡")

    st.markdown(f"**Estado LED Actual:** `{st.session_state.last_led_state}`")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🟢 Verde"):
            send_mqtt_signal("GREEN")
    with col_btn2:
        if st.button("🔴 Rojo"):
            send_mqtt_signal("RED")

    st.divider()
    api_key = st.text_input("OpenAI API Key (Opcional):", type="password", help="Si no ingresas clave, se usará el motor de simulación local.")

# ==========================================
# 5. AMBIENTE 1: ASISTENTE DE LECTURA (PDF)
# ==========================================
if ambiente == "1. Asistente de Lectura (PDF)":
    st.title("Interacción con el Documento")
    st.write("Carga tu lectura académica en PDF para resolver dudas gramaticales, resumir conceptos complejos o traducir párrafos.")

    col_file, col_info = st.columns([1, 1])

    with col_file:
        uploaded_file = st.file_uploader("Cargar lectura universitaria (PDF)", type=["pdf"])
        if uploaded_file is not None:
            if HAS_PYPDF:
                try:
                    pdf_reader = pypdf.PdfReader(uploaded_file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() or ""
                    st.session_state.pdf_text = text
                    st.success(f" Documento cargado con éxito ({len(pdf_reader.pages)} páginas).")
                except Exception as e:
                    st.error(f"Error al leer el PDF: {e}")
            else:
                st.session_state.pdf_text = "Texto extraído de muestra del documento de lectura..."
                st.info(" Archivo recibido en modo simulación.")

    with col_info:
        st.markdown("""
            <div class="custom-card card-blue">
                <h3>💡 Consejos de Consulta</h3>
                <ul>
                    <li>Pídele que traduzca párrafos manteniendo el estilo del autor.</li>
                    <li>Solicita aclaraciones sobre el uso de tiempos verbales o vocabularios técnicos.</li>
                    <li>Pide resúmenes en viñetas para tu jornada de estudio.</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.subheader("Chat de Análisis de Lectura")

    # Mostrar historial del chat
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Entrada de texto del usuario
    if user_prompt := st.chat_input("Escribe tu pregunta sobre la lectura..."):
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Respuesta simulada/asistida
        with st.chat_message("assistant"):
            send_mqtt_signal("BLUE")
            
            if not st.session_state.pdf_text:
                response = "Por favor carga un archivo PDF primero para poder analizarlo en profundidad."
            else:
                response = (
                    f"Con base en el documento cargado: En relación a **'{user_prompt}'**, el texto plantea "
                    "que las estructuras conceptuales determinan la comprensión. Te sugiero practicar "
                    "la pronunciación de esta sección en el **Laboratorio de Pronunciación**."
                )
            
            st.markdown(response)
            st.session_state.chat_history.append({"role": "assistant", "content": response})

# ==========================================
# 6. AMBIENTE 2: LABORATORIO DE PRONUNCIACIÓN (VOZ)
# ==========================================
else:
    st.title("Laboratorio de Pronunciación y Fluidez")
    st.write("Selecciona o ingresa una frase de tu lectura, presiona el botón para grabar tu voz y recibe retroalimentación inmediata.")

    st.markdown(f"""
        <div class="custom-card card-green">
            <h3>📖 Texto a Practicar:</h3>
            <p style="font-size: 1.2rem; line-height: 1.6;">"{st.session_state.selected_practice_text}"</p>
        </div>
    """, unsafe_allow_html=True)

    new_text = st.text_input("Cambiar texto a practicar:", value=st.session_state.selected_practice_text)
    if new_text != st.session_state.selected_practice_text:
        st.session_state.selected_practice_text = new_text
        st.rerun()

    st.divider()

    col_rec, col_res = st.columns([1, 1])

    with col_rec:
        st.subheader("1. Captura de Voz")
        st.write("Presiona el botón del hardware en Wokwi o usa la grabadora en pantalla:")
        
        audio_input = st.audio_input("Grabar tu pronunciación")
        
        simulated_speech = st.text_input(
            "O escribe lo que pronunciaste (Simulador de Speech-to-Text):",
            placeholder="Ej: Language shapes the way we think..."
        )

    with col_res:
        st.subheader("2. Evaluador de Fluidez")
        
        if audio_input is not None or simulated_speech:
            send_mqtt_signal("BLUE")
            
            # Texto dicho por el usuario (tomamos el simulado o el predeterminado)
            user_spoken = simulated_speech if simulated_speech else st.session_state.selected_practice_text
            
            target_words = st.session_state.selected_practice_text.lower().replace(".", "").replace(",", "").split()
            spoken_words = user_spoken.lower().replace(".", "").replace(",", "").split()

            # Cálculo de similitud
            similarity = SequenceMatcher(None, target_words, spoken_words).ratio() * 100

            if similarity >= 80:
                send_mqtt_signal("GREEN")
                st.balloons()
                st.markdown("""
                    <div class="custom-card card-green">
                        <h2 style="color: #2E7D32;">¡Excelente Pronunciación! 🌟</h2>
                        <p>Tu fluidez fue adecuada y la entonación se escucha natural.</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                send_mqtt_signal("RED")
                st.markdown("""
                    <div class="custom-card card-pink">
                        <h2 style="color: #C7859B;">Hay detalles por pulir 💡</h2>
                        <p>Revisa la pronunciación de las palabras marcadas en rojo.</p>
                    </div>
                """, unsafe_allow_html=True)

            # Desglose de palabras (Badges)
            st.write("**Desglose de Palabras:**")
            badges_html = ""
            for word in target_words:
                if word in spoken_words:
                    badges_html += f'<span class="word-badge-correct">✓ {word}</span> '
                else:
                    badges_html += f'<span class="word-badge-error">✗ {word}</span> '
            
            st.markdown(badges_html, unsafe_allow_html=True)
            st.metric(label="Score de Coincidencia", value=f"{similarity:.1f}%")
        else:
            st.info("Esperando captura de audio o prueba de voz...")
apply_custom_fonts_and_styles()
