import streamlit as st

def apply_custom_fonts_and_styles():
    st.markdown("""
        <style>
        /* 1. Importar Inter desde Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* 2. Cargar la fuente local Sunborn para títulos */
        @font-face {
            font-family: 'Sunborn';
            src: url('app/static/Sunborn.woff2') format('woff2'),
                 url('app/static/Sunborn.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }

        /* Tipografía general del cuerpo (Inter) */
        html, body, [class*="css"], .stMarkdown, p, span, label, div {
            font-family: 'Inter', sans-serif !important;
            color: #1A1A1A;
        }

        /* Tipografía de títulos (Sunborn) */
        h1, h2, h3, .stTitle, .stHeader {
            font-family: 'Sunborn', 'Inter', sans-serif !important;
            letter-spacing: 0.5px;
        }
        </style>
    """, unsafe_allow_html=True)

apply_custom_fonts_and_styles()
