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
# 3. CSS (LÍNEA GRÁFICA & PROTECCIÓN MODO OSCURO)
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
# 4. FUNCIONES MQTT
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
# 6. BANNER Y CAMPO DE API KEY EN PANTALLA PRINCIPAL
