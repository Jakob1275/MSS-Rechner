import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- SEITENKONFIGURATION ---
st.set_page_config(page_title="Wirtschaftlichkeitsvergleich Maschinen", layout="wide")

st.title("📊 Wirtschaftlichkeitsvergleich: Manuell vs. Automation")
st.markdown("""
Vergleichen Sie zwei Investitionsalternativen unter Berücksichtigung von Fixkosten, 
variablen Kosten und einem individuellen Produktionsprogramm über verschiedene Serien.
""")

# --- SIDEBAR: MASCHINENPARAMETER ---
with st.sidebar:
    st.header("⚙️ Grundparameter")
    ak = st.number_input("Anschaffungskosten (Gesamt) [€]", value=600000, step=10000)
    n = st.number_input("Nutzungsdauer [Jahre]", value=20, step=1)
    zins_satz = st.slider("Kalk. Zinssatz [%]", 0.0, 10.0, 5.0) / 100
    lohn_satz = st.number_input("Lohnsatz (belastet) [€/h]", value=65.0)
    strom_preis = st.number_input("Strompreis [€/kWh]", value=0.30)
    raum_preis = st.number_input("Raumkosten [€/m²]", value=15.0)

    st.divider()

    # Spalten für den direkten Vergleich in der Sidebar
    st.subheader("Maschinenspezifische Daten")
    
    col_sid1, col_sid2 = st.columns(2)
    with col_sid1:
        st.info("Maschine A (Manuell)")
        h_jahr_a = st.number_input("Std./Jahr (A)", value=2400)
        nutzgrad_a = st.slider("Nutzgrad A [%]", 0, 100, 75) / 100
        bedien_a = 1.0
        wartung_a = 0.025
        raum_a = st.number_input("Fläche A [m²]", value=20)
        energie_a = st.number_input("Verbrauch A [kW]", value=8.0)
        vers_a = st.number_input("Versicherung A [€/J]", value=500)

    with col_sid2:
        st.success("Maschine B (Auto)")
        h_jahr_b = st.number_input("Std./Jahr (B)", value=5000)
        nutzgrad_b = st.slider("Nutzgrad B [%]", 0, 100, 85) / 100
        bedien_b = st.slider("Bedienfaktor B", 0.1, 1.0, 0.3)
        wartung_b = 0.045
        raum_b = st.number_input("Fläche B [m²]", value=35)
        energie_b = st.number_input("Verbrauch B [kW]", value=18.0)
        vers_b = st.number_input("Versicherung B [€/J]", value=1200)

# --- BERECHNUNGSFUNKTIONEN ---
def berechne_mss(ak, n, zins, wartung_satz, raum, r_preis, vers, h_jahr, nutzgrad, kw, s_preis):
    # Fixkosten
    afa = ak / n
    zinsen = (ak / 2) * zins
    wartung = ak * wartung_satz
    raumkosten = raum * r_preis
    fix_jahr = afa + zinsen + wartung + raumkosten + vers
    
    # Stundenrechnung
    stunden_effektiv = h_jahr * nutzgrad
    mss_fix = fix_jahr / stunden_effektiv if stunden_effektiv > 0 else 0
    
    # Variable Kosten
    energie_h = kw * s_preis
    
    return mss_fix, energie_h, fix_jahr, stunden_effektiv

# Ergebnisse berechnen
mss_f_a, mss_v_a, fix_j_a, std_e_a = berechne_mss(ak, n, zins_satz, wartung_a, raum_a, raum_preis, vers_a, h_jahr_a, nutzgrad_a, energie_a, strom_preis)
mss_f_b, mss_v_b, fix_j_b, std_e_b = berechne_mss(ak, n, zins_satz, wartung_b, raum_b, raum_preis, vers_b, h_jahr_b, nutzgrad_b, energie_b, strom_preis)

# --- PRODUKTIONSPROGRAMM ---
st.header("📋 Produktionsprogramm (Serien)")
st.write("Geben Sie hier die verschiedenen Bauteil-Serien ein, die pro Jahr gefertigt werden sollen.")

default_serien = {
    "Bauteil": ["Welle Typ 1", "Gehäuse groß", "Flansch klein"],
    "Serien pro Jahr": [20, 10, 50],
    "Stück pro Serie": [50, 20, 100],
    "Bearbeitungszeit (min/Stk)": [10, 45, 5],
    "Rüstzeit (min/Serie)": [45, 120, 30]
}
df_serien = st.data_editor(pd.DataFrame(default_serien), num_rows="dynamic", use_container_width=True)

# --- GESAMTVERGLEICH BERECHNEN ---
def kalkuliere_programm(df, mss_fix, mss_var, lohn, faktor):
    ges_kosten = 0
    ges_stunden = 0
    
    for _, row in df.iterrows():
        stk_jahr = row["Serien pro Jahr"] * row["Stück pro Serie"]
        t_bearb_h = (stk_jahr * row["Bearbeitungszeit (min/Stk)"]) / 60
        t_ruest_h = (row["Serien pro Jahr"] * row["Rüstzeit (min/Serie)"]) / 60
        
        # Kosten = Zeit * (Maschine + Personal)
        kosten_bearb = t_bearb_h * (mss_fix + mss_var + (lohn * faktor))
        kosten_ruest = t_ruest_h * (mss_fix + mss_var + lohn) # Rüstzeit meist 1:1 Personal
        
        ges_kosten += (kosten_bearb + kosten_ruest)
        ges_stunden += (t_bearb_h + t_ruest_h)
        
    return ges_kosten, ges_stunden

kosten_a, std_a = kalkuliere_programm(df_serien, mss_f_a, mss_v_a, lohn_satz, bedien_a)
kosten_b, std_b = kalkuliere_programm(df_serien, mss_f_b, mss_v_b, lohn_satz, bedien_b)

# --- DISPLAY ERGEBNISSE ---
st.divider()
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Gesamtkosten Manuell (A)", f"{kosten_a:,.2f} €")
    st.write(f"Auslastung: {std_a:,.0f} / {std_e_a:,.0f} h")
with c2:
    ersparnis = kosten_a - kosten_b
    st.metric("Gesamtkosten Auto (B)", f"{kosten_b:,.2f} €", delta=f"{ersparnis:,.2f} € Ersparnis")
    st.write(f"Auslastung: {std_b:,.0f} / {std_e_b:,.0f} h")
with c3:
    if ersparnis > 0:
        amortisation = (fix_j_b - fix_j_a) / (ersparnis / 1) if ersparnis > 0 else 0
        st.write("✅ Automation wirtschaftlicher")
    else:
        st.write("⚠️ Manuelle Fertigung günstiger")

# --- VISUALISIERUNG ---
st.subheader("Kostenvergleich nach Kategorien")

# Daten für Chart aufbereiten
chart_data = pd.DataFrame({
    "Maschine": ["Manuell (A)", "Automation (B)"],
    "Gesamtkosten [€]": [kosten_a, kosten_b]
})

fig, ax = plt.subplots(figsize=(8, 4))
bars = ax.bar(chart_data["Maschine"], chart_data["Gesamtkosten [€]"], color=['#555555', '#007bff'])
ax.set_ylabel("Euro pro Jahr")
ax.set_title("Vergleich der jährlichen Gesamtkosten")

# Werte an die Balken schreiben
for bar in bars:
    yval = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, yval + 5000, f"{yval:,.0f} €", ha='center', va='bottom', fontweight='bold')

st.pyplot(fig)

# --- DETAILS ---
with st.expander("Details der Maschinenstundensatz-Kalkulation (MSS)"):
    det1, det2 = st.columns(2)
    det1.write("**Okuma (A)**")
    det1.write(f"Fixkosten/Jahr: {fix_j_a:,.2f} €")
    det1.write(f"MSS Fix: {mss_f_a:.2f} €/h")
    det1.write(f"Variable (Energie): {mss_v_a:.2f} €/h")
    
    det2.write("**DMG (B)**")
    det2.write(f"Fixkosten/Jahr: {fix_j_b:,.2f} €")
    det2.write(f"MSS Fix: {mss_f_b:.2f} €/h")
    det2.write(f"Variable (Energie): {mss_v_b:.2f} €/h")
