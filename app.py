import streamlit as st
import requests
import json

# Configurazione della pagina Streamlit
st.set_page_config(page_title="AI Vehicle Comparator", page_icon="🚗", layout="wide")

st.title("🚗 AI Vehicle Advisor & Comparator")
st.write("Analizza un singolo annuncio o confronta due annunci diversi per scoprire qual è il miglior affare.")

# Scelta della modalità d'uso
modalita = st.radio("Cosa vuoi fare?", ["Analizza un singolo annuncio", "Confronta due annunci diversi"], horizontal=True)

# Recupero della chiave API dai Secrets di Streamlit
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

def chiama_gemini(prompt_testo):
    """Funzione di supporto per interrogare le API di Google Gemini"""
    if not GEMINI_API_KEY:
        return {"errore": "Chiave API non configurata nei Secrets di Streamlit."}
        
    url = f"https://googleapis.com{GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt_testo}]}]}
    
    try:
        response = requests.post(url, json=payload)
        testo_risposta = response.json()['candidates']['content']['parts']['text']
        # Pulizia dell'output per garantire che sia solo un JSON puro
        testo_risposta = testo_risposta.replace("```json", "").replace("```", "").strip()
        return json.loads(testo_risposta)
    except Exception as e:
        return {"errore": f"Impossibile analizzare i dati. Riprova. Dettaglio: {str(e)}"}

# ----------------- MODALITÀ 1: SINGOLO ANNUNCIO -----------------
if modalita == "Analizza un singolo annuncio":
    annuncio_testo = st.text_area("Incolla qui il testo dell'annuncio:", height=200, 
                                  placeholder="Es: Vendo Fiat Panda 2018 con 75.000km a 7200€...")
    
    if st.button("Analizza Annuncio 🚀"):
        if not annuncio_testo.strip():
            st.warning("Inserisci il testo di un annuncio.")
        else:
            with st.spinner("L'intelligenza artificiale sta analizzando il mezzo..."):
                prompt = f"""
                Analizza questo annuncio di auto/moto e rispondi ESCLUSIVAMENTE in un formato JSON valido.
                Usa esattamente questa struttura:
                {{
                  "valutazione": "OTTIMO" o "ONESTO" o "CARO",
                  "motivazione_prezzo": "spiegazione del perché",
                  "criticita": ["danno o difetto 1", "difetto 2"],
                  "punti_forza": ["punto 1", "punto 2"]
                }}
                Ecco l'annuncio:
                {annuncio_testo}
                """
                risultato = chiama_gemini(prompt)
                
                if "errore" in risultato:
                    st.error(risultato["errore"])
                else:
                    st.success("Analisi Completata!")
                    val = risultato["valutazione"]
                    if val == "OTTIMO": st.metric("Verdetto Prezzo", "🟢 OTTIMO AFFARE")
                    elif val == "ONESTO": st.metric("Verdetto Prezzo", "🟡 PREZZO ONESTO")
                    else: st.metric("Verdetto Prezzo", "🔴 SOVRAPPREZZO")
                    
                    st.write(f"**Motivazione:** {risultato['motivazione_prezzo']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("⚠️ Criticità / Danni Rilevati")
                        for c in risultato.get("criticita", []): st.write(f"- {c}")
                    with col2:
                        st.subheader("✅ Punti di Forza")
                        for p in risultato.get("punti_forza", []): st.write(f"- {p}")

# ----------------- MODALITÀ 2: CONFRONTO ANNUNCI -----------------
else:
    st.write("Inserisci i testi dei due annunci da confrontare (es. uno da Subito e uno da Facebook Marketplace).")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🛒 Annuncio A (es. Subito)")
        annuncio_a = st.text_area("Testo Annuncio A:", height=200, placeholder="Incolla qui il primo annuncio...")
    with col_b:
        st.subheader("🛒 Annuncio B (es. Facebook)")
        annuncio_b = st.text_area("Testo Annuncio B:", height=200, placeholder="Incolla qui il secondo annuncio...")
        
    if st.button("Confronta i due Mezzi ⚔️"):
        if not annuncio_a.strip() or not annuncio_b.strip():
            st.warning("Per favore, inserisci entrambi gli annunci per avviare il confronto.")
        else:
            with st.spinner("L'intelligenza artificiale sta analizzando e confrontando i due annunci..."):
                prompt_comparazione = f"""
                Confronta questi due annunci di veicoli (Auto o Moto) e determina quale rappresenta la scelta migliore (miglior rapporto qualità/prezzo, chilometraggio, stato del mezzo e anno).
                Rispondi ESCLUSIVAMENTE in formato JSON valido, senza testo prima o dopo. Usa esattamente questa struttura:
                {{
                  "vincitore": "ANNUNCIO A" o "ANNUNCIO B" o "PAREGGIO",
                  "motivazione_vincitore": "Spiegazione dettagliata del perché questo mezzo è preferibile rispetto all'altro.",
                  "confronto_prezzo": "Analisi della differenza di prezzo in rapporto a quello che offrono.",
                  "tabella_comparativa": {{
                    "prezzo_a": "prezzo A", "prezzo_b": "prezzo B",
                    "anno_a": "anno A", "anno_b": "anno B",
                    "km_a": "km A", "km_b": "km B"
                  }},
                  "pro_contro_a": {{ "pro": ["pro 1"], "contro": ["contro 1"] }},
                  "pro_contro_b": {{ "pro": ["pro 1"], "contro": ["contro 1"] }}
                }}
                
                Ecco l'Annuncio A:
                {annuncio_a}
                
                Ecco l'Annuncio B:
                {annuncio_b}
                """
                
                risultato = chiama_gemini(prompt_comparazione)
                
                if "errore" in risultato:
                    st.error(risultato["errore"])
                else:
                    st.success("Confronto Completata!")
                    
                    vincitore = risultato["vincitore"]
                    if vincitore == "ANNUNCIO A":
                        st.info("🏆 **Il verdetto dell'AI:** L'Annuncio A è la scelta migliore!")
                    elif vincitore == "ANNUNCIO B":
                        st.info("🏆 **Il verdetto dell'AI:** L'Annuncio B è la scelta migliore!")
                    else:
                        st.info("🤝 **Il verdetto dell'AI:** Sostanziale pareggio. Entrambe le opzioni sono valide.")
                        
                    st.write(f"**Analisi della scelta:** {risultato['motivazione_vincitore']}")
                    st.write(f"**Rapporto dei Prezzi:** {risultato['confronto_prezzo']}")
                    
                    st.subheader("📊 Sintesi dei Dati Principali")
                    tab = risultato["tabella_comparativa"]
                    st.table({
                        "Caratteristica": ["Prezzo", "Anno Immatricolazione", "Chilometri"],
                        "Annuncio A": [tab.get("prezzo_a"), tab.get("anno_a"), tab.get("km_a")],
                        "Annuncio B": [tab.get("prezzo_b"), tab.get("anno_b"), tab.get("km_b")]
                    })
                    
                    st.subheader("🔍 Analisi di Dettaglio")
                    col_res_a, col_res_b = st.columns(2)
                    
                    with col_res_a:
                        st.markdown("### 🛒 Focus Annuncio A")
                        st.markdown("**Vantaggi:**")
                        for pro in risultato["pro_contro_a"]["pro"]: st.write(f"✅ {pro}")
                        st.markdown("**Svantaggi / Danni:**")
                        for contro in risultato["pro_contro_a"]["contro"]: st.write(f"❌ {contro}")
                        
                    with col_res_b:
                        st.markdown("### 🛒 Focus Annuncio B")
                        st.markdown("**Vantaggi:**")
                        for pro in risultato["pro_contro_b"]["pro"]: st.write(f"✅ {pro}")
                        st.markdown("**Svantaggi / Danni:**")
                        for contro in risultato["pro_contro_b"]["contro"]: st.write(f"❌ {contro}")
