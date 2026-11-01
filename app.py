import streamlit as st
import requests
import json

st.set_page_config(page_title="AI Auto Advisor Pro", page_icon="🏎️", layout="wide")

st.title("🏎️ AI Vehicle Advisor - Analisi da Link Diretto")
st.write("Incolla il link dell'annuncio e le tue chiavi di accesso per avviare il controllo automatico.")

# 1. Pannello di configurazione chiavi direttamente a schermo per evitare bug di cache
st.sidebar.header("🔑 Configurazione Chiavi")
apify_token_input = st.sidebar.text_input("Inserisci il tuo Token Apify:", type="password", 
                                         placeholder="apify_api_...")
gemini_key_input = st.sidebar.text_input("Inserisci la tua API Key Gemini:", type="password", 
                                         placeholder="AIzaSy...")

# Input del link dell'annuncio
url_annuncio = st.text_input("Incolla il link dell'annuncio (Subito.it o Facebook Marketplace):")

def scrape_con_apify(url, token):
    """Chiama l'attore di Apify isolando l'URL da qualsiasi manipolazione esterna"""
    # Puliamo il token da eventuali spazi o caratteri errati, mantenendo le maiuscole corrette
    token_pulito = str(token).strip()
    
    if "subito.it" in url:
        actor_id = "frances_api~subito-motori-scraper"
        run_input = {"url": url, "maxItems": 1}
    elif "://facebook.com" in url:
        actor_id = "apify~facebook-marketplace-scraper"
        run_input = {"searchUrls": [url], "maxResults": 1}
    else:
        return None, "Sito non supportato. Inserisci un link valido di Subito o Facebook Marketplace."

    # Usiamo una stringa standard senza alcuna variabile extra per l'host
    api_url = f"https://apify.com{actor_id}/run-sync-get-dataset-items?token={token_pulito}"
    
    try:
        response = requests.post(api_url, json=run_input, timeout=120)
        
        if response.status_code != 200 and response.status_code != 201:
            return None, f"Errore Apify (Stato {response.status_code}): {response.text}"
            
        dati_scaricati = response.json()
        if not dati_scaricati:
            return None, "L'annuncio non ha restituito dati. Controlla il link."
            
        item = dati_scaricati[0] if isinstance(dati_scaricati, list) and len(dati_scaricati) > 0 else dati_scaricati

        features = item.get("features", {})
        price_info = features.get("price", {})
        prezzo = price_info.get("value") or item.get("price") or "Non specificato"
        
        raw_images = item.get("images") or item.get("photos") or []
        lista_immagini = []
        for img in raw_images:
            if isinstance(img, dict):
                lista_immagini.append(img.get("url", ""))
            else:
                lista_immagini.append(str(img))
        
        output = {
            "titolo": item.get("title") or item.get("name") or "Veicolo",
            "descrizione": item.get("description") or "Nessuna descrizione disponibile.",
            "prezzo": f"{prezzo} €" if isinstance(prezzo, (int, float)) else f"{prezzo}",
            "immagini": [u for u in lista_immagini if u]
        }
        return output, None
        
    except Exception as e:
        return None, f"Errore durante la connessione ai server di scraping: {str(e)}"

def analizza_veicolo_completo(dati_veicolo, gemini_key):
    """Invia i dati strutturati a Gemini"""
    url_gemini = f"https://googleapis.com{gemini_key}"
    immagini_stringa = ", ".join(dati_veicolo["immagini"][:5])
    
    prompt = f"""
    Analizza questo veicolo usandone i dati testuali e le immagini dell'annuncio.
    Titolo: {dati_veicolo['titolo']}
    Prezzo: {dati_veicolo['prezzo']}
    Descrizione: {dati_veicolo['descrizione']}
    Link Immagini: [{immagini_stringa}]
    
    Rispondi ESCLUSIVAMENTE in un formato JSON valido con questa struttura:
    {{
      "valutazione": "OTTIMO" o "ONESTO" o "CARO",
      "motivazione": "Spiegazione sintetica sul rapporto qualità/prezzo",
      "criticita_rilevate": ["Lista di difetti o problemi"],
      "punti_forza": ["Pregi"]
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

# Bottone di esecuzione
if st.button("Analizza Annuncio dal Link 🚀"):
    if not url_annuncio:
        st.warning("Per favore, inserisci un link valido.")
    elif not apify_token_input:
        st.error("Inserisci il tuo Token Apify nella barra laterale sinistra.")
    elif not gemini_key_input:
        st.error("Inserisci la tua API Key Gemini nella barra laterale sinistra.")
    else:
        with st.spinner("Estrazione dati in corso dal link fornito..."):
            dati_veicolo, errore = scrape_con_apify(url_annuncio, apify_token_input)
            
            if errore:
                st.error(errore)
            else:
                st.success(f"Dati di '{dati_veicolo['titolo']}' recuperati correttamente!")
                
                if dati_veicolo["immagini"]:
                    st.image(dati_veicolo["immagini"][0], width=400, caption="Anteprima Veicolo")
                
                with st.spinner("Analisi intelligenza artificiale in corso..."):
                    risultato = analizza_veicolo_completo(dati_veicolo, gemini_key_input)
                    
                    if "errore" in risultato:
                        st.error(risultato["errore"])
                    else:
                        val = risultato.get("valutazione", "ONESTO")
                        if val == "OTTIMO": st.metric("Verdetto", "🟢 OTTIMO AFFARE")
                        elif val == "ONESTO": st.metric("Verdetto", "🟡 PREZZO ONESTO")
                        else: st.metric("Verdetto", "🔴 SOVRAPPREZZO")
                        
                        st.write(f"**Analisi:** {risultato.get('motivazione', '')}")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("⚠️ Difetti/Criticità")
                            for c in risultato.get("criticita_rilevate", []): st.error(f"• {c}")
                        with col2:
                            st.subheader("✅ Pregi")
                            for p in risultato.get("punti_forza", []): st.success(f"• {p}")
