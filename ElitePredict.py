import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import time
from io import StringIO
import gspread
from google.oauth2.service_account import Credentials

# Configurazione pagina
st.set_page_config(
    page_title="Predizioni Calcistiche",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizzato
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #1f77b4;
    }
    .success-metric {
        border-left-color: #2e8b57;
    }
    .warning-metric {
        border-left-color: #ff6347;
    }
    .info-metric {
        border-left-color: #4682b4;
    }
</style>
""", unsafe_allow_html=True)

class FootballAPI:
    """Classe per recuperare risultati in tempo reale"""
    
    @staticmethod
    def get_live_results(team1, team2, date):
        """
        Recupera risultati in tempo reale (simulato per demo)
        In produzione, utilizzare API come Football-Data.org, API-Sports, etc.
        """
        try:
            # Simulazione di chiamata API
            # In produzione sostituire con vera API
            simulated_results = {
                ("Milan", "Napoli"): "1-2",
                ("Roma", "Verona"): "2-0",
                ("Sassuolo", "Udinese"): "1-1",
                ("Lecce", "Bologna"): "0-1",
                ("Parma", "Torino"): "2-1",
                ("Genoa", "Lazio"): "1-3"
            }
            
            key = (team1, team2)
            if key in simulated_results:
                return simulated_results[key]
            else:
                return "Da giocare"
                
        except Exception as e:
            return "Errore API"

@st.cache_data(ttl=300)  # Cache per 5 minuti
def load_data_from_drive(file_url):
    """Carica dati da Google Drive"""
    try:
        # Converte URL di Google Drive in formato scaricabile
        if 'drive.google.com' in file_url:
            file_id = file_url.split('/d/')[1].split('/')[0]
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        else:
            download_url = file_url
            
        df = pd.read_excel(download_url, skiprows=3)  # Salta le prime 3 righe con statistiche
        
        # Pulizia e preparazione dati
        df['Data predizione'] = pd.to_datetime(df['Data predizione'], format='%d/%m/%Y')
        df['Data partita'] = pd.to_datetime(df['Data partita'], format='%d/%m/%Y')
        
        return df
    except Exception as e:
        st.error(f"Errore nel caricamento del file: {str(e)}")
        return None

def calculate_statistics(df):
    """Calcola statistiche generali"""
    played_matches = df[df['Risultato secco reale'].notna()]
    
    stats = {
        'total_matches': len(df),
        'played_matches': len(played_matches),
        'to_play_matches': len(df) - len(played_matches),
        'correct_predictions': len(played_matches[played_matches['Risultato predizione (risultato secco)'] == 'Corretto']),
        'accuracy_exact': len(played_matches[played_matches['Risultato predizione (risultato secco)'] == 'Corretto']) / len(played_matches) * 100 if len(played_matches) > 0 else 0,
        'accuracy_double': len(played_matches[played_matches['Risultato predizione (doppia chance)'] == 'Corretto']) / len(played_matches) * 100 if len(played_matches) > 0 else 0,
        'home_wins': len(played_matches[played_matches['Risultato secco reale'] == '1']) / len(played_matches) * 100 if len(played_matches) > 0 else 0,
        'draws': len(played_matches[played_matches['Risultato secco reale'] == 'X']) / len(played_matches) * 100 if len(played_matches) > 0 else 0,
        'away_wins': len(played_matches[played_matches['Risultato secco reale'] == '2']) / len(played_matches) * 100 if len(played_matches) > 0 else 0
    }
    
    return stats, played_matches

def create_accuracy_chart(df):
    """Crea grafico accuratezza per campionato"""
    played_matches = df[df['Risultato secco reale'].notna()]
    
    # Accuratezza per campionato
    league_accuracy = played_matches.groupby('Campionato').agg({
        'Risultato predizione (risultato secco)': lambda x: (x == 'Corretto').sum() / len(x) * 100,
        'Risultato predizione (doppia chance)': lambda x: (x == 'Corretto').sum() / len(x) * 100
    }).reset_index()
    
    league_accuracy.columns = ['Campionato', 'Accuratezza Risultato Secco', 'Accuratezza Doppia Chance']
    
    fig = px.bar(league_accuracy, 
                 x='Campionato', 
                 y=['Accuratezza Risultato Secco', 'Accuratezza Doppia Chance'],
                 title='Accuratezza Predizioni per Campionato',
                 barmode='group')
    
    fig.update_layout(height=400)
    return fig

def create_confidence_analysis(df):
    """Analizza accuratezza per livello di confidenza"""
    played_matches = df[df['Risultato secco reale'].notna()]
    
    confidence_analysis = played_matches.groupby('Confidence').agg({
        'Risultato predizione (risultato secco)': lambda x: (x == 'Corretto').sum() / len(x) * 100
    }).reset_index()
    
    confidence_analysis.columns = ['Confidence', 'Accuratezza']
    
    fig = px.pie(confidence_analysis, 
                 values='Accuratezza', 
                 names='Confidence',
                 title='Accuratezza per Livello di Confidenza')
    
    return fig

def show_statistics_page(df):
    """Pagina delle statistiche"""
    st.header("📊 Statistiche Predizioni")
    
    stats, played_matches = calculate_statistics(df)
    
    # Metriche principali
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card info-metric">
            <h3>Partite Totali</h3>
            <h2>{}</h2>
        </div>
        """.format(stats['total_matches']), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card success-metric">
            <h3>Partite Giocate</h3>
            <h2>{}</h2>
        </div>
        """.format(stats['played_matches']), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card warning-metric">
            <h3>Accuratezza Risultato Secco</h3>
            <h2>{:.1f}%</h2>
        </div>
        """.format(stats['accuracy_exact']), unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card success-metric">
            <h3>Accuratezza Doppia Chance</h3>
            <h2>{:.1f}%</h2>
        </div>
        """.format(stats['accuracy_double']), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Grafici
    col1, col2 = st.columns(2)
    
    with col1:
        # Grafico accuratezza per campionato
        fig_accuracy = create_accuracy_chart(df)
        st.plotly_chart(fig_accuracy, use_container_width=True)
    
    with col2:
        # Distribuzione risultati
        result_dist = played_matches['Risultato secco reale'].value_counts()
        fig_results = px.pie(values=result_dist.values, 
                            names=['Vittoria Casa' if x=='1' else 'Pareggio' if x=='X' else 'Vittoria Ospite' for x in result_dist.index],
                            title='Distribuzione Risultati Reali')
        st.plotly_chart(fig_results, use_container_width=True)
    
    # Analisi per confidenza
    st.subheader("Analisi per Livello di Confidenza")
    confidence_fig = create_confidence_analysis(df)
    st.plotly_chart(confidence_fig, use_container_width=True)
    
    # Tabella dettagliata per campionato
    st.subheader("Statistiche Dettagliate per Campionato")
    
    league_stats = played_matches.groupby('Campionato').agg({
        'Squadra casa': 'count',
        'Risultato predizione (risultato secco)': lambda x: (x == 'Corretto').sum(),
        'Risultato predizione (doppia chance)': lambda x: (x == 'Corretto').sum()
    }).reset_index()
    
    league_stats.columns = ['Campionato', 'Partite Giocate', 'Predizioni Corrette (Secco)', 'Predizioni Corrette (Doppia)']
    league_stats['Accuratezza Secco (%)'] = (league_stats['Predizioni Corrette (Secco)'] / league_stats['Partite Giocate'] * 100).round(1)
    league_stats['Accuratezza Doppia (%)'] = (league_stats['Predizioni Corrette (Doppia)'] / league_stats['Partite Giocate'] * 100).round(1)
    
    st.dataframe(league_stats, use_container_width=True)

def show_upcoming_matches(df):
    """Pagina partite da giocare"""
    st.header("🎯 Partite da Giocare")
    
    # Filtra partite da giocare
    upcoming = df[df['Risultato secco reale'].isna()].copy()
    
    if len(upcoming) == 0:
        st.info("Nessuna partita da giocare nel dataset!")
        return
    
    st.subheader(f"Prossime {len(upcoming)} partite")
    
    # Filtri
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_league = st.selectbox("Filtra per Campionato", 
                                     ["Tutti"] + list(upcoming['Campionato'].unique()))
    
    with col2:
        selected_confidence = st.selectbox("Filtra per Confidenza", 
                                         ["Tutti"] + list(upcoming['Confidence'].unique()))
    
    with col3:
        if st.button("🔄 Aggiorna Risultati Live"):
            st.rerun()
    
    # Applica filtri
    filtered_upcoming = upcoming.copy()
    if selected_league != "Tutti":
        filtered_upcoming = filtered_upcoming[filtered_upcoming['Campionato'] == selected_league]
    if selected_confidence != "Tutti":
        filtered_upcoming = filtered_upcoming[filtered_upcoming['Confidence'] == selected_confidence]
    
    # Recupera risultati live
    api = FootballAPI()
    
    for idx, row in filtered_upcoming.iterrows():
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
            
            with col1:
                st.markdown(f"""
                **{row['Squadra casa']} vs {row['Squadra ospite']}**  
                📅 {row['Data partita'].strftime('%d/%m/%Y')} - {row['Giorno partita']}  
                🏆 {row['Campionato']} (Giornata {row['Giornata']})
                """)
            
            with col2:
                confidence_color = {"Alta": "🟢", "Media": "🟡", "Bassa": "🔴"}
                st.markdown(f"""
                **Predizione:**  
                {row['Risultato secco previsto']}  
                {confidence_color.get(row['Confidence'], '⚪')} {row['Confidence']}
                """)
            
            with col3:
                st.markdown(f"""
                **Doppia Chance:**  
                {row['Doppia chance prevista']}
                """)
            
            with col4:
                # Recupera risultato live
                live_result = api.get_live_results(row['Squadra casa'], row['Squadra ospite'], row['Data partita'])
                
                if live_result == "Da giocare":
                    st.markdown("⏳ **Da giocare**")
                elif live_result == "Errore API":
                    st.markdown("❌ **Errore nel recupero**")
                else:
                    st.markdown(f"⚽ **Risultato Live:** {live_result}")
            
            st.markdown("---")

def show_played_matches(df):
    """Pagina partite giocate"""
    st.header("📋 Partite Giocate")
    
    played_matches = df[df['Risultato secco reale'].notna()].copy()
    
    if len(played_matches) == 0:
        st.info("Nessuna partita giocata nel dataset!")
        return
    
    # Filtri
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_league = st.selectbox("Campionato", 
                                     ["Tutti"] + list(played_matches['Campionato'].unique()),
                                     key="played_league")
    
    with col2:
        result_filter = st.selectbox("Risultato Predizione", 
                                   ["Tutti", "Corretto", "Errato"],
                                   key="played_result")
    
    with col3:
        confidence_filter = st.selectbox("Confidenza", 
                                       ["Tutti"] + list(played_matches['Confidence'].unique()),
                                       key="played_confidence")
    
    # Applica filtri
    filtered_played = played_matches.copy()
    if selected_league != "Tutti":
        filtered_played = filtered_played[filtered_played['Campionato'] == selected_league]
    if result_filter != "Tutti":
        filtered_played = filtered_played[filtered_played['Risultato predizione (risultato secco)'] == result_filter]
    if confidence_filter != "Tutti":
        filtered_played = filtered_played[filtered_played['Confidence'] == confidence_filter]
    
    st.subheader(f"Visualizzate {len(filtered_played)} partite")
    
    # Visualizza partite
    for idx, row in filtered_played.iterrows():
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.markdown(f"""
            **{row['Squadra casa']} vs {row['Squadra ospite']}**  
            📅 {row['Data partita'].strftime('%d/%m/%Y')}  
            🏆 {row['Campionato']}
            """)
        
        with col2:
            pred_icon = "✅" if row['Risultato predizione (risultato secco)'] == 'Corretto' else "❌"
            st.markdown(f"""
            **Predetto:** {row['Risultato secco previsto']}  
            **Reale:** {row['Risultato secco reale']}  
            {pred_icon}
            """)
        
        with col3:
            double_icon = "✅" if row['Risultato predizione (doppia chance)'] == 'Corretto' else "❌"
            st.markdown(f"""
            **Doppia:** {row['Doppia chance prevista']}  
            {double_icon}
            """)
        
        with col4:
            confidence_color = {"Alta": "🟢", "Media": "🟡", "Bassa": "🔴"}
            st.markdown(f"{confidence_color.get(row['Confidence'], '⚪')} {row['Confidence']}")
        
        st.markdown("---")

def main():
    st.title("⚽ Sistema di Predizioni Calcistiche")
    
    # Sidebar per configurazione
    st.sidebar.header("Configurazione")
    
    # Input per URL Google Drive
    drive_url = "https://docs.google.com/spreadsheets/d/1tC2h3ud-h1tLAnmU2tdWOFG7-lMoE-FK/edit?gid=105352643#gid=105352643"
    
    if not drive_url:
        st.info("👆 Inserisci l'URL del file Excel nella sidebar per iniziare")
        st.markdown("""
        ### Funzionalità:
        - 📊 **Statistiche**: Analisi complete delle predizioni
        - 🎯 **Partite da Giocare**: Visualizza le prossime partite con risultati live
        - 📋 **Partite Giocate**: Cronologia delle partite già disputate
        """)
        return
    
    # Carica dati
    with st.spinner("Caricamento dati..."):
        df = load_data_from_drive(drive_url)
    
    if df is None:
        return
    
    # Menu navigazione
    page = st.sidebar.selectbox(
        "Naviga",
        ["📊 Statistiche", "🎯 Partite da Giocare", "📋 Partite Giocate"]
    )
    
    # Informazioni dataset
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Partite totali:** {len(df)}")
    st.sidebar.markdown(f"**Partite giocate:** {len(df[df['Risultato secco reale'].notna()])}")
    st.sidebar.markdown(f"**Da giocare:** {len(df[df['Risultato secco reale'].isna()])}")
    st.sidebar.markdown(f"**Ultimo aggiornamento:** {datetime.now().strftime('%H:%M:%S')}")
    
    # Mostra pagina selezionata
    if page == "📊 Statistiche":
        show_statistics_page(df)
    elif page == "🎯 Partite da Giocare":
        show_upcoming_matches(df)
    else:
        show_played_matches(df)

if __name__ == "__main__":
    main()