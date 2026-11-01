import streamlit as st
import requests
import json

st.set_page_config(page_title="AI Auto Advisor Pro", page_icon="🏎️", layout="wide")

st.title("🏎️ AI Vehicle Advisor - Analisi da Link Diretto")
st.write("Incolla semplicemente il link dell'annuncio di Subito.it o Facebook Marketplace.")

# Input del link
url_annuncio = st.text_input("Incolla il link dell'annuncio qui:")

# Chiavi segrete prese dai Secrets di Streamlit
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
APIFY_API_TOKEN = st.secrets.get("APIFY_API_TOKEN", "") # Prendi questo token gratis da Apify

def scrape_con_apify(url):
    """Chiama l'attore di Apify per bypassare i blocchi e raccogliere dati ed immagini"""
    # Identifichiamo la piattaforma dal link
    if "subito.it" in url:
        # L'ID dell'attore è frances_api/subito-motori-scraper
        # Nelle API di Apify lo slash va sostituito con la tilde ~
        actor_id = "frances_api~subito-motori-scraper"
    elif "://facebook.com" in url:
        # ID ufficiale: apify/facebook-marketplace-scraper
        actor_id = "apify~facebook-marketplace-scraper"
    else:
        return None, "Sito non supportato. Inserisci un link valido di Subito o Facebook Marketplace."

    # URL FISSO E CORRETTO secondo le specifiche POST v2 di Apify
    api_url = f"https://api.apify.com/v2/actors/{actor_id}/run-sync-get-dataset-items?token={APIFY_API_TOKEN}"
    
    # Input richiesto dagli attori Apify
    run_input = {"searchUrls": [url]} if "facebook" in actor_id else {"url": url}
    
    try:
        # Inviamo la richiesta POST ad Apify
        response = requests.post(api_url, json=run_input, timeout=60)
        
        if response.status_code != 200:
            return None, f"Errore Apify (Stato {response.status_code}): {response.text}"
            
        dati_scaricati = response.json()
        
        if not dati_scaricati:
            return None, "L'annuncio non ha restituito dati. Controlla il link o i tuoi crediti su Apify."
            
        # Gli attori restituiscono sempre una lista (dataset items)
        # Prendiamo il primo elemento che corrisponde all'annuncio scansionato
        item = dati_scaricati[0] if isinstance(dati_scaricati, list) else dati_scaricati

        # Estrazione e normalizzazione pulita delle informazioni
        output = {
            "titolo": item.get("title") or item.get("name") or "Veicolo non specificato",
            "descrizione": item.get("description") or "Nessuna descrizione presente nell'annuncio.",
            "prezzo": item.get("price") or "Non specificato",
            "immagini": item.get("images") or item.get("photos") or []
        }
        return output, None
        
    except Exception as e:
        return None, f"Errore durante lo scraping: {str(e)}"

def analizza_veicolo_completo(dati_veicolo):
    """Invia il testo e i link delle immagini dell'annuncio a Gemini"""
    url_gemini = f"https://googleapis.com{GEMINI_API_KEY}"
    
    # Costruiamo il prompt includendo i link delle immagini recuperate dallo scraper
    immagini_stringa = ", ".join([img.get("url", img) if isinstance(img, dict) else img for img in dati_veicolo["immagini"][:5]])
    
    prompt = f"""
    Analizza questo veicolo. Ti fornisco i dati testuali dell'annuncio e i link delle immagini reali caricate dal venditore.
    
    Titolo: {dati_veicolo['titolo']}
    Prezzo: {dati_veicolo['prezzo']}
    Descrizione: {dati_veicolo['descrizione']}
    Link Immagini da ispezionare: [{immagini_stringa}]
    
    Rispondi ESCLUSIVAMENTE in formato JSON con questa struttura:
    {{
      "valutazione": "OTTIMO" o "ONESTO" o "CARO",
      "motivazione": "Spiegazione basata sul rapporto qualità/prezzo",
      "criticita_rilevate": ["Lista di danni, graffi o problemi meccanici citati o visibili nelle immagini"],
      "punti_forza": ["Pregi rilevati"]
    }}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url_gemini, json=payload)
        testo_risposta = response.json()['candidates']['content']['parts']['text']
        testo_risposta = testo_risposta.replace("```json", "").replace("```", "").strip()
        return json.loads(testo_risposta)
    except Exception as e:
        return {"errore": f"Errore nell'analisi AI: {str(e)}"}

# Bottone di avvio
if st.button("Analizza Annuncio dal Link 🚀"):
    if not url_annuncio:
        st.warning("Per favore, inserisci un link.")
    elif not APIFY_API_TOKEN:
        st.error("Configura la chiave APIFY_API_TOKEN nei tuoi Secrets di Streamlit.")
    else:
        with st.spinner("Bypassando le protezioni del sito ed estraendo i dati..."):
            dati_veicolo, errore = scrape_con_apify(url_annuncio)
            
            if errore:
                st.error(errore)
            else:
                st.success(f"Dati di '{dati_veicolo['titolo']}' estratti con successo! Avvio analisi AI...")
                
                # Mostriamo un'anteprima delle immagini estratte direttamente dal link
                if dati_veicolo["immagini"]:
                    st.image(dati_veicolo["immagini"][0], width=300, caption="Foto principale estratta dall'annuncio")
                
                with st.spinner("Gemini sta analizzando testo e immagini alla ricerca di anomalie..."):
                    risultato = analizza_veicolo_completo(dati_veicolo)
                    
                    if "errore" in risultato:
                        st.error(risultato["errore"])
                    else:
                        # Mostriamo i risultati
                        val = risultato["valutazione"]
                        if val == "OTTIMO": st.metric("Verdetto Convenienza", "🟢 OTTIMO AFFARE")
                        elif val == "ONESTO": st.metric("Verdetto Convenienza", "🟡 PREZZO ONESTO")
                        else: st.metric("Verdetto Convenienza", "🔴 SOVRAPPREZZO")
                        
                        st.write(f"**Analisi:** {risultato['motivazione']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("⚠️ Criticità e Danni Individuati")
                            for c in risultato.get("criticita_rilevate", []): st.error(f"• {c}")
                        with col2:
                            st.subheader("✅ Punti di Forza del mezzo")
                            for p in risultato.get("punti_forza", []): st.success(f"• {p}")
