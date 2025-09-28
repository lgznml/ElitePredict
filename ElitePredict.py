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
    page_title="⚽ Predizioni Calcio",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
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
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 10px 0;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    
    .prediction-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin: 15px 0;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
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
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        margin: 5px 0;
    }
    
    .status-correct {
        background-color: #28a745;
        color: white;
    }
    
    .status-incorrect {
        background-color: #dc3545;
        color: white;
    }
    
    .status-pending {
        background-color: #ffc107;
        color: black;
    }
    
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            font-size: 14px;
            padding: 0px 8px;
        }
    }
</style>
""", unsafe_allow_html=True)

# Funzione per caricare dati dal Google Sheets
@st.cache_data(ttl=300)  # Cache per 5 minuti
def load_data():
    """
    Carica i dati dal Google Sheets convertendo l'URL in formato CSV
    """
    # URL originale del Google Sheets
    google_sheets_url = "https://docs.google.com/spreadsheets/d/15sGAUABd3b-dsQ-iW8AHVclM_hSu_cD_/edit?gid=843549565#gid=843549565"
    
    try:
        # Estrae l'ID del foglio e il GID
        sheet_id = "15sGAUABd3b-dsQ-iW8AHVclM_hSu_cD_"
        gid = "843549565"
        
        # Costruisce l'URL CSV
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        
        # Legge i dati dal CSV
        df = pd.read_csv(csv_url)
        
        # Pulizia e preprocessing dei dati
        # Rimuove spazi bianchi dai nomi delle colonne
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
        
        st.success(f"✅ Dati caricati con successo! {len(df)} partite trovate.")
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

# Funzione per ottenere risultati live (simulata)
@st.cache_data(ttl=60)  # Cache per 1 minuto
def get_live_scores(home_team, away_team):
    # Simulazione di chiamata API per risultati live
    # In realtà dovresti usare un'API come Football-Data.org, RapidAPI, etc.
    import random
    
    # Simula risultati casuali
    home_score = random.randint(0, 4)
    away_score = random.randint(0, 4)
    status = random.choice(['LIVE', 'FT', 'HT', 'SCHEDULED'])
    
    return {
        'home_score': home_score,
        'away_score': away_score,
        'status': status,
        'minute': random.randint(1, 90) if status == 'LIVE' else None
    }

# Caricamento dati
df = load_data()

# Header
st.markdown("# ⚽ Dashboard Predizioni Calcio")
st.markdown("---")

# Tabs principali
tab1, tab2 = st.tabs(["📊 Statistiche", "🔴 Live Predizioni"])

with tab1:
    st.markdown("## 📈 Performance delle Predizioni")
    
    # Filtra partite terminate
    completed_matches = df[
        (df['Risultato predizione (risultato secco)'] != 'Da giocare') &
        (df['Risultato predizione (doppia chance)'] != 'Da giocare')
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
            
            with col1:
                st.markdown(f"""
                **{match['Squadra casa']} vs {match['Squadra ospite']}**  
                📅 {match['Data partita']} | 🏆 {match['Campionato']}  
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
            
            st.markdown("---")
    
    else:
        st.info("📊 Nessuna partita completata ancora. Le statistiche appariranno qui una volta terminate le prime partite.")

with tab2:
    st.markdown("## 🔴 Predizioni Live")
    
    # Filtra partite da giocare
    upcoming_matches = df[
        (df['Risultato predizione (risultato secco)'] == 'Da giocare') |
        (df['Risultato predizione (doppia chance)'] == 'Da giocare')
    ]
    
    if len(upcoming_matches) > 0:
        st.markdown(f"### 🎮 {len(upcoming_matches)} Partite in Programma")
        
        # Auto-refresh ogni 30 secondi
        if st.button("🔄 Aggiorna Risultati Live", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        for idx, match in upcoming_matches.iterrows():
            # Ottieni risultato live
            live_data = get_live_scores(match['Squadra casa'], match['Squadra ospite'])
            
            st.markdown(f"""
            <div class="prediction-card">
                <h3>⚽ {match['Squadra casa']} vs {match['Squadra ospite']}</h3>
                <p>📅 {match['Data partita']} | 🏆 {match['Campionato']} | Giornata {match['Giornata']}</p>
                
                <div style="display: flex; justify-content: space-between; margin: 15px 0;">
                    <div>
                        <strong>🎯 Risultato Secco Previsto:</strong> {match['Risultato secco previsto']}<br>
                        <strong>🎲 Doppia Chance:</strong> {match['Doppia chance prevista']}<br>
                        <strong>📊 Confidence:</strong> {match['Confidence']}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Risultato live
            if live_data['status'] in ['LIVE', 'FT', 'HT']:
                status_text = {
                    'LIVE': f"🔴 LIVE - {live_data['minute']}'",
                    'FT': "✅ FINITA",
                    'HT': "⏸️ INTERVALLO"
                }.get(live_data['status'], live_data['status'])
                
                st.markdown(f"""
                <div class="live-score">
                    <h4>{status_text}</h4>
                    <h2>{match['Squadra casa']} {live_data['home_score']} - {live_data['away_score']} {match['Squadra ospite']}</h2>
                </div>
                """, unsafe_allow_html=True)
                
                # Analisi predizione in tempo reale
                if live_data['status'] == 'FT':
                    home_score = live_data['home_score']
                    away_score = live_data['away_score']
                    
                    # Determina risultato reale
                    if home_score > away_score:
                        actual_result = '1'
                    elif home_score < away_score:
                        actual_result = '2'
                    else:
                        actual_result = 'X'
                    
                    # Verifica predizioni
                    exact_correct = match['Risultato secco previsto'] == actual_result
                    
                    # Verifica doppia chance
                    double_chance = match['Doppia chance prevista']
                    double_correct = False
                    if double_chance == '1X' and actual_result in ['1', 'X']:
                        double_correct = True
                    elif double_chance == '2X' and actual_result in ['2', 'X']:
                        double_correct = True
                    elif double_chance == '12' and actual_result in ['1', '2']:
                        double_correct = True
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        exact_status = "✅ CORRETTO" if exact_correct else "❌ ERRATO"
                        st.markdown(f"**🎯 Risultato Secco:** {exact_status}")
                    
                    with col2:
                        double_status = "✅ CORRETTO" if double_correct else "❌ ERRATO"
                        st.markdown(f"**🎲 Doppia Chance:** {double_status}")
            
            else:
                st.markdown(f"""
                <div class="live-score">
                    <h4>⏰ PROGRAMMATA</h4>
                    <p>La partita inizierà presto</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
    
    else:
        st.info("🎮 Nessuna partita in programma al momento. Le prossime predizioni appariranno qui.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    ⚽ Dashboard Predizioni Calcio | Aggiornato automaticamente<br>
    📱 Ottimizzato per smartphone
</div>
""", unsafe_allow_html=True)

# Auto-refresh per dati live (ogni 30 secondi quando ci sono partite live)
if len(df[(df['Risultato predizione (risultato secco)'] == 'Da giocare')]) > 0:
    time.sleep(0.1)  # Piccola pausa per evitare refresh troppo frequenti
