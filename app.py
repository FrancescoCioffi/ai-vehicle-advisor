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
APIFY_API_TOKEN = st.secrets.get("APIFY_API_TOKEN", "").strip() # Rimuove eventuali spazi bianchi accidentali

def scrape_con_apify(url):
    """Chiama l'attore di Apify usando URL statici puliti"""
    
    if "subito.it" in url:
        api_url = f"https://apify.com{APIFY_API_TOKEN}"
        run_input = {"url": url, "maxItems": 1}
    elif "://facebook.com" in url:
        api_url = f"https://apify.com{APIFY_API_TOKEN}"
        run_input = {"searchUrls": [url], "maxResults": 1}
    else:
        return None, "Sito non supportato. Inserisci un link valido di Subito o Facebook Marketplace."
    
    try:
        response = requests.post(api_url, json=run_input, timeout=150)
        
        if response.status_code != 200 and response.status_code != 201:
            return None, f"Errore Apify (Stato {response.status_code}): {response.text}"
            
        dati_scaricati = response.json()
        
        if not dati_scaricati:
            return None, "L'annuncio non ha restituito dati. Controlla che il link sia ancora attivo."
            
        # Gestiamo in modo sicuro se la risposta è una lista o un singolo elemento
        if isinstance(dati_scaricati, list):
            if len(dati_scaricati) == 0:
                return None, "Nessun dato trovato nel dataset di Apify."
            item = dati_scaricati[0]
        else:
            item = dati_scaricati

        features = item.get("features", {})
        price_info = features.get("price", {})
        prezzo = price_info.get("value") or item.get("price") or "Non specificato"
        
        # Recupero sicuro delle immagini sia da formato lista che dizionario
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
            "immagini": [url for url in lista_immagini if url]
        }
        return output, None
        
    except requests.exceptions.Timeout:
        return None, "⏱️ Il server di scraping ha impiegato troppo tempo per aggirare i blocchi. Riprova."
    except Exception as e:
        return None, f"Errore durante l'elaborazione dei dati: {str(e)}"

def analizza_veicolo_completo(dati_veicolo):
    """Invia il testo e le immagini a Gemini 1.5 Flash"""
    url_gemini = f"https://googleapis.com{GEMINI_API_KEY}"
    
    immagini_stringa = ", ".join(dati_veicolo["immagini"][:5])
    
    prompt = f"""
    Analizza questo veicolo usandone i dati testuali e le immagini dell'annuncio.
    
    Titolo: {dati_veicolo['titolo']}
    Prezzo: {dati_veicolo['prezzo']}
    Descrizione: {dati_veicolo['descrizione']}
    Link Immagini da ispezionare: [{immagini_stringa}]
    
    Rispondi ESCLUSIVAMENTE in un formato JSON valido. Non aggiungere testo extra o markdown. Usa questa struttura:
    {{
      "valutazione": "OTTIMO" o "ONESTO" o "CARO",
      "motivazione": "Spiegazione sintetica sul rapporto qualità/prezzo",
      "criticita_rilevate": ["Lista di difetti, graffi o problemi meccanici evidenti"],
      "punti_forza": ["Pregi del veicolo"]
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
    elif not APIFY_API_TOKEN or "apify_api" not in APIFY_API_TOKEN:
        st.error("Rilevato token Apify non valido nei Secrets. Assicurati che contenga solo la chiave alfanumerica.")
    else:
        with st.spinner("Bypassando le protezioni ed estraendo i dati dal link..."):
            dati_veicolo, errore = scrape_con_apify(url_annuncio)
            
            if errore:
                st.error(errore)
            else:
                st.success(f"Dati di '{dati_veicolo['titolo']}' estratti con successo!")
                
                # Mostriamo l'anteprima della prima immagine se presente
                if dati_veicolo["immagini"]:
                    st.image(dati_veicolo["immagini"][0], width=400, caption="Immagine dell'annuncio")
                
                with st.spinner("L'intelligenza artificiale sta analizzando il veicolo..."):
                    risultato = analizza_veicolo_completo(dati_veicolo)
                    
                    if "errore" in risultato:
                        st.error(risultato["errore"])
                    else:
                        val = risultato.get("valutazione", "ONESTO")
                        if val == "OTTIMO": st.metric("Verdetto Convenienza", "🟢 OTTIMO AFFARE")
                        elif val == "ONESTO": st.metric("Verdetto Convenienza", "🟡 PREZZO ONESTO")
                        else: st.metric("Verdetto Convenienza", "🔴 SOVRAPPREZZO")
                        
                        st.write(f"**Analisi dell'esperto:** {risultato.get('motivazione', '')}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("⚠️ Criticità e Danni Individuati")
                            for c in risultato.get("criticita_rilevate", []): st.error(f"• {c}")
                        with col2:
                            st.subheader("✅ Punti di Forza")
                            for p in risultato.get("punti_forza", []): st.success(f"• {p}")
