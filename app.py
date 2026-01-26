import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from datetime import datetime

# --- SEITENKONFIGURATION ---
st.set_page_config(page_title="Wirtschaftlichkeitsvergleich Werkzeugmaschinen", layout="wide")

st.title("Wirtschaftlichkeitsvergleich Werkzeugmaschinen")
st.markdown("""
Detaillierter Vergleich zweier Investitionsalternativen mit Fixkosten, variablen Kosten,
Stückkostenkalkulation, Break-Even-Analyse, Amortisation und Barwert.
""")

# =========================
# BERECHNUNGSFUNKTIONEN
# =========================
@st.cache_data(show_spinner=False)
def berechne_mss(ak, n, zins, wartung_satz, raum, r_preis, vers, werkzeug, h_jahr, nutzgrad, kw, s_preis, restwert=0.0):
    """
    Berechnet Maschinenstundensatz und Kostenkomponenten
    - AfA: linear auf Basis (AK - Restwert)
    - Kalk. Zinsen: auf durchschnittlich gebundenes Kapital ~ (AK + Restwert)/2
    """
    afa_basis = max(0.0, ak - restwert)
    afa = afa_basis / n if n > 0 else 0.0

    geb_kapital_mittel = (ak + restwert) / 2.0
    zinsen = geb_kapital_mittel * zins

    wartung = ak * wartung_satz
    raumkosten = raum * r_preis * 12
    fix_jahr = afa + zinsen + wartung + raumkosten + vers + werkzeug

    stunden_effektiv = h_jahr * nutzgrad
    mss_fix = fix_jahr / stunden_effektiv if stunden_effektiv > 0 else 0.0
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

@st.cache_data(show_spinner=False)
def kalkuliere_programm_detail(df, mss_fix, mss_var, lohn, bedien_faktor, machine="A"):
    """Detaillierte Kalkulation mit Stückkostenaufschlüsselung (Maschine A oder B)"""
    details = []
    ges_kosten = 0.0
    ges_stunden = 0.0
    ges_stueck = 0

    if machine == "A":
        col_bearb = "Bearbzeit (min/Stk) A"
        col_ruest = "Rüstzeit (min) A"
        ruest_bedien_faktor = 1.0
    else:
        col_bearb = "Bearbzeit (min/Stk) B"
        col_ruest = "Rüstzeit (min) B"
        ruest_bedien_faktor = 1.0

    for _, row in df.iterrows():
        serie = row["Serie"]
        serien_jahr = float(row["Serien/Jahr"])
        stueck_serie = float(row["Stück/Serie"])

        t_bearb_min = float(row[col_bearb])
        t_ruest_min = float(row[col_ruest])

        stueck_jahr = serien_jahr * stueck_serie
        t_bearb_h = (stueck_jahr * t_bearb_min) / 60.0
        t_ruest_h = (serien_jahr * t_ruest_min) / 60.0

        # Bearbeitung (Automation über Bedienfaktor)
        mss_gesamt_bearb = mss_fix + mss_var + (lohn * bedien_faktor)
        kosten_bearb = t_bearb_h * mss_gesamt_bearb

        # Rüsten (typisch: volle Bedienung)
        mss_gesamt_ruest = mss_fix + mss_var + (lohn * ruest_bedien_faktor)
        kosten_ruest = t_ruest_h * mss_gesamt_ruest

        kosten_ges = kosten_bearb + kosten_ruest
        kosten_stueck = kosten_ges / stueck_jahr if stueck_jahr > 0 else 0.0

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

        ges_kosten += float(kosten_ges)
        ges_stunden += float(t_bearb_h + t_ruest_h)
        ges_stueck += int(stueck_jahr)

    return {
        'details': pd.DataFrame(details),
        'ges_kosten': float(ges_kosten),
        'ges_stunden': float(ges_stunden),
        'ges_stueck': int(ges_stueck)
    }

def fig_to_base64(fig):
    """Konvertiert Matplotlib Figure zu Base64 für HTML-Einbettung"""
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{img_str}"

def npv_alternative(ak_a, ak_b, rest_a, rest_b, annual_saving, zins, n_years):
    """
    NPV aus Sicht 'B statt A'
      t=0: - (AK_B - AK_A)
      t=1..n: + annual_saving
      t=n: + (Rest_B - Rest_A)
    """
    mehrinvest = ak_b - ak_a
    npv = -mehrinvest

    for t in range(1, n_years + 1):
        npv += annual_saving / ((1 + zins) ** t)

    npv += (rest_b - rest_a) / ((1 + zins) ** n_years)
    return float(npv)

def npv_alternative_series(ak_a, ak_b, rest_a, rest_b, savings_series, zins):
    """
    NPV aus Sicht 'B statt A' mit jährlicher Einsparungsreihe
      t=0: - (AK_B - AK_A)
      t=1..n: + saving_t
      t=n: + (Rest_B - Rest_A)
    """
    mehrinvest = ak_b - ak_a
    npv = -mehrinvest
    for t, saving in enumerate(savings_series, start=1):
        npv += float(saving) / ((1 + zins) ** t)
    if savings_series:
        n_years = len(savings_series)
        npv += (rest_b - rest_a) / ((1 + zins) ** n_years)
    return float(npv)

def discounted_payback(mehrinvest, savings_series, zins):
    """Dynamische Amortisation (diskontierte Zahlungsreihe)."""
    if mehrinvest <= 0:
        return 0.0
    cumulative = 0.0
    for t, saving in enumerate(savings_series, start=1):
        cumulative += float(saving) / ((1 + zins) ** t)
        if cumulative >= mehrinvest:
            return float(t)
    return None

@st.cache_data(show_spinner=False)
def annual_costs_series(res, result, lohn, bedien_factor, years, cost_escalation, prod_growth):
    """
    Vereinfachte Kostenreihe:
    - Fixkosten eskalieren mit cost_escalation
    - Variable Kosten eskalieren mit cost_escalation und skalieren mit Produktionswachstum
    """
    fixed0 = float(res['fix_jahr'])
    variable0 = (float(res['mss_var']) + float(lohn) * float(bedien_factor)) * float(result['ges_stunden'])

    series = []
    for t in range(years):
        esc = (1 + cost_escalation) ** t
        prod = (1 + prod_growth) ** t
        fixed = fixed0 * esc
        variable = variable0 * esc * prod
        series.append(float(fixed + variable))
    return series

def kapazitaetscheck(result, res):
    if res['stunden_effektiv'] <= 0:
        return False, 0.0
    auslastung = result['ges_stunden'] / res['stunden_effektiv']
    ok = result['ges_stunden'] <= res['stunden_effektiv']
    return ok, float(auslastung)

# =========================
# SIDEBAR: MASCHINENPARAMETER
# =========================
with st.sidebar:
    st.header("Grundparameter")

    ak_a = st.number_input("Anschaffungskosten Maschine A [€]", value=600000, step=10000)
    ak_b = st.number_input("Anschaffungskosten Maschine B [€]", value=950000, step=10000)

    n = st.number_input("Nutzungsdauer [Jahre]", value=20, step=1, min_value=1)
    zins_satz = st.slider("Kalk. Zinssatz [%]", 0.0, 10.0, 5.0, 0.5) / 100

    lohn_satz = st.number_input("Lohnkosten [€/h]", value=65.0, step=1.0)
    strom_preis = st.number_input("Strompreis [€/kWh]", value=0.30, step=0.01)
    raum_preis = st.number_input("Raumkosten [€/m²/Monat]", value=15.0, step=1.0)

    st.divider()
    st.subheader("Annahmen (Erste Abschätzung)")
    kosten_steigerung = st.slider("Kostensteigerung p.a. [%]", 0.0, 8.0, 2.0, 0.25) / 100
    prod_wachstum = st.slider("Produktionswachstum p.a. [%]", -5.0, 10.0, 0.0, 0.5) / 100

    st.divider()
    st.caption("Optional (für Barwert/NPV): Restwert am Ende der Nutzungsdauer")
    restwert_a = st.number_input("Restwert A am Ende [€]", value=0, step=10000, min_value=0)
    restwert_b = st.number_input("Restwert B am Ende [€]", value=0, step=10000, min_value=0)

    st.divider()
    st.subheader("Maschine A")
    name_a = st.text_input("Bezeichnung A", value="Okuma LT3000-2T1MY")
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
    st.subheader("Maschine B")
    name_b = st.text_input("Bezeichnung B", value="DMG CTX 550 mir Robo2Go")
    h_jahr_b = st.number_input("Betriebsstunden/Jahr (B)", value=5000, step=100)
    nutzgrad_b = st.slider("Nutzungsgrad B [%]", 0, 100, 85, 5) / 100
    bedien_b = st.slider("Bedienfaktor B", 0.1, 1.0, 0.3, 0.05)
    wartung_b = st.slider("Wartungssatz B [% von AK]", 0.0, 10.0, 4.5, 0.5) / 100
    raum_b = st.number_input("Platzbedarf B [m²]", value=35, step=5)
    energie_b = st.number_input("Leistungsaufnahme B [kW]", value=18.0, step=1.0)
    vers_b = st.number_input("Versicherung B [€/Jahr]", value=1200, step=100)
    werkzeug_b = st.number_input("Werkzeugkosten B [€/Jahr]", value=8000, step=500)

# =========================
# MSS / Fixkosten je Maschine
# =========================
res_a = berechne_mss(ak_a, n, zins_satz, wartung_a, raum_a, raum_preis, vers_a, werkzeug_a,
                     h_jahr_a, nutzgrad_a, energie_a, strom_preis, restwert=restwert_a)

res_b = berechne_mss(ak_b, n, zins_satz, wartung_b, raum_b, raum_preis, vers_b, werkzeug_b,
                     h_jahr_b, nutzgrad_b, energie_b, strom_preis, restwert=restwert_b)

if res_a['stunden_effektiv'] <= 0:
    st.warning("Maschine A: Effektive Jahresstunden sind 0 oder negativ. Bitte Eingaben prüfen.")
if res_b['stunden_effektiv'] <= 0:
    st.warning("Maschine B: Effektive Jahresstunden sind 0 oder negativ. Bitte Eingaben prüfen.")

# =========================
# PRODUKTIONSPROGRAMM
# =========================
st.header("Produktionsprogramm")
st.write("Definieren Sie die zu fertigenden Serien. Sie können Zeilen hinzufügen oder löschen.")

default_serien = pd.DataFrame({
    "Serie": ["Welle Typ 1", "Welle Typ 2", "Welle Typ 3"],
    "Serien/Jahr": [100, 100, 100],
    "Stück/Serie": [10, 10, 10],
    "Bearbzeit (min/Stk) A": [10, 10, 10],
    "Bearbzeit (min/Stk) B": [12, 12, 12],
    "Rüstzeit (min) A": [45, 45, 45],
    "Rüstzeit (min) B": [60, 60, 60]
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

# Programm-Kalkulation
result_a = kalkuliere_programm_detail(df_serien, res_a['mss_fix'], res_a['mss_var'], lohn_satz, bedien_a, machine="A")
result_b = kalkuliere_programm_detail(df_serien, res_b['mss_fix'], res_b['mss_var'], lohn_satz, bedien_b, machine="B")

# Kapazitätscheck
ok_a, ausl_a = kapazitaetscheck(result_a, res_a)
ok_b, ausl_b = kapazitaetscheck(result_b, res_b)

if not ok_a:
    st.error(f"❌ Kapazität reicht nicht für Maschine A ({name_a}). "
             f"Benötigt: {result_a['ges_stunden']:.0f} h, verfügbar: {res_a['stunden_effektiv']:.0f} h "
             f"(Auslastung: {ausl_a*100:.1f}%).")

if not ok_b:
    st.error(f"❌ Kapazität reicht nicht für Maschine B ({name_b}). "
             f"Benötigt: {result_b['ges_stunden']:.0f} h, verfügbar: {res_b['stunden_effektiv']:.0f} h "
             f"(Auslastung: {ausl_b*100:.1f}%).")

vergleich_ok = ok_a and ok_b
if not vergleich_ok:
    st.warning("⚠️ Achtung: Mindestens eine Alternative kann das Produktionsprogramm kapazitiv nicht abbilden. "
               "Kostenvergleich ist dann nur eingeschränkt interpretierbar (Überstunden, Fremdvergabe oder Zusatzmaschine nötig).")

# =========================
# KERNERGEBNISSE
# =========================
st.divider()
st.header("🎯 Kernergebnisse")

ersparnis = result_a['ges_kosten'] - result_b['ges_kosten']
ersparnis_proz = (ersparnis / result_a['ges_kosten'] * 100) if result_a['ges_kosten'] > 0 else 0.0
mehrinvest = ak_b - ak_a

# Kostenreihen für dynamische Bewertung
costs_a_series = annual_costs_series(res_a, result_a, lohn_satz, bedien_a, int(n), kosten_steigerung, prod_wachstum)
costs_b_series = annual_costs_series(res_b, result_b, lohn_satz, bedien_b, int(n), kosten_steigerung, prod_wachstum)
savings_series = [a - b for a, b in zip(costs_a_series, costs_b_series)]

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Kosten Maschine A", f"{result_a['ges_kosten']:,.0f} €".replace(",", "."),
              help="Gesamtkosten für das Produktionsprogramm pro Jahr")
    st.caption(f"⏱️ Auslastung: {ausl_a*100:.1f}% ({result_a['ges_stunden']:.0f}/{res_a['stunden_effektiv']:.0f} h)")

with col2:
    st.metric("Kosten Maschine B", f"{result_b['ges_kosten']:,.0f} €".replace(",", "."),
              help="Gesamtkosten für das Produktionsprogramm pro Jahr")
    st.caption(f"⏱️ Auslastung: {ausl_b*100:.1f}% ({result_b['ges_stunden']:.0f}/{res_b['stunden_effektiv']:.0f} h)")

with col3:
    st.metric("Ersparnis/Jahr", f"{ersparnis:,.0f} €".replace(",", "."),
              delta=f"{ersparnis_proz:.1f}%",
              delta_color="normal" if ersparnis > 0 else "inverse",
              help="Positive Werte bedeuten: Maschine B ist günstiger")

with col4:
    # Amortisation korrekt: (AK_B - AK_A) / jährliche Einsparung
    if ersparnis > 0 and mehrinvest > 0:
        amortisation = mehrinvest / ersparnis
        st.metric("Amortisation", f"{amortisation:.1f} Jahre",
                  help="(AK_B - AK_A) / jährliche Einsparung")
        if amortisation < n:
            st.success("✅ Wirtschaftlich")
        else:
            st.warning("⚠️ Kritisch prüfen")
    elif ersparnis > 0 and mehrinvest <= 0:
        amortisation = 0.0
        st.metric("Amortisation", "0.0 Jahre",
                  help="B ist nicht teurer in der Anschaffung und spart jährlich → sofort wirtschaftlich.")
        st.success("✅ Wirtschaftlich")
    else:
        amortisation = None
        st.metric("Amortisation", "N/A")
        st.info("ℹ️ Keine Einsparung durch B")

# Dynamische Amortisation (diskontiert)
dyn_amort = discounted_payback(mehrinvest, savings_series, zins_satz)
if dyn_amort is not None:
    st.caption(f"Dynamische Amortisation (diskontiert): {dyn_amort:.0f} Jahre")
else:
    st.caption("Dynamische Amortisation (diskontiert): nicht erreicht")

# Empfehlungstext (mit Hinweis auf Kapazität)
if ersparnis > 0:
    empfehlung_text = f"""**💡 Empfehlung: Maschine B ({name_b})** ist wirtschaftlich vorteilhaft mit einer
    jährlichen Ersparnis von **{ersparnis:,.0f} €** ({ersparnis_proz:.1f}%)."""
    if mehrinvest > 0 and amortisation is not None:
        empfehlung_text += f" Die Mehrinvestition amortisiert sich in **{amortisation:.1f} Jahren**."
    if not vergleich_ok:
        empfehlung_text += " **Hinweis:** Kapazität ist nicht für beide Alternativen gegeben → Vergleich eingeschränkt."
    st.success(empfehlung_text)
else:
    empfehlung_text = f"""**💡 Empfehlung: Maschine A ({name_a})** ist bei diesem Produktionsprogramm die
    wirtschaftlichere Lösung. Maschine B ist **{abs(ersparnis):,.0f} €** teurer pro Jahr."""
    if not vergleich_ok:
        empfehlung_text += " **Hinweis:** Kapazität ist nicht für beide Alternativen gegeben → Vergleich eingeschränkt."
    st.warning(empfehlung_text)

# NPV / Barwert
st.divider()
st.subheader("📌 Barwert (NPV) der Alternative B gegenüber A")
if vergleich_ok:
    npv_b_vs_a = npv_alternative(
        ak_a=ak_a, ak_b=ak_b,
        rest_a=restwert_a, rest_b=restwert_b,
        annual_saving=ersparnis,
        zins=zins_satz,
        n_years=n
    )
    npv_b_vs_a_dyn = npv_alternative_series(
        ak_a=ak_a, ak_b=ak_b,
        rest_a=restwert_a, rest_b=restwert_b,
        savings_series=savings_series,
        zins=zins_satz
    )
    if npv_b_vs_a >= 0:
        st.success(f"✅ NPV (B statt A): {npv_b_vs_a:.0f} €  → B ist aus Barwertsicht vorteilhaft.")
    else:
        st.warning(f"⚠️ NPV (B statt A): {npv_b_vs_a:.0f} €  → A ist aus Barwertsicht vorteilhafter.")
    st.caption(f"NPV dynamisch (mit Kostensteigerung/Produktionswachstum): {npv_b_vs_a_dyn:.0f} €")
else:
    npv_b_vs_a = None
    npv_b_vs_a_dyn = None
    st.info("NPV wird nicht ausgewertet, da mindestens eine Alternative kapazitiv nicht machbar ist.")

# =========================
# MSS-VERGLEICH
# =========================
st.divider()
st.header("💰 Maschinenstundensatz (MSS)")

col_mss1, col_mss2 = st.columns(2)

with col_mss1:
    st.subheader(f"{name_a}")
    mss_personal_a = lohn_satz * bedien_a
    mss_gesamt_a = res_a['mss_fix'] + res_a['mss_var'] + mss_personal_a

    data_mss_a = pd.DataFrame({
        'Komponente': ['Fixkosten', 'Energie', 'Personal', 'GESAMT'],
        'Betrag [€/h]': [res_a['mss_fix'], res_a['mss_var'], mss_personal_a, mss_gesamt_a]
    })
    st.dataframe(
        data_mss_a.style.format({'Betrag [€/h]': '{:.2f}'}).set_properties(subset=['Betrag [€/h]'], **{'text-align': 'right'}),
        use_container_width=True
    )

with col_mss2:
    st.subheader(f"{name_b}")
    mss_personal_b = lohn_satz * bedien_b
    mss_gesamt_b = res_b['mss_fix'] + res_b['mss_var'] + mss_personal_b

    data_mss_b = pd.DataFrame({
        'Komponente': ['Fixkosten', 'Energie', 'Personal', 'GESAMT'],
        'Betrag [€/h]': [res_b['mss_fix'], res_b['mss_var'], mss_personal_b, mss_gesamt_b]
    })
    st.dataframe(
        data_mss_b.style.format({'Betrag [€/h]': '{:.2f}'}).set_properties(subset=['Betrag [€/h]'], **{'text-align': 'right'}),
        use_container_width=True
    )

# =========================
# KOSTENSTRUKTUR VISUALISIERUNG
# =========================
st.divider()
st.header("📊 Kostenstruktur (Jahreskosten)")

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

bars1 = ax.bar(x - width/2, werte_a, width, label=name_a, color='#6b7280', alpha=0.8)
bars2 = ax.bar(x + width/2, werte_b, width, label=name_b, color='#3b82f6', alpha=0.8)

ax.set_ylabel('Kosten [€]', fontsize=12)
ax.set_title('Vergleich der Kostenkomponenten', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(kategorien, rotation=45, ha='right')
ax.legend()
ax.grid(axis='y', alpha=0.3)

for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        if height > 1000:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height/1000:.1f}k', ha='center', va='bottom', fontsize=8)

plt.tight_layout()
kostenstruktur_img = fig_to_base64(fig)
st.pyplot(fig)

# =========================
# BREAK-EVEN-ANALYSE
# =========================
st.divider()
st.header("📈 Break-Even-Analyse")

st.write("""
Wie ändern sich die Gesamtkosten bei unterschiedlichen Produktionsmengen?
Der Schnittpunkt zeigt die Break-Even-Menge.
""")

faktoren = np.linspace(0.2, 3.0, 15)
kosten_verlauf_a = []
kosten_verlauf_b = []
stueckzahlen = []

for faktor in faktoren:
    df_scaled = df_serien.copy()
    df_scaled['Serien/Jahr'] = (df_scaled['Serien/Jahr'] * faktor).round().astype(int)

    res_temp_a = kalkuliere_programm_detail(df_scaled, res_a['mss_fix'], res_a['mss_var'], lohn_satz, bedien_a, machine="A")
    res_temp_b = kalkuliere_programm_detail(df_scaled, res_b['mss_fix'], res_b['mss_var'], lohn_satz, bedien_b, machine="B")

    kosten_verlauf_a.append(res_temp_a['ges_kosten'])
    kosten_verlauf_b.append(res_temp_b['ges_kosten'])
    stueckzahlen.append(res_temp_a['ges_stueck'])

fig2, ax2 = plt.subplots(figsize=(12, 6))
ax2.plot(stueckzahlen, kosten_verlauf_a, 'o-', linewidth=2, markersize=6, label=name_a, color='#6b7280')
ax2.plot(stueckzahlen, kosten_verlauf_b, 's-', linewidth=2, markersize=6, label=name_b, color='#3b82f6')

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
breakeven_img = fig_to_base64(fig2)
st.pyplot(fig2)

# =========================
# STÜCKKOSTENDETAILS
# =========================
st.divider()
st.header("🔍 Stückkostenvergleich nach Serie")

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

# =========================
# DETAILLIERTE AUFSCHLÜSSELUNG
# =========================
with st.expander("📋 Detaillierte Kostenaufschlüsselung"):
    tab1, tab2 = st.tabs([name_a, name_b])

    with tab1:
        st.subheader(f"{name_a} - Details")
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
        st.subheader(f"{name_b} - Details")
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

# =========================
# FIXKOSTENAUFSCHLÜSSELUNG
# =========================
with st.expander("💶 Fixkostenaufschlüsselung"):
    col_fix1, col_fix2 = st.columns(2)

    with col_fix1:
        st.subheader(name_a)
        fix_df_a = pd.DataFrame({
            'Position': ['Abschreibung', 'Kalk. Zinsen', 'Wartung', 'Raumkosten', 'Versicherung', 'Werkzeug', 'SUMME'],
            'Betrag [€/Jahr]': [
                res_a['afa'], res_a['zinsen'], res_a['wartung'],
                res_a['raumkosten'], res_a['versicherung'], res_a['werkzeug'],
                res_a['fix_jahr']
            ]
        })
        st.dataframe(
            fix_df_a.style.format({'Betrag [€/Jahr]': '{:,.2f}'}).set_properties(subset=['Betrag [€/Jahr]'], **{'text-align': 'right'}),
            use_container_width=True
        )

    with col_fix2:
        st.subheader(name_b)
        fix_df_b = pd.DataFrame({
            'Position': ['Abschreibung', 'Kalk. Zinsen', 'Wartung', 'Raumkosten', 'Versicherung', 'Werkzeug', 'SUMME'],
            'Betrag [€/Jahr]': [
                res_b['afa'], res_b['zinsen'], res_b['wartung'],
                res_b['raumkosten'], res_b['versicherung'], res_b['werkzeug'],
                res_b['fix_jahr']
            ]
        })
        st.dataframe(
            fix_df_b.style.format({'Betrag [€/Jahr]': '{:,.2f}'}).set_properties(subset=['Betrag [€/Jahr]'], **{'text-align': 'right'}),
            use_container_width=True
        )

# =========================
# HTML REPORT
# =========================
def generate_html_report():
    """Generiert einen vollständigen HTML-Bericht"""
    amort_text = f"{amortisation:.1f}" if amortisation is not None else "N/A"
    def fmt_eur(value, decimals=0):
        try:
            fmt = f"{{:,.{decimals}f}}"
            return fmt.format(value).replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return str(value)

    npv_text = f"{fmt_eur(npv_b_vs_a)} €" if npv_b_vs_a is not None else "N/A"

    data_mss_a_html = data_mss_a.copy()
    data_mss_a_html['Betrag [€/h]'] = data_mss_a_html['Betrag [€/h]'].apply(lambda v: f"{fmt_eur(v, 2)} €")
    data_mss_b_html = data_mss_b.copy()
    data_mss_b_html['Betrag [€/h]'] = data_mss_b_html['Betrag [€/h]'].apply(lambda v: f"{fmt_eur(v, 2)} €")

    fix_df_a_html = fix_df_a.copy()
    fix_df_a_html['Betrag [€/Jahr]'] = fix_df_a_html['Betrag [€/Jahr]'].apply(lambda v: f"{fmt_eur(v, 2)} €")
    fix_df_b_html = fix_df_b.copy()
    fix_df_b_html['Betrag [€/Jahr]'] = fix_df_b_html['Betrag [€/Jahr]'].apply(lambda v: f"{fmt_eur(v, 2)} €")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Wirtschaftlichkeitsvergleich - {name_a} vs {name_b}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.5em;
            }}
            .header h2 {{
                margin: 10px 0 0;
                color: #ffffff;
                font-weight: 600;
            }}
            .header .date {{
                margin-top: 10px;
                opacity: 0.9;
            }}
            .section {{
                background: white;
                padding: 25px;
                margin-bottom: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }}
            .metric-card {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }}
            .metric-label {{
                color: #6c757d;
                font-size: 0.9em;
                margin-bottom: 5px;
            }}
            .metric-value {{
                font-size: 2em;
                font-weight: bold;
                color: #212529;
            }}
            .metric-sub {{
                color: #6c757d;
                font-size: 0.85em;
                margin-top: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #dee2e6;
            }}
            th {{
                background-color: #f8f9fa;
                font-weight: 600;
            }}
            .table tbody tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
            .table th + th,
            .table td + td {{
                text-align: right;
            }}
            tr:hover {{
                background-color: #f8f9fa;
            }}
            .success {{
                background-color: #d4edda;
                border-left: 4px solid #28a745;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .warning {{
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .chart-container {{
                margin: 30px 0;
                text-align: center;
            }}
            .chart-container img {{
                max-width: 100%;
                height: auto;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            h2 {{
                color: #667eea;
                border-bottom: 2px solid #667eea;
                padding-bottom: 10px;
                margin-top: 30px;
            }}
            .two-column {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                color: #6c757d;
                font-size: 0.9em;
                margin-top: 40px;
                border-top: 1px solid #dee2e6;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Wirtschaftlichkeitsvergleich</h1>
            <h2>{name_a} vs. {name_b}</h2>
            <div class="date">Erstellt am: {datetime.now().strftime("%d.%m.%Y %H:%M Uhr")}</div>
        </div>

        <div class="section">
            <h2>🎯 Kernergebnisse</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Kosten {name_a}</div>
                    <div class="metric-value">{fmt_eur(result_a['ges_kosten'])} €</div>
                    <div class="metric-sub">Auslastung: {ausl_a*100:.1f}% ({result_a['ges_stunden']:.0f}h/{res_a['stunden_effektiv']:.0f}h)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Kosten {name_b}</div>
                    <div class="metric-value">{fmt_eur(result_b['ges_kosten'])} €</div>
                    <div class="metric-sub">Auslastung: {ausl_b*100:.1f}% ({result_b['ges_stunden']:.0f}h/{res_b['stunden_effektiv']:.0f}h)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Ersparnis pro Jahr</div>
                    <div class="metric-value">{fmt_eur(ersparnis)} €</div>
                    <div class="metric-sub">{ersparnis_proz:.1f}% Einsparung</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Amortisation</div>
                    <div class="metric-value">{amort_text} Jahre</div>
                    <div class="metric-sub">Mehrinvest: {fmt_eur(mehrinvest)} €</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">NPV (B statt A)</div>
                    <div class="metric-value">{npv_text}</div>
                    <div class="metric-sub">bei i={zins_satz*100:.1f}%, n={n}</div>
                </div>
            </div>

            <div class="{'success' if ersparnis > 0 else 'warning'}">
                <strong>💡 Empfehlung:</strong> {empfehlung_text.replace('**', '')}
            </div>
        </div>

        <div class="section">
            <h2>💰 Maschinenstundensatz (MSS)</h2>
            <div class="two-column">
                <div>
                    <h3>{name_a}</h3>
                    {data_mss_a_html.to_html(index=False, classes='table')}
                </div>
                <div>
                    <h3>{name_b}</h3>
                    {data_mss_b_html.to_html(index=False, classes='table')}
                </div>
            </div>
        </div>

        <div class="section">
            <h2>📊 Kostenstruktur</h2>
            <div class="chart-container">
                <img src="{kostenstruktur_img}" alt="Kostenstruktur">
            </div>
        </div>

        <div class="section">
            <h2>📈 Break-Even-Analyse</h2>
            <div class="chart-container">
                <img src="{breakeven_img}" alt="Break-Even-Analyse">
            </div>
        </div>

        <div class="section">
            <h2>🔍 Stückkostenvergleich</h2>
            {df_vergleich.to_html(index=False, classes='table')}
        </div>

        <div class="section">
            <h2>📋 Produktionsprogramm</h2>
            {df_serien.to_html(index=False, classes='table')}
        </div>

        <div class="section">
            <h2>💶 Fixkostenaufschlüsselung</h2>
            <div class="two-column">
                <div>
                    <h3>{name_a}</h3>
                    {fix_df_a_html.to_html(index=False, classes='table')}
                </div>
                <div>
                    <h3>{name_b}</h3>
                    {fix_df_b_html.to_html(index=False, classes='table')}
                </div>
            </div>
        </div>

        <div class="section">
            <h2>⚙️ Eingabeparameter</h2>
            <table>
                <tr><th>Parameter</th><th>Wert</th></tr>
                <tr><td>Anschaffungskosten A</td><td>{ak_a:,.0f} €</td></tr>
                <tr><td>Anschaffungskosten B</td><td>{ak_b:,.0f} €</td></tr>
                <tr><td>Restwert A</td><td>{restwert_a:,.0f} €</td></tr>
                <tr><td>Restwert B</td><td>{restwert_b:,.0f} €</td></tr>
                <tr><td>Nutzungsdauer</td><td>{n} Jahre</td></tr>
                <tr><td>Kalkulatorischer Zinssatz</td><td>{zins_satz*100:.1f}%</td></tr>
                <tr><td>Lohnsatz</td><td>{lohn_satz:.2f} €/h</td></tr>
                <tr><td>Strompreis</td><td>{strom_preis:.2f} €/kWh</td></tr>
                <tr><td>Raumkosten</td><td>{raum_preis:.2f} €/m²/Monat</td></tr>
            </table>
        </div>

        <div class="footer">
            <p><strong>Hinweis:</strong> Diese Berechnung basiert auf den angegebenen Parametern und dient als Entscheidungshilfe.
            Bitte prüfen Sie weitere Faktoren wie Technologierisiko, Flexibilität, Lieferzeiten und strategische Aspekte.</p>
            <p>Erstellt mit Streamlit Wirtschaftlichkeitsvergleich Tool</p>
        </div>
    </body>
    </html>
    """
    return html_content

# =========================
# EXPORT
# =========================
st.divider()
st.header("💾 Export")
col_export1, col_export2 = st.columns(2)

with col_export1:
    if st.button("📄 HTML-Bericht generieren", use_container_width=True):
        html_report = generate_html_report()
        st.download_button(
            label="⬇️ HTML-Bericht herunterladen",
            data=html_report,
            file_name=f"Wirtschaftlichkeitsvergleich_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
            mime="text/html",
            use_container_width=True
        )
        st.success("✅ HTML-Bericht erfolgreich generiert!")

with col_export2:
    if st.button("📊 Excel-Export (Rohdaten)", use_container_width=True):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            overview_data = pd.DataFrame({
                'Kennzahl': ['Gesamtkosten', 'Gesamtstunden', 'Gesamtstückzahl', 'Auslastung', 'MSS Gesamt', 'Mehrinvest', 'Amortisation', 'NPV (B statt A)'],
                name_a: [
                    f"{result_a['ges_kosten']:.2f} €",
                    f"{result_a['ges_stunden']:.1f} h",
                    f"{result_a['ges_stueck']} Stk",
                    f"{ausl_a*100:.1f}%",
                    f"{mss_gesamt_a:.2f} €/h",
                    "",
                    "",
                    ""
                ],
                name_b: [
                    f"{result_b['ges_kosten']:.2f} €",
                    f"{result_b['ges_stunden']:.1f} h",
                    f"{result_b['ges_stueck']} Stk",
                    f"{ausl_b*100:.1f}%",
                    f"{mss_gesamt_b:.2f} €/h",
                    f"{mehrinvest:.2f} €",
                    f"{amortisation:.2f} Jahre" if amortisation is not None else "N/A",
                    f"{npv_b_vs_a:.2f} €" if npv_b_vs_a is not None else "N/A"
                ]
            })
            overview_data.to_excel(writer, sheet_name='Übersicht', index=False)
            result_a['details'].to_excel(writer, sheet_name='Details_A', index=False)
            result_b['details'].to_excel(writer, sheet_name='Details_B', index=False)
            df_serien.to_excel(writer, sheet_name='Produktionsprogramm', index=False)
            fix_df_a.to_excel(writer, sheet_name='Fixkosten_A', index=False)
            fix_df_b.to_excel(writer, sheet_name='Fixkosten_B', index=False)

        output.seek(0)
        st.download_button(
            label="⬇️ Excel-Datei herunterladen",
            data=output,
            file_name=f"Wirtschaftlichkeitsvergleich_Daten_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        st.success("✅ Excel-Export vorbereitet!")

# --- FOOTER ---
st.divider()
st.caption("""
Hinweis: Diese Berechnung basiert auf den angegebenen Parametern und dient als Entscheidungshilfe.
Bitte prüfen Sie weitere Faktoren wie Technologierisiko, Flexibilität, Lieferzeiten und strategische Aspekte.
""")
