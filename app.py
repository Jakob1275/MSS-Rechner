import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- SEITENKONFIGURATION ---
st.set_page_config(page_title="Wirtschaftlichkeitsvergleich Maschinen", layout="wide")

st.title("📊 Wirtschaftlichkeitsvergleich: Manuell vs. Automation")
st.markdown("""
Detaillierter Vergleich zweier Investitionsalternativen mit Fixkosten, variablen Kosten, 
Stückkostenkalkulation, Break-Even-Analyse und Amortisationsrechnung.
""")

# --- SIDEBAR: MASCHINENPARAMETER ---
with st.sidebar:
    st.header("⚙️ Grundparameter")
    ak = st.number_input("Anschaffungskosten (pro Maschine) [€]", value=600000, step=10000)
    n = st.number_input("Nutzungsdauer [Jahre]", value=20, step=1, min_value=1)
    zins_satz = st.slider("Kalk. Zinssatz [%]", 0.0, 10.0, 5.0, 0.5) / 100
    lohn_satz = st.number_input("Lohnsatz (belastet) [€/h]", value=65.0, step=1.0)
    strom_preis = st.number_input("Strompreis [€/kWh]", value=0.30, step=0.01)
    raum_preis = st.number_input("Raumkosten [€/m²/Monat]", value=15.0, step=1.0)

    st.divider()
    st.subheader("🔧 Maschine A (Manuell)")
    h_jahr_a = st.number_input("Betriebsstunden/Jahr (A)", value=2400, step=100)
    nutzgrad_a = st.slider("Nutzungsgrad A [%]", 0, 100, 75, 5) / 100
    bedien_a = 1.0
    st.info(f"Bedienfaktor A: {bedien_a} (Vollzeit)")
    wartung_a = st.slider("Wartungssatz A [% von AK]", 0.0, 10.0, 2.5, 0.5) / 100
    raum_a = st.number_input("Platzbedarf A [m²]", value=20, step=5)
    energie_a = st.number_input("Leistungsaufnahme A [kW]", value=8.0, step=1.0)
    vers_a = st.number_input("Versicherung A [€/Jahr]", value=500, step=100)
    werkzeug_a = st.number_input("Werkzeugkosten A [€/Jahr]", value=3000, step=500)

    st.divider()
    st.subheader("🤖 Maschine B (Automation)")
    h_jahr_b = st.number_input("Betriebsstunden/Jahr (B)", value=5000, step=100)
    nutzgrad_b = st.slider("Nutzungsgrad B [%]", 0, 100, 85, 5) / 100
    bedien_b = st.slider("Bedienfaktor B", 0.1, 1.0, 0.3, 0.05)
    wartung_b = st.slider("Wartungssatz B [% von AK]", 0.0, 10.0, 4.5, 0.5) / 100
    raum_b = st.number_input("Platzbedarf B [m²]", value=35, step=5)
    energie_b = st.number_input("Leistungsaufnahme B [kW]", value=18.0, step=1.0)
    vers_b = st.number_input("Versicherung B [€/Jahr]", value=1200, step=100)
    werkzeug_b = st.number_input("Werkzeugkosten B [€/Jahr]", value=8000, step=500)

# --- BERECHNUNGSFUNKTIONEN ---
def berechne_mss(ak, n, zins, wartung_satz, raum, r_preis, vers, werkzeug, h_jahr, nutzgrad, kw, s_preis):
    """Berechnet Maschinenstundensatz und Kostenkomponenten"""
    # Fixkosten pro Jahr
    afa = ak / n
    zinsen = (ak / 2) * zins
    wartung = ak * wartung_satz
    raumkosten = raum * r_preis * 12  # Monatlich -> Jährlich
    fix_jahr = afa + zinsen + wartung + raumkosten + vers + werkzeug
    
    # Effektive Stunden
    stunden_effektiv = h_jahr * nutzgrad
    
    # MSS Fixkosten
    mss_fix = fix_jahr / stunden_effektiv if stunden_effektiv > 0 else 0
    
    # MSS Variable Kosten (Energie)
    mss_var = kw * s_preis
    
    return {
        'mss_fix': mss_fix,
        'mss_var': mss_var,
        'fix_jahr': fix_jahr,
        'stunden_effektiv': stunden_effektiv,
        'afa': afa,
        'zinsen': zinsen,
        'wartung': wartung,
        'raumkosten': raumkosten,
        'versicherung': vers,
        'werkzeug': werkzeug
    }

# Ergebnisse berechnen
res_a = berechne_mss(ak, n, zins_satz, wartung_a, raum_a, raum_preis, vers_a, werkzeug_a, 
                     h_jahr_a, nutzgrad_a, energie_a, strom_preis)
res_b = berechne_mss(ak, n, zins_satz, wartung_b, raum_b, raum_preis, vers_b, werkzeug_b, 
                     h_jahr_b, nutzgrad_b, energie_b, strom_preis)

# --- PRODUKTIONSPROGRAMM ---
st.header("📋 Produktionsprogramm")
st.write("Definieren Sie die zu fertigenden Serien. Sie können Zeilen hinzufügen oder löschen.")

default_serien = pd.DataFrame({
    "Serie": ["Welle Typ 1", "Gehäuse groß", "Flansch klein"],
    "Serien/Jahr": [20, 10, 50],
    "Stück/Serie": [50, 20, 100],
    "Bearbzeit (min/Stk) A": [10, 45, 5],
    "Bearbzeit (min/Stk) B": [8, 30, 4],
    "Rüstzeit (min) A": [45, 120, 30],
    "Rüstzeit (min) B": [30, 90, 20]
})

df_serien = st.data_editor(
    default_serien, 
    num_rows="dynamic", 
    use_container_width=True,
    column_config={
        "Serie": st.column_config.TextColumn("Serie/Bauteil", width="medium"),
        "Serien/Jahr": st.column_config.NumberColumn("Serien/Jahr", min_value=1, step=1),
        "Stück/Serie": st.column_config.NumberColumn("Stück/Serie", min_value=1, step=1),
        "Bearbzeit (min/Stk) A": st.column_config.NumberColumn("t_Bearb A (min)", min_value=0.1, step=0.5, format="%.1f"),
        "Bearbzeit (min/Stk) B": st.column_config.NumberColumn("t_Bearb B (min)", min_value=0.1, step=0.5, format="%.1f"),
        "Rüstzeit (min) A": st.column_config.NumberColumn("t_Rüst A (min)", min_value=0, step=1),
        "Rüstzeit (min) B": st.column_config.NumberColumn("t_Rüst B (min)", min_value=0, step=1)
    }
)

# --- DETAILLIERTE KALKULATION ---
def kalkuliere_programm_detail(df, mss_fix, mss_var, lohn, faktor):
    """Detaillierte Kalkulation mit Stückkostenaufschlüsselung"""
    details = []
    ges_kosten = 0
    ges_stunden = 0
    ges_stueck = 0
    
    for _, row in df.iterrows():
        serie = row["Serie"]
        serien_jahr = row["Serien/Jahr"]
        stueck_serie = row["Stück/Serie"]
        
        # Identifiziere ob Maschine A oder B anhand der Spalten
        if "Bearbzeit (min/Stk) A" in df.columns:
            machine = "A"
            t_bearb_min = row["Bearbzeit (min/Stk) A"]
            t_ruest_min = row["Rüstzeit (min) A"]
        else:
            machine = "B"
            t_bearb_min = row["Bearbzeit (min/Stk) B"]
            t_ruest_min = row["Rüstzeit (min) B"]
        
        stueck_jahr = serien_jahr * stueck_serie
        t_bearb_h = (stueck_jahr * t_bearb_min) / 60
        t_ruest_h = (serien_jahr * t_ruest_min) / 60
        
        # Kosten Bearbeitung (MSS + Personal mit Faktor)
        mss_gesamt = mss_fix + mss_var + (lohn * faktor)
        kosten_bearb = t_bearb_h * mss_gesamt
        
        # Kosten Rüsten (MSS + Personal Vollzeit)
        mss_ruest = mss_fix + mss_var + lohn
        kosten_ruest = t_ruest_h * mss_ruest
        
        kosten_ges = kosten_bearb + kosten_ruest
        kosten_stueck = kosten_ges / stueck_jahr if stueck_jahr > 0 else 0
        
        details.append({
            'Serie': serie,
            'Stück/Jahr': int(stueck_jahr),
            'Zeit Bearb (h)': round(t_bearb_h, 1),
            'Zeit Rüst (h)': round(t_ruest_h, 1),
            'Kosten Bearb (€)': round(kosten_bearb, 2),
            'Kosten Rüst (€)': round(kosten_ruest, 2),
            'Kosten Gesamt (€)': round(kosten_ges, 2),
            'Kosten/Stück (€)': round(kosten_stueck, 2)
        })
        
        ges_kosten += kosten_ges
        ges_stunden += (t_bearb_h + t_ruest_h)
        ges_stueck += stueck_jahr
    
    return {
        'details': pd.DataFrame(details),
        'ges_kosten': ges_kosten,
        'ges_stunden': ges_stunden,
        'ges_stueck': ges_stueck
    }

# Kalkulation für beide Maschinen
df_a = df_serien.copy()
df_b = df_serien.copy()

result_a = kalkuliere_programm_detail(
    df_a, res_a['mss_fix'], res_a['mss_var'], lohn_satz, bedien_a
)
result_b = kalkuliere_programm_detail(
    df_b, res_b['mss_fix'], res_b['mss_var'], lohn_satz, bedien_b
)

# --- KERNERGEBNISSE ---
st.divider()
st.header("🎯 Kernergebnisse")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Kosten Maschine A", 
        f"{result_a['ges_kosten']:,.0f} €",
        help="Gesamtkosten für das Produktionsprogramm pro Jahr"
    )
    auslastung_a = (result_a['ges_stunden'] / res_a['stunden_effektiv'] * 100) if res_a['stunden_effektiv'] > 0 else 0
    st.caption(f"⏱️ Auslastung: {auslastung_a:.1f}% ({result_a['ges_stunden']:.0f}/{res_a['stunden_effektiv']:.0f} h)")

with col2:
    st.metric(
        "Kosten Maschine B", 
        f"{result_b['ges_kosten']:,.0f} €",
        help="Gesamtkosten für das Produktionsprogramm pro Jahr"
    )
    auslastung_b = (result_b['ges_stunden'] / res_b['stunden_effektiv'] * 100) if res_b['stunden_effektiv'] > 0 else 0
    st.caption(f"⏱️ Auslastung: {auslastung_b:.1f}% ({result_b['ges_stunden']:.0f}/{res_b['stunden_effektiv']:.0f} h)")

with col3:
    ersparnis = result_a['ges_kosten'] - result_b['ges_kosten']
    ersparnis_proz = (ersparnis / result_a['ges_kosten'] * 100) if result_a['ges_kosten'] > 0 else 0
    st.metric(
        "Ersparnis/Jahr", 
        f"{ersparnis:,.0f} €",
        delta=f"{ersparnis_proz:.1f}%",
        delta_color="normal" if ersparnis > 0 else "inverse",
        help="Positive Werte bedeuten: Maschine B ist günstiger"
    )
    
with col4:
    if ersparnis > 0:
        fix_differenz = res_b['fix_jahr'] - res_a['fix_jahr']
        amortisation = fix_differenz / ersparnis if ersparnis > 0 else 999
        st.metric(
            "Amortisation", 
            f"{amortisation:.1f} Jahre",
            help="Zeit bis sich Mehrinvestition amortisiert"
        )
        if amortisation < n:
            st.success("✅ Wirtschaftlich")
        else:
            st.warning("⚠️ Kritisch prüfen")
    else:
        st.metric("Amortisation", "N/A")
        st.info("ℹ️ Maschine A günstiger")

# --- EMPFEHLUNG ---
if ersparnis > 0:
    st.success(f"""
    **💡 Empfehlung: Maschine B (Automation)** ist wirtschaftlich vorteilhaft mit einer 
    jährlichen Ersparnis von **{ersparnis:,.0f} €** ({ersparnis_proz:.1f}%). 
    Die Mehrkosten amortisieren sich in **{amortisation:.1f} Jahren**.
    """)
else:
    st.warning(f"""
    **💡 Empfehlung: Maschine A (Manuell)** ist bei diesem Produktionsprogramm die 
    wirtschaftlichere Lösung. Maschine B ist **{abs(ersparnis):,.0f} €** teurer pro Jahr.
    Prüfen Sie höhere Stückzahlen oder Zusatzaufträge.
    """)

# --- MSS-VERGLEICH ---
st.divider()
st.header("💰 Maschinenstundensatz (MSS)")

col_mss1, col_mss2 = st.columns(2)

with col_mss1:
    st.subheader("Maschine A (Manuell)")
    mss_personal_a = lohn_satz * bedien_a
    mss_gesamt_a = res_a['mss_fix'] + res_a['mss_var'] + mss_personal_a
    
    data_mss_a = pd.DataFrame({
        'Komponente': ['Fixkosten', 'Energie', 'Personal', 'GESAMT'],
        'Betrag [€/h]': [
            res_a['mss_fix'],
            res_a['mss_var'],
            mss_personal_a,
            mss_gesamt_a
        ]
    })
    st.dataframe(data_mss_a.style.format({'Betrag [€/h]': '{:.2f}'}), use_container_width=True)

with col_mss2:
    st.subheader("Maschine B (Automation)")
    mss_personal_b = lohn_satz * bedien_b
    mss_gesamt_b = res_b['mss_fix'] + res_b['mss_var'] + mss_personal_b
    
    data_mss_b = pd.DataFrame({
        'Komponente': ['Fixkosten', 'Energie', 'Personal', 'GESAMT'],
        'Betrag [€/h]': [
            res_b['mss_fix'],
            res_b['mss_var'],
            mss_personal_b,
            mss_gesamt_b
        ]
    })
    st.dataframe(data_mss_b.style.format({'Betrag [€/h]': '{:.2f}'}), use_container_width=True)

# --- KOSTENSTRUKTUR VISUALISIERUNG ---
st.divider()
st.header("📊 Kostenstruktur (Jahreskosten)")

# Berechne Personalkosten aus tatsächlichen Stunden
personal_kosten_a = lohn_satz * bedien_a * result_a['ges_stunden']
personal_kosten_b = lohn_satz * bedien_b * result_b['ges_stunden']

energie_kosten_a = res_a['mss_var'] * result_a['ges_stunden']
energie_kosten_b = res_b['mss_var'] * result_b['ges_stunden']

kategorien = ['Abschreibung', 'Zinsen', 'Wartung', 'Raum', 'Versicherung', 'Werkzeug', 'Personal', 'Energie']
werte_a = [res_a['afa'], res_a['zinsen'], res_a['wartung'], res_a['raumkosten'], 
           res_a['versicherung'], res_a['werkzeug'], personal_kosten_a, energie_kosten_a]
werte_b = [res_b['afa'], res_b['zinsen'], res_b['wartung'], res_b['raumkosten'], 
           res_b['versicherung'], res_b['werkzeug'], personal_kosten_b, energie_kosten_b]

fig, ax = plt.subplots(figsize=(12, 6))
x = np.arange(len(kategorien))
width = 0.35

bars1 = ax.bar(x - width/2, werte_a, width, label='Maschine A', color='#6b7280', alpha=0.8)
bars2 = ax.bar(x + width/2, werte_b, width, label='Maschine B', color='#3b82f6', alpha=0.8)

ax.set_ylabel('Kosten [€]', fontsize=12)
ax.set_title('Vergleich der Kostenkomponenten', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(kategorien, rotation=45, ha='right')
ax.legend()
ax.grid(axis='y', alpha=0.3)

# Werte auf Balken schreiben
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        if height > 1000:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height/1000:.1f}k', ha='center', va='bottom', fontsize=8)

plt.tight_layout()
st.pyplot(fig)

# --- BREAK-EVEN-ANALYSE ---
st.divider()
st.header("📈 Break-Even-Analyse")

st.write("""
Wie ändern sich die Gesamtkosten bei unterschiedlichen Produktionsmengen? 
Der Schnittpunkt zeigt die Break-Even-Menge.
""")

# Berechne für verschiedene Skalierungsfaktoren
faktoren = np.linspace(0.2, 3.0, 15)
kosten_verlauf_a = []
kosten_verlauf_b = []
stueckzahlen = []

for faktor in faktoren:
    df_scaled = df_serien.copy()
    df_scaled['Serien/Jahr'] = (df_scaled['Serien/Jahr'] * faktor).round().astype(int)
    
    res_temp_a = kalkuliere_programm_detail(df_scaled, res_a['mss_fix'], res_a['mss_var'], lohn_satz, bedien_a)
    res_temp_b = kalkuliere_programm_detail(df_scaled, res_b['mss_fix'], res_b['mss_var'], lohn_satz, bedien_b)
    
    kosten_verlauf_a.append(res_temp_a['ges_kosten'])
    kosten_verlauf_b.append(res_temp_b['ges_kosten'])
    stueckzahlen.append(res_temp_a['ges_stueck'])

fig2, ax2 = plt.subplots(figsize=(12, 6))
ax2.plot(stueckzahlen, kosten_verlauf_a, 'o-', linewidth=2, markersize=6, label='Maschine A', color='#6b7280')
ax2.plot(stueckzahlen, kosten_verlauf_b, 's-', linewidth=2, markersize=6, label='Maschine B', color='#3b82f6')

# Aktueller Betriebspunkt
ax2.axvline(result_a['ges_stueck'], color='red', linestyle='--', alpha=0.5, label='Aktuelles Programm')
ax2.scatter([result_a['ges_stueck']], [result_a['ges_kosten']], s=150, color='#6b7280', 
           edgecolors='red', linewidths=2, zorder=5)
ax2.scatter([result_b['ges_stueck']], [result_b['ges_kosten']], s=150, color='#3b82f6', 
           edgecolors='red', linewidths=2, zorder=5)

ax2.set_xlabel('Stückzahl pro Jahr', fontsize=12)
ax2.set_ylabel('Gesamtkosten [€]', fontsize=12)
ax2.set_title('Kostenvergleich bei verschiedenen Produktionsmengen', fontsize=14, fontweight='bold')
ax2.legend(fontsize=10)
ax2.grid(alpha=0.3)
plt.tight_layout()
st.pyplot(fig2)

# --- STÜCKKOSTENDETAILS ---
st.divider()
st.header("🔍 Stückkostenvergleich nach Serie")

# Merge der Details
df_vergleich = result_a['details'][['Serie', 'Stück/Jahr', 'Kosten/Stück (€)']].copy()
df_vergleich.rename(columns={'Kosten/Stück (€)': 'Kosten/Stk A (€)'}, inplace=True)
df_vergleich['Kosten/Stk B (€)'] = result_b['details']['Kosten/Stück (€)'].values
df_vergleich['Differenz (€)'] = df_vergleich['Kosten/Stk A (€)'] - df_vergleich['Kosten/Stk B (€)']
df_vergleich['Vorteil'] = df_vergleich['Differenz (€)'].apply(
    lambda x: f"✅ B spart {abs(x):.2f} €" if x > 0 else f"⚠️ A spart {abs(x):.2f} €"
)

st.dataframe(
    df_vergleich.style.format({
        'Stück/Jahr': '{:.0f}',
        'Kosten/Stk A (€)': '{:.2f}',
        'Kosten/Stk B (€)': '{:.2f}',
        'Differenz (€)': '{:.2f}'
    }).background_gradient(subset=['Differenz (€)'], cmap='RdYlGn'),
    use_container_width=True
)

# --- DETAILLIERTE AUFSCHLÜSSELUNG ---
with st.expander("📋 Detaillierte Kostenaufschlüsselung"):
    tab1, tab2 = st.tabs(["Maschine A", "Maschine B"])
    
    with tab1:
        st.subheader("Maschine A - Details")
        st.dataframe(
            result_a['details'].style.format({
                'Stück/Jahr': '{:.0f}',
                'Zeit Bearb (h)': '{:.1f}',
                'Zeit Rüst (h)': '{:.1f}',
                'Kosten Bearb (€)': '{:.2f}',
                'Kosten Rüst (€)': '{:.2f}',
                'Kosten Gesamt (€)': '{:.2f}',
                'Kosten/Stück (€)': '{:.2f}'
            }),
            use_container_width=True
        )
        st.write(f"**Summe Gesamtkosten:** {result_a['ges_kosten']:,.2f} €")
    
    with tab2:
        st.subheader("Maschine B - Details")
        st.dataframe(
            result_b['details'].style.format({
                'Stück/Jahr': '{:.0f}',
                'Zeit Bearb (h)': '{:.1f}',
                'Zeit Rüst (h)': '{:.1f}',
                'Kosten Bearb (€)': '{:.2f}',
                'Kosten Rüst (€)': '{:.2f}',
                'Kosten Gesamt (€)': '{:.2f}',
                'Kosten/Stück (€)': '{:.2f}'
            }),
            use_container_width=True
        )
        st.write(f"**Summe Gesamtkosten:** {result_b['ges_kosten']:,.2f} €")

# --- FIXKOSTENAUFSCHLÜSSELUNG ---
with st.expander("💶 Fixkostenaufschlüsselung"):
    col_fix1, col_fix2 = st.columns(2)
    
    with col_fix1:
        st.subheader("Maschine A")
        fix_df_a = pd.DataFrame({
            'Position': ['Abschreibung', 'Kalk. Zinsen', 'Wartung', 'Raumkosten', 'Versicherung', 'Werkzeug', 'SUMME'],
            'Betrag [€/Jahr]': [
                res_a['afa'], res_a['zinsen'], res_a['wartung'], 
                res_a['raumkosten'], res_a['versicherung'], res_a['werkzeug'],
                res_a['fix_jahr']
            ]
        })
        st.dataframe(fix_df_a.style.format({'Betrag [€/Jahr]': '{:,.2f}'}), use_container_width=True)
    
    with col_fix2:
        st.subheader("Maschine B")
        fix_df_b = pd.DataFrame({
            'Position': ['Abschreibung', 'Kalk. Zinsen', 'Wartung', 'Raumkosten', 'Versicherung', 'Werkzeug', 'SUMME'],
            'Betrag [€/Jahr]': [
                res_b['afa'], res_b['zinsen'], res_b['wartung'], 
                res_b['raumkosten'], res_b['versicherung'], res_b['werkzeug'],
                res_b['fix_jahr']
            ]
        })
        st.dataframe(fix_df_b.style.format({'Betrag [€/Jahr]': '{:,.2f}'}), use_container_width=True)

# --- SENSITIVITÄTSANALYSE ---
with st.expander("🔬 Sensitivitätsanalyse"):
    st.subheader("Einfluss von Parametern auf die Wirtschaftlichkeit")
    
    sens_param = st.selectbox(
        "Welcher Parameter soll variiert werden?",
        ["Lohnsatz", "Strompreis", "Nutzungsgrad A", "Nutzungsgrad B", "Bedienfaktor B"]
    )
    
    if sens_param == "Lohnsatz":
        lohn_range = np.linspace(lohn_satz * 0.5, lohn_satz * 1.5, 20)
        ersparnis_sens = []
        for lohn_test in lohn_range:
            r_a_temp = kalkuliere_programm_detail(df_serien, res_a['mss_fix'], res_a['mss_var'], lohn_test, bedien_a)
            r_b_temp = kalkuliere_programm_detail(df_serien, res_b['mss_fix'], res_b['mss_var'], lohn_test, bedien_b)
            ersparnis_sens.append(r_a_temp['ges_kosten'] - r_b_temp['ges_kosten'])
        
        fig_sens, ax_sens = plt.subplots(figsize=(10, 5))
        ax_sens.plot(lohn_range, ersparnis_sens, linewidth=2, color='purple')
        ax_sens.axhline(0, color='red', linestyle='--', alpha=0.7)
        ax_sens.axvline(lohn_satz, color='green', linestyle='--', alpha=0.7, label='Aktueller Wert')
        ax_sens.set_xlabel('Lohnsatz [€/h]')
        ax_sens.set_ylabel('Ersparnis durch Maschine B [€]')
        ax_sens.set_title('Sensitivität: Lohnsatz')
        ax_sens.legend()
        ax_sens.grid(alpha=0.3)
        st.pyplot(fig_sens)
#--- FOOTER ---
st.divider()
st.caption("""
Hinweis: Diese Berechnung basiert auf den angegebenen Parametern und dient als Entscheidungshilfe.
Bitte prüfen Sie weitere Faktoren wie Technologierisiko, Flexibilität, Lieferzeiten und strategische Aspekte.
""")
