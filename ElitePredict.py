import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import json
import time

# Configurazione pagina per mobile
st.set_page_config(
    page_title="Predizioni Calcio",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS per ottimizzazione mobile
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0px 12px;
        background-color: #f0f2f6;
        border-radius: 8px;
        color: #262730;
        font-size: 16px;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #ff6b35 !important;
        color: white !important;
    }
    
    .metric-card {
    background: white;
    padding: 25px;
    border-radius: 16px;
    color: #1e293b;
    text-align: center;
    margin: 10px 0;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    border: 1px solid #e2e8f0;
    transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 30px rgba(102, 126, 234, 0.15);
    }
    
    .metric-card h3 {
        color: #64748b;
        font-size: 0.9rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }
    
    .metric-card h2 {
        color: #667eea;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    
    .metric-card p {
        color: #94a3b8;
        font-size: 0.85rem;
    }
    
    .prediction-card {
    background: white;
    padding: 25px;
    border-radius: 16px;
    border-left: 5px solid #667eea;
    margin: 20px 0;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .prediction-card:hover {
        transform: translateX(5px);
        box-shadow: 0 8px 30px rgba(102, 126, 234, 0.15);
    }
    
    .prediction-card h3 {
        color: #1e293b;
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 0.8rem;
    }
    
    .prediction-card p {
        color: #64748b;
        font-size: 0.95rem;
        margin: 0.3rem 0;
    }
    
    .live-score {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 15px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin: 10px 0;
        font-weight: bold;
        box-shadow: 0 6px 20px rgba(0,0,0,0.1);
    }
    
    .status-badge {
    display: inline-block;
    padding: 8px 16px;
    border-radius: 50px;
    font-size: 0.8rem;
    font-weight: 600;
    margin: 5px 5px 5px 0;
    letter-spacing: 0.3px;
    text-transform: uppercase;
    }
    
    .status-correct {
        background-color: #d1fae5;
        color: #065f46;
        border: 1px solid #6ee7b7;
    }
    
    .status-incorrect {
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #fca5a5;
    }
    
    .status-pending {
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #fcd34d;
    }
    
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: #f8fafc;
        padding: 8px;
        border-radius: 12px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 55px;
            padding: 0px 24px;
            background-color: white;
            border-radius: 10px;
            color: #64748b;
            font-size: 16px;
            font-weight: 600;
            border: 2px solid transparent;
            transition: all 0.2s;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #f1f5f9;
            border-color: #cbd5e1;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border-color: transparent !important;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
    }
</style>
""", unsafe_allow_html=True)

import re
from urllib.parse import urlparse, parse_qs, unquote

def parse_sheet_url(url: str):
    """
    Estrae automaticamente sheet_id e gid da un Google Sheets URL.
    Restituisce (sheet_id, gid_or_None).
    """
    url = (url or "").strip()
    parsed = urlparse(url)

    # 1) Prova ad ottenere l'id dal percorso /d/<id>/
    m = re.search(r'/d/([a-zA-Z0-9-_]+)', parsed.path)
    if m:
        sheet_id = m.group(1)
    else:
        # 2) Prova a trovare id nella query (es. ?id=<id>)
        qs = parse_qs(parsed.query)
        id_list = qs.get('id') or qs.get('spreadsheetId')
        if id_list:
            sheet_id = id_list[0]
        else:
            # 3) Cerca nell'fragment
            frag = unquote(parsed.fragment or "")
            m2 = re.search(r'id=([a-zA-Z0-9-_]+)', frag)
            if m2:
                sheet_id = m2.group(1)
            else:
                raise ValueError("Impossibile trovare lo sheet id nell'URL fornito.")

    # Estrai il gid (può essere in query o nel fragment)
    qs = parse_qs(parsed.query)
    gid = None
    if 'gid' in qs:
        gid = qs['gid'][0]
    else:
        frag = unquote(parsed.fragment or "")
        m_gid = re.search(r'gid=(\d+)', frag)
        if m_gid:
            gid = m_gid.group(1)
        else:
            m_gid2 = re.search(r'gid[:=](\d+)', frag)
            if m_gid2:
                gid = m_gid2.group(1)

    return sheet_id, gid

def make_csv_export_url(sheet_id: str, gid: str | None = None) -> str:
    """
    Costruisce l'URL di esportazione CSV per Google Sheets.
    """
    if gid:
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    else:
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"


@st.cache_data(ttl=300)  # Cache per 5 minuti
def load_data():
    """
    Carica i dati dal Google Sheets convertendo l'URL in formato CSV.
    Ora rileva automaticamente sheet_id e gid dall'URL.
    """

    import os
    google_sheets_url = os.getenv('GOOGLE_SHEETS_URL', 'https://esempio-fallback.com')

    # Verifica che l'URL sia stato configurato
    if google_sheets_url == 'https://esempio-fallback.com':
        st.error("⚠️ URL Google Sheets non configurato. Imposta la variabile d'ambiente GOOGLE_SHEETS_URL")
        st.info("💡 Consulta la documentazione per configurare l'accesso ai dati")
        st.stop()
    
    try:
        # Estrae lo sheet_id e il gid dall'URL
        sheet_id, gid = parse_sheet_url(google_sheets_url)
        
        # Costruisce l'URL CSV
        csv_url = make_csv_export_url(sheet_id, gid)
        
        # Legge i dati dal CSV
        df = pd.read_csv(csv_url)
        
        # Pulizia e preprocessing dei dati
        df.columns = df.columns.str.strip()
        
        # Converte le date in formato corretto se necessario
        if 'Data predizione' in df.columns:
            df['Data predizione'] = pd.to_datetime(df['Data predizione'], format='%d/%m/%Y', errors='coerce')
        if 'Data partita' in df.columns:
            df['Data partita'] = pd.to_datetime(df['Data partita'], format='%d/%m/%Y', errors='coerce')
        
        # Rimuove righe completamente vuote
        df = df.dropna(how='all')
        
        # Sostituisce NaN con stringhe vuote per alcune colonne
        text_columns = ['Risultato secco reale', 'Risultato predizione (risultato secco)', 
                       'Risultato predizione (doppia chance)']
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].fillna('Da giocare')
                
        return df
        
    except Exception as e:
        st.error(f"❌ Errore nel caricamento dei dati: {str(e)}")
        st.info("🔄 Utilizzo dati di esempio per il test dell'app...")
        
        # Fallback con dati di esempio in caso di errore
        data = {
            'Data predizione': pd.to_datetime(['23/8/2025', '23/8/2025', '24/8/2025', '24/8/2025', '25/8/2025'], format='%d/%m/%Y'),
            'Squadra casa': ['Manchester City', 'Bournemouth', 'Arsenal', 'Liverpool', 'Chelsea'],
            'Squadra ospite': ['Tottenham', 'Wolves', 'Brighton', 'Crystal Palace', 'Newcastle'],
            'Risultato secco previsto': ['1', '1', '1', '1', '1'],
            'Risultato secco reale': ['2', '1', '', '', ''],
            'Doppia chance prevista': ['12', '1X', '1X', '12', '1X'],
            'Confidence': ['Alta', 'Media', 'Alta', 'Media', 'Bassa'],
            'Risultato predizione (risultato secco)': ['Errato', 'Corretto', 'Da giocare', 'Da giocare', 'Da giocare'],
            'Risultato predizione (doppia chance)': ['Corretto', 'Corretto', 'Da giocare', 'Da giocare', 'Da giocare'],
            'Giornata': [2, 2, 3, 3, 3],
            'Campionato': ['Premier League'] * 5,
            'Data partita': pd.to_datetime(['23/8/2025', '23/8/2025', '24/8/2025', '24/8/2025', '25/8/2025'], format='%d/%m/%Y')
        }
        return pd.DataFrame(data)

# Caricamento dati
df = load_data()

# Debug info (mostra solo in sviluppo)
if st.sidebar.button("🔧 Debug Info"):
    st.sidebar.write("**Colonne disponibili:**")
    st.sidebar.write(df.columns.tolist())
    st.sidebar.write("**Dimensioni dataset:**", df.shape)
    st.sidebar.write("**Prime 3 righe:**")
    st.sidebar.write(df.head(3))
    
    # Info sui valori nelle colonne chiave
    if 'Risultato predizione (risultato secco)' in df.columns:
        st.sidebar.write("**Valori 'Risultato secco':**")
        st.sidebar.write(df['Risultato predizione (risultato secco)'].value_counts())
    
    if 'Risultato predizione (doppia chance)' in df.columns:
        st.sidebar.write("**Valori 'Doppia chance':**")
        st.sidebar.write(df['Risultato predizione (doppia chance)'].value_counts())

# Styling sidebar professionale
st.sidebar.markdown("""
<div style="
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1.5rem 1rem;
    border-radius: 15px;
    margin-bottom: 1.5rem;
    text-align: center;
">
    <h2 style="color: white; margin: 0; font-size: 1.5rem;">⚙️ Filters</h2>
</div>
""", unsafe_allow_html=True)

# Header professionale con gradient e shadow
st.markdown("""
<div style="
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem 1rem;
    border-radius: 20px;
    margin-bottom: 2rem;
    box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
    text-align: center;
">
    <h1 style="color: white; margin: 0; font-size: 2.5rem; font-weight: 700; letter-spacing: -1px;">
        ⚽ Football Predictions Dashboard
    </h1>
    <p style="color: rgba(255,255,255,0.9); margin-top: 0.5rem; font-size: 1.1rem;">
        AI-Powered Match Analysis & Forecasting
    </p>
</div>
""", unsafe_allow_html=True)

# Filtri globali
# Filtri nella sidebar
st.sidebar.markdown("## 📅 Filtri")

# Data minima e massima disponibili
if 'Data partita' in df.columns and not df['Data partita'].isna().all():
    min_date = df['Data partita'].min().date()
    max_date = df['Data partita'].max().date()
else:
    min_date = datetime.now().date()
    max_date = datetime.now().date() + timedelta(days=30)

# Imposta il valore di default del filtro come la data minima disponibile
default_date = min_date
    
selected_date = st.sidebar.date_input(
    "Seleziona data partite:",
    value=default_date,
    min_value=min_date,
    max_value=max_date,
    help="Filtra le partite da questa data in poi"
)

only_selected_date = st.sidebar.checkbox(
    "Solo questa data", 
    value=False, 
    help="Se selezionato mostra solo le partite di questa data, altrimenti da questa data in poi"
)
show_all = st.sidebar.checkbox("Mostra tutte le date", value=False, help="Ignora il filtro data e mostra tutte le partite")

# Filtro campionato
available_leagues = ['Tutti'] + sorted(df['Campionato'].dropna().unique().tolist())
selected_league = st.sidebar.selectbox(
    "Campionato:",
    options=available_leagues,
    index=0,
    help="Filtra per campionato specifico"
)

# Applica filtri data e campionato
df_base = df.copy()

# Filtro campionato
if selected_league != 'Tutti':
    df_base = df_base[df_base['Campionato'] == selected_league]

# Filtro data
if not show_all and 'Data partita' in df_base.columns:
    if only_selected_date:
        # Mostra solo partite della data selezionata
        df_filtered = df_base[df_base['Data partita'].dt.date == selected_date].copy()
        filter_info = f"del {selected_date.strftime('%d/%m/%Y')}"
    else:
        # Mostra partite dalla data selezionata in poi
        df_filtered = df_base[df_base['Data partita'].dt.date >= selected_date].copy()
        filter_info = f"dal {selected_date.strftime('%d/%m/%Y')} in poi"
    
    if len(df_filtered) == 0:
        st.warning(f"⚠️ Nessuna partita trovata {filter_info}" + (f" per {selected_league}" if selected_league != 'Tutti' else ""))
        st.info("💡 Prova a selezionare una data diversa, un altro campionato o attiva 'Mostra tutte le date'")
else:
    df_filtered = df_base.copy()
    filter_info = "tutte le date"

# Info filtro applicato
league_info = f" - {selected_league}" if selected_league != 'Tutti' else ""
    
st.markdown("""
<div style="
    height: 2px;
    background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
    margin: 2rem 0;
"></div>
""", unsafe_allow_html=True)

# Tabs principali
# Calcola il numero di partite da giocare per il badge
upcoming_count = len(df_filtered[
    (df_filtered['Risultato predizione (risultato secco)'] == 'Da giocare') |
    (df_filtered['Risultato predizione (doppia chance)'] == 'Da giocare')
])

tab1, tab2, tab3, tab4 = st.tabs(["📊 Statistiche", "📋 Storico Predizioni", f"🔴 Predizioni Future ({upcoming_count})", "🤖 Come Funzionano"])

with tab1:
    # Nuova sezione Statistiche
    st.markdown("## 📊 Statistiche Generali")
    
    # Usa df_filtered per rispettare i filtri data e campionato
    completed_filtered = df_filtered[
        (df_filtered['Risultato predizione (risultato secco)'] != 'Da giocare') &
        (df_filtered['Risultato predizione (doppia chance)'] != 'Da giocare')
    ]
    
    if len(completed_filtered) > 0:
        # KPI principali - 2 righe con 3 colonne ciascuna
        st.markdown("### 📈 Metriche Principali")
        
        # Prima riga - Risultato Secco
        col1, col2, col3 = st.columns(3)
        
        total_matches = len(completed_filtered)
        correct_exact = len(completed_filtered[completed_filtered['Risultato predizione (risultato secco)'] == 'Corretto'])
        accuracy_exact = (correct_exact / total_matches) * 100
        wrong_exact = total_matches - correct_exact
        
        with col1:
            st.markdown(f"""
            <div style="
                background: white;
                padding: 25px 20px;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                border-top: 4px solid #667eea;
                text-align: center;
                transition: transform 0.2s, box-shadow 0.2s;
            " onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 8px 30px rgba(102,126,234,0.15)';" 
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 20px rgba(0,0,0,0.08)';">
                <div style="
                    color: #64748b;
                    font-size: 0.85rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 8px;
                ">
                    🎯 Risultato Secco
                </div>
                <div style="
                    color: #667eea;
                    font-size: 2.8rem;
                    font-weight: 700;
                    margin: 10px 0;
                    line-height: 1;
                ">
                    {accuracy_exact:.1f}%
                </div>
                <div style="
                    color: #94a3b8;
                    font-size: 0.9rem;
                    font-weight: 500;
                ">
                    Accuratezza
                </div>
            </div>
            """, unsafe_allow_html=True)
                
        with col2:
            st.markdown(f"""
            <div style="
                background: white;
                padding: 25px 20px;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                border-top: 4px solid #10b981;
                text-align: center;
                transition: transform 0.2s, box-shadow 0.2s;
            " onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 8px 30px rgba(16,185,129,0.15)';" 
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 20px rgba(0,0,0,0.08)';">
                <div style="
                    color: #64748b;
                    font-size: 0.85rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 8px;
                ">
                    ✅ Corrette
                </div>
                <div style="
                    color: #10b981;
                    font-size: 2.8rem;
                    font-weight: 700;
                    margin: 10px 0;
                    line-height: 1;
                ">
                    {correct_exact}
                </div>
                <div style="
                    color: #94a3b8;
                    font-size: 0.9rem;
                    font-weight: 500;
                ">
                    predizioni
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="
                background: white;
                padding: 25px 20px;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                border-top: 4px solid #ef4444;
                text-align: center;
                transition: transform 0.2s, box-shadow 0.2s;
            " onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 8px 30px rgba(239,68,68,0.15)';" 
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 20px rgba(0,0,0,0.08)';">
                <div style="
                    color: #64748b;
                    font-size: 0.85rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 8px;
                ">
                    ❌ Errate
                </div>
                <div style="
                    color: #ef4444;
                    font-size: 2.8rem;
                    font-weight: 700;
                    margin: 10px 0;
                    line-height: 1;
                ">
                    {wrong_exact}
                </div>
                <div style="
                    color: #94a3b8;
                    font-size: 0.9rem;
                    font-weight: 500;
                ">
                    predizioni
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Seconda riga - Doppia Chance
        col1, col2, col3 = st.columns(3)
        
        correct_double = len(completed_filtered[completed_filtered['Risultato predizione (doppia chance)'] == 'Corretto'])
        accuracy_double = (correct_double / total_matches) * 100 if total_matches > 0 else 0
        wrong_double = total_matches - correct_double
        
        with col1:
            st.markdown(f"""
            <div style="
                background: white;
                padding: 25px 20px;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                border-top: 4px solid #3b82f6;
                text-align: center;
                transition: transform 0.2s, box-shadow 0.2s;
            " onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 8px 30px rgba(59,130,246,0.15)';" 
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 20px rgba(0,0,0,0.08)';">
                <div style="
                    color: #64748b;
                    font-size: 0.85rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 8px;
                ">
                    🎲 Doppia Chance
                </div>
                <div style="
                    color: #3b82f6;
                    font-size: 2.8rem;
                    font-weight: 700;
                    margin: 10px 0;
                    line-height: 1;
                ">
                    {accuracy_double:.1f}%
                </div>
                <div style="
                    color: #94a3b8;
                    font-size: 0.9rem;
                    font-weight: 500;
                ">
                    Accuratezza
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="
                background: white;
                padding: 25px 20px;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                border-top: 4px solid #10b981;
                text-align: center;
                transition: transform 0.2s, box-shadow 0.2s;
            " onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 8px 30px rgba(16,185,129,0.15)';" 
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 20px rgba(0,0,0,0.08)';">
                <div style="
                    color: #64748b;
                    font-size: 0.85rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 8px;
                ">
                    ✅ Corrette
                </div>
                <div style="
                    color: #10b981;
                    font-size: 2.8rem;
                    font-weight: 700;
                    margin: 10px 0;
                    line-height: 1;
                ">
                    {correct_double}
                </div>
                <div style="
                    color: #94a3b8;
                    font-size: 0.9rem;
                    font-weight: 500;
                ">
                    predizioni
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="
                background: white;
                padding: 25px 20px;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                border-top: 4px solid #ef4444;
                text-align: center;
                transition: transform 0.2s, box-shadow 0.2s;
            " onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 8px 30px rgba(239,68,68,0.15)';" 
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 20px rgba(0,0,0,0.08)';">
                <div style="
                    color: #64748b;
                    font-size: 0.85rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 8px;
                ">
                    ❌ Errate
                </div>
                <div style="
                    color: #ef4444;
                    font-size: 2.8rem;
                    font-weight: 700;
                    margin: 10px 0;
                    line-height: 1;
                ">
                    {wrong_double}
                </div>
                <div style="
                    color: #94a3b8;
                    font-size: 0.9rem;
                    font-weight: 500;
                ">
                    predizioni
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="
            height: 2px;
            background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
            margin: 2rem 0;
        "></div>
        """, unsafe_allow_html=True)
        
        # Statistiche per campionato
        st.markdown("### 🏆 Performance per Campionato")
        
        league_stats_exact = completed_filtered.groupby('Campionato').agg({
            'Risultato predizione (risultato secco)': [
                ('Totale', 'count'),
                ('Corrette Secco', lambda x: (x == 'Corretto').sum()),
                ('Accuratezza Secco %', lambda x: (x == 'Corretto').sum() / len(x) * 100)
            ]
        }).round(1)
        
        league_stats_double = completed_filtered.groupby('Campionato').agg({
            'Risultato predizione (doppia chance)': [
                ('Corrette Doppia', lambda x: (x == 'Corretto').sum()),
                ('Accuratezza Doppia %', lambda x: (x == 'Corretto').sum() / len(x) * 100)
            ]
        }).round(1)
        
        league_stats = pd.concat([league_stats_exact, league_stats_double], axis=1)
        league_stats.columns = ['Totale Partite', 'Corrette Secco', 'Accuratezza Secco %', 'Corrette Doppia', 'Accuratezza Doppia %']
        league_stats = league_stats.sort_values('Accuratezza Secco %', ascending=False)
        
        st.dataframe(league_stats, use_container_width=True)
        
        st.markdown("""
        <div style="
            height: 2px;
            background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
            margin: 2rem 0;
        "></div>
        """, unsafe_allow_html=True)
        
        # Statistiche per Status Merged
        st.markdown("### ⚖️ Performance per Tipo Sfida")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'Status Merged' in completed_filtered.columns:
                status_stats_exact = completed_filtered.groupby('Status Merged').agg({
                    'Risultato predizione (risultato secco)': [
                        ('Accuratezza', lambda x: (x == 'Corretto').sum() / len(x) * 100),
                        ('Totale', 'count'),
                        ('Corrette', lambda x: (x == 'Corretto').sum())
                    ]
                }).round(1)
                status_stats_exact.columns = ['Accuratezza', 'Totale', 'Corrette']
                status_stats_exact = status_stats_exact.reset_index()
                
                fig = px.bar(
                    status_stats_exact,
                    x='Status Merged',
                    y='Accuratezza',
                    title='Accuratezza per Tipo Sfida (Risultato Secco)',
                    labels={'Accuratezza': 'Accuratezza %', 'Status Merged': 'Tipo Sfida'},
                    color='Accuratezza',
                    color_continuous_scale='RdYlGn',
                    hover_data={
                        'Accuratezza': ':.1f',
                        'Totale': True,
                        'Corrette': True
                    }
                )
                fig.update_traces(
                    hovertemplate='<b>%{x}</b><br>Accuratezza: %{y:.1f}%<br>Corrette: %{customdata[1]}<br>Totale: %{customdata[0]}<extra></extra>'
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'Status Merged' in completed_filtered.columns:
                status_stats_double = completed_filtered.groupby('Status Merged').agg({
                    'Risultato predizione (doppia chance)': [
                        ('Accuratezza', lambda x: (x == 'Corretto').sum() / len(x) * 100),
                        ('Totale', 'count'),
                        ('Corrette', lambda x: (x == 'Corretto').sum())
                    ]
                }).round(1)
                status_stats_double.columns = ['Accuratezza', 'Totale', 'Corrette']
                status_stats_double = status_stats_double.reset_index()
                
                fig = px.bar(
                    status_stats_double,
                    x='Status Merged',
                    y='Accuratezza',
                    title='Accuratezza per Tipo Sfida (Doppia Chance)',
                    labels={'Accuratezza': 'Accuratezza %', 'Status Merged': 'Tipo Sfida'},
                    color='Accuratezza',
                    color_continuous_scale='Blues',
                    hover_data={
                        'Accuratezza': ':.1f',
                        'Totale': True,
                        'Corrette': True
                    }
                )
                fig.update_traces(
                    hovertemplate='<b>%{x}</b><br>Accuratezza: %{y:.1f}%<br>Corrette: %{customdata[1]}<br>Totale: %{customdata[0]}<extra></extra>'
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("""
        <div style="
            height: 2px;
            background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
            margin: 2rem 0;
        "></div>
        """, unsafe_allow_html=True)

        # Styling tabella
        st.markdown("""
        <style>
            .dataframe {
                font-size: 0.9rem;
                border-radius: 12px;
                overflow: hidden;
            }
            .dataframe th {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                font-weight: 600;
                padding: 12px;
            }
            .dataframe td {
                padding: 10px;
                border-bottom: 1px solid #e2e8f0;
            }
            .dataframe tr:hover {
                background-color: #f8fafc;
            }
        </style>
        """, unsafe_allow_html=True)

        # Grafico confidence
        st.markdown("### 💪 Performance per Livello Confidence")
        
        confidence_stats = completed_filtered.groupby('Confidence').agg({
            'Risultato predizione (risultato secco)': lambda x: (x == 'Corretto').sum() / len(x) * 100,
            'Risultato predizione (doppia chance)': lambda x: (x == 'Corretto').sum() / len(x) * 100
        }).round(1).reset_index()
        
        # Ordina per livello di confidence
        confidence_order = {'Bassa': 0, 'Media': 1, 'Alta': 2}
        confidence_stats['order'] = confidence_stats['Confidence'].map(confidence_order)
        confidence_stats = confidence_stats.sort_values('order').drop('order', axis=1)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='Risultato Secco',
            x=confidence_stats['Confidence'],
            y=confidence_stats['Risultato predizione (risultato secco)'],
            marker_color='#ff6b35'
        ))
        fig.add_trace(go.Bar(
            name='Doppia Chance',
            x=confidence_stats['Confidence'],
            y=confidence_stats['Risultato predizione (doppia chance)'],
            marker_color='#4facfe'
        ))
        
        fig.update_layout(
            title='Accuratezza per Livello Confidence',
            xaxis_title='Livello Confidence',
            yaxis_title='Accuratezza (%)',
            barmode='group',
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("""
        <div style="
            height: 2px;
            background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
            margin: 2rem 0;
        "></div>
        """, unsafe_allow_html=True)
        
        # Trend temporale
        st.markdown("### 📈 Trend Accuratezza nel Tempo")
        
        if 'Data partita' in completed_filtered.columns:
            weekly_stats = completed_filtered.copy()
            weekly_stats['Settimana'] = pd.to_datetime(weekly_stats['Data partita']).dt.to_period('W').astype(str)
            
            weekly_accuracy = weekly_stats.groupby('Settimana').agg({
                'Risultato predizione (risultato secco)': lambda x: (x == 'Corretto').sum() / len(x) * 100,
                'Risultato predizione (doppia chance)': lambda x: (x == 'Corretto').sum() / len(x) * 100
            }).reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=weekly_accuracy['Settimana'],
                y=weekly_accuracy['Risultato predizione (risultato secco)'],
                mode='lines+markers',
                name='Risultato Secco',
                line=dict(color='#ff6b35', width=3)
            ))
            fig.add_trace(go.Scatter(
                x=weekly_accuracy['Settimana'],
                y=weekly_accuracy['Risultato predizione (doppia chance)'],
                mode='lines+markers',
                name='Doppia Chance',
                line=dict(color='#4facfe', width=3)
            ))
            
            fig.update_layout(
                title='Accuratezza Settimanale',
                xaxis_title='Settimana',
                yaxis_title='Accuratezza (%)',
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.info("📊 Nessun dato disponibile per generare statistiche con i filtri selezionati. Prova a modificare i filtri o attiva 'Mostra tutte le date'.")
with tab2:
    # Genera il testo dinamico basato sui filtri applicati
    if show_all:
        title_date_info = ""
    elif only_selected_date:
        title_date_info = f" del {selected_date.strftime('%d/%m/%Y')}"
    else:
        title_date_info = f" dal {selected_date.strftime('%d/%m/%Y')}"
    
    st.markdown(f"## 📈 Performance delle Predizioni{title_date_info}")
    
    # Filtra partite terminate dal dataset filtrato per data
    completed_matches = df_filtered[
        (df_filtered['Risultato predizione (risultato secco)'] != 'Da giocare') &
        (df_filtered['Risultato predizione (doppia chance)'] != 'Da giocare')
    ]
    
    if len(completed_matches) > 0:
        # Metriche principali
        col1, col2 = st.columns(2)
        
        with col1:
            # Accuratezza risultato secco
            correct_exact = len(completed_matches[completed_matches['Risultato predizione (risultato secco)'] == 'Corretto'])
            total_exact = len(completed_matches)
            accuracy_exact = (correct_exact / total_exact) * 100 if total_exact > 0 else 0
            
            st.markdown(f"""
            <div class="metric-card">
                <h3>🎯 Risultato Secco</h3>
                <h2>{accuracy_exact:.1f}%</h2>
                <p>{correct_exact}/{total_exact} predizioni corrette</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Accuratezza doppia chance
            correct_double = len(completed_matches[completed_matches['Risultato predizione (doppia chance)'] == 'Corretto'])
            accuracy_double = (correct_double / total_exact) * 100 if total_exact > 0 else 0
            
            st.markdown(f"""
            <div class="metric-card">
                <h3>🎲 Doppia Chance</h3>
                <h2>{accuracy_double:.1f}%</h2>
                <p>{correct_double}/{total_exact} predizioni corrette</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Grafici
        st.markdown("### 📊 Analisi Dettagliata")
        
        # Grafico accuratezza per confidence
        confidence_stats = completed_matches.groupby('Confidence').agg({
            'Risultato predizione (risultato secco)': lambda x: (x == 'Corretto').sum() / len(x) * 100,
            'Risultato predizione (doppia chance)': lambda x: (x == 'Corretto').sum() / len(x) * 100
        }).reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='Risultato Secco',
            x=confidence_stats['Confidence'],
            y=confidence_stats['Risultato predizione (risultato secco)'],
            marker_color='#ff6b35'
        ))
        fig.add_trace(go.Bar(
            name='Doppia Chance',
            x=confidence_stats['Confidence'],
            y=confidence_stats['Risultato predizione (doppia chance)'],
            marker_color='#4facfe'
        ))
        
        fig.update_layout(
            title='Accuratezza per Livello di Confidence',
            xaxis_title='Livello Confidence',
            yaxis_title='Accuratezza (%)',
            barmode='group',
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabella dettagli partite completate
        st.markdown("### 📋 Dettaglio Partite Completate")
        
        for idx, match in completed_matches.iterrows():
            col1, col2 = st.columns([3, 1])
            
            # Formatta la data per visualizzazione
            match_date = match['Data partita'].strftime('%d/%m/%Y') if pd.notna(match['Data partita']) else 'Data N/D'
            
            with col1:
                st.markdown(f"""
                **{match['Squadra casa']} vs {match['Squadra ospite']}**  
                📅 {match_date} | 🏆 {match['Campionato']}  
                🎯 Previsto: {match['Risultato secco previsto']} | Reale: {match['Risultato secco reale']}  
                🎲 Doppia Chance: {match['Doppia chance prevista']} | Confidence: {match['Confidence']}
                """)
            
            with col2:
                # Badge status
                exact_status = match['Risultato predizione (risultato secco)']
                double_status = match['Risultato predizione (doppia chance)']
                
                exact_class = 'status-correct' if exact_status == 'Corretto' else 'status-incorrect'
                double_class = 'status-correct' if double_status == 'Corretto' else 'status-incorrect'
                
                st.markdown(f"""
                <div class="status-badge {exact_class}">Secco: {exact_status}</div><br>
                <div class="status-badge {double_class}">Doppia: {double_status}</div>
                """, unsafe_allow_html=True)
            
            st.markdown("""
            <div style="
                height: 2px;
                background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
                margin: 2rem 0;
            "></div>
            """, unsafe_allow_html=True)
    
    else:
        st.info("📊 Nessuna partita completata ancora. Le statistiche appariranno qui una volta terminate le prime partite.")

with tab3:
    st.markdown("## 🔴 Predizioni")
    
    # Filtra partite da giocare dal dataset filtrato per data
    upcoming_matches = df_filtered[
        (df_filtered['Risultato predizione (risultato secco)'] == 'Da giocare') |
        (df_filtered['Risultato predizione (doppia chance)'] == 'Da giocare')
    ]
    
    if len(upcoming_matches) > 0:
        st.markdown(f"### 🎮 {len(upcoming_matches)} Partite in Programma")
        
        for idx, match in upcoming_matches.iterrows():
            # Formatta la data per visualizzazione
            match_date = match['Data partita'].strftime('%d/%m/%Y') if pd.notna(match['Data partita']) else 'Data N/D'
            
            # Card con predizioni usando container normale invece di HTML
            with st.container():
                st.markdown(f"""
                <div class="prediction-card">
                    <h3>⚽ {match['Squadra casa']} vs {match['Squadra ospite']}</h3>
                    <p>📅 {match_date} | 🏆 {match['Campionato']} | Giornata {match['Giornata']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Predizioni usando colonne Streamlit normali
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**🎯 Risultato Secco Previsto:**")
                    st.markdown(f"**{match['Risultato secco previsto']}**")
                
                with col2:
                    st.markdown("**🎲 Doppia Chance:**")
                    st.markdown(f"**{match['Doppia chance prevista']}**")
                
                with col3:
                    st.markdown("**📊 Confidence:**")
                    st.markdown(f"**{match['Confidence']}**")
                
                # Spazio tra le partite
                st.markdown("""
                <div style="
                    height: 2px;
                    background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
                    margin: 2rem 0;
                "></div>
                """, unsafe_allow_html=True)
                    
    else:
        st.info("🎮 Nessuna partita in programma al momento. Le prossime predizioni appariranno qui.")

with tab4:
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
        text-align: center;
    ">
        <h1 style="margin: 0; font-size: 2.2rem; font-weight: 700;">🤖 Come Funzionano le Predizioni</h1>
        <p style="margin-top: 1rem; font-size: 1.1rem; opacity: 0.95;">
            Sistema AI avanzato che combina analisi statistica e informazioni contestuali in tempo reale
        </p>
    </div>
    
    <div style="background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 25px;">
        <h2 style="color: #1e293b; margin-bottom: 20px; font-size: 1.5rem;">🔄 Pipeline di Analisi</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px;">
            <div style="background: #f8fafc; padding: 20px; border-radius: 12px; border-left: 4px solid #667eea;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">📊</div>
                <h3 style="color: #1e293b; font-size: 1.1rem; margin-bottom: 10px;">1. Raccolta Dati</h3>
                <p style="color: #64748b; font-size: 0.9rem; line-height: 1.6;">
                    Estrazione automatica delle partite da Sky Sport per tutti i principali campionati europei (Serie A, Premier League, Bundesliga, Ligue 1, La Liga)
                </p>
            </div>
            <div style="background: #f8fafc; padding: 20px; border-radius: 12px; border-left: 4px solid #3b82f6;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">🔍</div>
                <h3 style="color: #1e293b; font-size: 1.1rem; margin-bottom: 10px;">2. Analisi Statistica</h3>
                <p style="color: #64748b; font-size: 0.9rem; line-height: 1.6;">
                    Recupero statistiche avanzate (Expected Goals, Expected Points, forma recente) e informazioni contestuali (infortuni, squalifiche, motivazioni)
                </p>
            </div>
            <div style="background: #f8fafc; padding: 20px; border-radius: 12px; border-left: 4px solid #10b981;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">🤖</div>
                <h3 style="color: #1e293b; font-size: 1.1rem; margin-bottom: 10px;">3. Predizione AI</h3>
                <p style="color: #64748b; font-size: 0.9rem; line-height: 1.6;">
                    GPT-4o-mini analizza tutti i dati raccolti e genera predizioni con percentuali di probabilità e livelli di confidence
                </p>
            </div>
        </div>
    </div>
    
    <div style="background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 25px;">
        <h2 style="color: #1e293b; margin-bottom: 20px; font-size: 1.5rem;">📈 Statistiche Chiave Analizzate</h2>
        <div style="background: #f8fafc; padding: 20px; border-radius: 12px; margin-bottom: 15px; border-left: 4px solid #667eea;">
            <h3 style="color: #667eea; margin-bottom: 10px; font-size: 1.1rem;">🎯 Expected Goals (xG)</h3>
            <p style="color: #64748b; line-height: 1.7; margin-bottom: 8px;">
                Misura la qualità delle occasioni create. Un xG alto con pochi gol segnati indica sfortuna in fase realizzativa e probabile miglioramento futuro.
            </p>
            <p style="color: #475569; font-size: 0.85rem; background: white; padding: 10px; border-radius: 6px;">
                <strong>Esempio:</strong> xG = 4.3 ma solo 2 gol segnati → la squadra crea ottime occasioni ma è sfortunata, probabile che segni di più nelle prossime partite
            </p>
        </div>
        <div style="background: #f8fafc; padding: 20px; border-radius: 12px; margin-bottom: 15px; border-left: 4px solid #3b82f6;">
            <h3 style="color: #3b82f6; margin-bottom: 10px; font-size: 1.1rem;">🛡️ Expected Goals Conceded (xGC)</h3>
            <p style="color: #64748b; line-height: 1.7; margin-bottom: 8px;">
                Misura la solidità difensiva. Indica quanti gol una squadra "dovrebbe" subire in base alle occasioni concesse agli avversari.
            </p>
            <p style="color: #475569; font-size: 0.85rem; background: white; padding: 10px; border-radius: 6px;">
                <strong>Esempio:</strong> xGC = 1.2 ma 3 gol subiti → la difesa concede poche occasioni ma è sfortunata, possibile miglioramento
            </p>
        </div>
        <div style="background: #f8fafc; padding: 20px; border-radius: 12px; border-left: 4px solid #10b981;">
            <h3 style="color: #10b981; margin-bottom: 10px; font-size: 1.1rem;">📊 Expected Points (xPTS)</h3>
            <p style="color: #64748b; line-height: 1.7; margin-bottom: 8px;">
                Punti che una squadra "dovrebbe" aver ottenuto in base alle performance effettive. Rivela squadre sovra o sottoperformanti.
            </p>
            <p style="color: #475569; font-size: 0.85rem; background: white; padding: 10px; border-radius: 6px;">
                <strong>Esempio:</strong> xPTS = 12 ma solo 6 punti reali → squadra sottovalutata che gioca meglio di quanto dice la classifica
            </p>
        </div>
    </div>
    
    <div style="background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 25px;">
        <h2 style="color: #1e293b; margin-bottom: 20px; font-size: 1.5rem;">🔍 Fattori Contestuali Analizzati</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px;">
            <div style="background: #f8fafc; padding: 18px; border-radius: 10px;">
                <strong style="color: #667eea;">📰 Informazioni Real-Time</strong>
                <p style="color: #64748b; font-size: 0.9rem; margin-top: 8px; line-height: 1.6;">
                    Infortuni/squalifiche giocatori chiave, dichiarazioni pre-partita allenatori, rotazioni previste per impegni ravvicinati
                </p>
            </div>
            <div style="background: #f8fafc; padding: 18px; border-radius: 10px;">
                <strong style="color: #3b82f6;">📊 Forma e Storico</strong>
                <p style="color: #64748b; font-size: 0.9rem; margin-top: 8px; line-height: 1.6;">
                    Risultati ultime 5 partite, performance casa/trasferta, scontri diretti recenti, trend miglioramento/peggioramento
                </p>
            </div>
            <div style="background: #f8fafc; padding: 18px; border-radius: 10px;">
                <strong style="color: #10b981;">🎯 Fattori Psicologici</strong>
                <p style="color: #64748b; font-size: 0.9rem; margin-top: 8px; line-height: 1.6;">
                    Motivazioni particolari (derby, salvezza, corsa al titolo), pressione, rivalità storiche, gestione energie
                </p>
            </div>
        </div>
    </div>
    
    <div style="background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 25px;">
        <h2 style="color: #1e293b; margin-bottom: 20px; font-size: 1.5rem;">💪 Livelli di Confidence</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 25px; border-radius: 12px; color: white; text-align: center;">
                <h3 style="margin: 0; font-size: 1.3rem;">🟢 Alta</h3>
                <p style="margin-top: 12px; font-size: 0.9rem; line-height: 1.6; opacity: 0.95;">
                    Forte convergenza di tutti gli indicatori statistici. Divario netto tra le squadre e nessun fattore contestuale rilevante in contrasto.
                </p>
            </div>
            <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); padding: 25px; border-radius: 12px; color: white; text-align: center;">
                <h3 style="margin: 0; font-size: 1.3rem;">🟡 Media</h3>
                <p style="margin-top: 12px; font-size: 0.9rem; line-height: 1.6; opacity: 0.95;">
                    Situazione equilibrata o con segnali contrastanti. Le statistiche indicano una direzione ma alcuni fattori suggeriscono cautela.
                </p>
            </div>
            <div style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); padding: 25px; border-radius: 12px; color: white; text-align: center;">
                <h3 style="margin: 0; font-size: 1.3rem;">🔴 Bassa</h3>
                <p style="margin-top: 12px; font-size: 0.9rem; line-height: 1.6; opacity: 0.95;">
                    Partita molto incerta. Statistiche vicine, fattori imprevedibili o mancanza di informazioni chiave. Risultato difficile da prevedere.
                </p>
            </div>
        </div>
    </div>
    
    <div style="background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 25px;">
        <h2 style="color: #1e293b; margin-bottom: 20px; font-size: 1.5rem; text-align: center;">⚙️ Stack Tecnologico</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px;">
            <div style="text-align: center; padding: 15px;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">🔥</div>
                <strong style="color: #1e293b;">Firecrawl</strong>
                <p style="color: #64748b; font-size: 0.8rem; margin-top: 5px;">Scraping partite</p>
            </div>
            <div style="text-align: center; padding: 15px;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">🤖</div>
                <strong style="color: #1e293b;">GPT-4o-mini</strong>
                <p style="color: #64748b; font-size: 0.8rem; margin-top: 5px;">Analisi AI</p>
            </div>
            <div style="text-align: center; padding: 15px;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">🔍</div>
                <strong style="color: #1e293b;">Tavily</strong>
                <p style="color: #64748b; font-size: 0.8rem; margin-top: 5px;">Info real-time</p>
            </div>
            <div style="text-align: center; padding: 15px;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">⚡</div>
                <strong style="color: #1e293b;">n8n</strong>
                <p style="color: #64748b; font-size: 0.8rem; margin-top: 5px;">Automazione</p>
            </div>
            <div style="text-align: center; padding: 15px;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">📊</div>
                <strong style="color: #1e293b;">Streamlit</strong>
                <p style="color: #64748b; font-size: 0.8rem; margin-top: 5px;">Dashboard</p>
            </div>
            <div style="text-align: center; padding: 15px;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">📋</div>
                <strong style="color: #1e293b;">Google Sheets</strong>
                <p style="color: #64748b; font-size: 0.8rem; margin-top: 5px;">Database</p>
            </div>
        </div>
    </div>
    
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
    ">
        <h3 style="margin: 0; font-size: 1.3rem; margin-bottom: 10px;">⚠️ Disclaimer</h3>
        <p style="margin: 0; font-size: 0.95rem; line-height: 1.7; opacity: 0.95;">
            Queste predizioni sono generate da un sistema AI a scopo informativo e di analisi. 
            Non costituiscono in alcun modo un consiglio per scommesse o investimenti. 
            Il calcio è uno sport imprevedibile e nessun sistema può garantire risultati accurati al 100%.
        </p>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("""
<div style="
    height: 2px;
    background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
    margin: 2rem 0;
"></div>
""", unsafe_allow_html=True)
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    ⚽ Dashboard Predizioni Calcistiche | Aggiornato automaticamente<br>
    📱 Il sistema che genera le predizioni è stato sviluppato in n8n
</div>
""", unsafe_allow_html=True)

