zimport streamlit as st
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

# Header
st.markdown("# ⚽ Dashboard Predizioni Calcio")

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

# Calcola il lunedì della settimana corrente
today = datetime.now().date()
days_since_monday = today.weekday()  # 0=Lunedì, 6=Domenica
monday_of_week = today - timedelta(days=days_since_monday)

# Assicura che il valore predefinito sia nel range valido
default_date = monday_of_week if min_date <= monday_of_week <= max_date else min_date
    
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
if not show_all:
    if only_selected_date:
        st.info(f"📅 Visualizzando partite {filter_info}{league_info} - {len(df_filtered)} partite trovate")
    else:
        st.info(f"📅 Visualizzando partite {filter_info}{league_info} - {len(df_filtered)} partite trovate")
else:
    st.info(f"📅 Visualizzando tutte le partite{league_info} - {len(df_filtered)} partite totali")
    
st.markdown("---")

# Tabs principali
# Calcola il numero di partite da giocare per il badge
upcoming_count = len(df_filtered[
    (df_filtered['Risultato predizione (risultato secco)'] == 'Da giocare') |
    (df_filtered['Risultato predizione (doppia chance)'] == 'Da giocare')
])

tab1, tab2, tab3 = st.tabs(["📊 Statistiche", "📋 Storico Predizioni", f"🔴 Predizioni ({upcoming_count})"])

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
            st.markdown("""
            <div class="metric-card">
                <h3>🎯 Risultato Secco</h3>
                <h2>{:.1f}%</h2>
                <p>Accuratezza</p>
            </div>
            """.format(accuracy_exact), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
                <h3>✅ Corrette</h3>
                <h2>{}</h2>
                <p>predizioni</p>
            </div>
            """.format(correct_exact), unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
                <h3>❌ Errate</h3>
                <h2>{}</h2>
                <p>predizioni</p>
            </div>
            """.format(wrong_exact), unsafe_allow_html=True)
        
        # Seconda riga - Doppia Chance
        col1, col2, col3 = st.columns(3)
        
        correct_double = len(completed_filtered[completed_filtered['Risultato predizione (doppia chance)'] == 'Corretto'])
        accuracy_double = (correct_double / total_matches) * 100
        wrong_double = total_matches - correct_double
        
        with col1:
            st.markdown("""
            <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                <h3>🎲 Doppia Chance</h3>
                <h2>{:.1f}%</h2>
                <p>Accuratezza</p>
            </div>
            """.format(accuracy_double), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
                <h3>✅ Corrette</h3>
                <h2>{}</h2>
                <p>predizioni</p>
            </div>
            """.format(correct_double), unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
                <h3>❌ Errate</h3>
                <h2>{}</h2>
                <p>predizioni</p>
            </div>
            """.format(wrong_double), unsafe_allow_html=True)
        
        st.markdown("---")
        
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
        
        st.markdown("---")
        
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
        
        st.markdown("---")
        
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
        
        st.markdown("---")
        
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
            
            st.markdown("---")
    
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








