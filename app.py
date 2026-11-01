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
APIFY_API_TOKEN = st.secrets.get("APIFY_API_TOKEN", "")

def scrape_con_apify(url):
    """Chiama l'attore di Apify usando URL statici e separati per evitare fusioni di stringhe"""
    
    if "subito.it" in url:
        # URL statico definitivo per Subito.it
        api_url = f"https://apify.com{APIFY_API_TOKEN}"
        run_input = {"url": url, "maxItems": 1}
        
    elif "://facebook.com" in url:
        # URL statico definitivo per Facebook Marketplace
        api_url = f"https://apify.com{APIFY_API_TOKEN}"
        run_input = {"searchUrls": [url], "maxResults": 1}
        
    else:
        return None, "Sito non supportato. Inserisci un link valido di Subito o Facebook Marketplace."
    
    try:
        # Chiamata HTTP
        response = requests.post(api_url, json=run_input, timeout=150)
        
        if response.status_code != 200 and response.status_code != 201:
            return None, f"Errore Apify (Stato {response.status_code}): {response.text}"
            
        dati_scaricati = response.json()
        
        if not dati_scaricati or len(dati_scaricati) == 0:
            return None, "L'annuncio non ha restituito dati. Controlla il link."
            
        # Estraiamo il primo annuncio della lista
        item = dati_scaricati[0] if isinstance(dati_scaricati, list) else dati_scaricati

        # Estrazione dati specifica per Subito
        features = item.get("features", {})
        price_info = features.get("price", {})
        prezzo = price_info.get("value") or item.get("price") or "Non specificato"
        
        output = {
            "titolo": item.get("title") or item.get("name") or "Veicolo",
            "descrizione": item.get("description") or "Nessuna descrizione.",
            "prezzo": f"{prezzo} €" if isinstance(prezzo, (int, float)) else prezzo,
            "immagini": item.get("images") or item.get("photos") or []
        }
        return output, None
        
    except requests.exceptions.Timeout:
        return None, "⏱️ Il server di scraping ha impiegato troppo tempo. Riprova tra un minuto."
    except Exception as e:
        return None, f"Errore durante l'elaborazione dei dati: {str(e)}"

def analizza_veicolo_completo(dati_veicolo):
    """Invia il testo e i link delle immagini dell'annuncio a Gemini"""
    url_gemini = f"https://googleapis.com{GEMINI_API_KEY}"
    
    link_immagini = []
    for img in dati_veicolo["immagini"][:5]:
        if isinstance(img, dict):
            link_immagini.append(img.get("url", ""))
        else:
            link_immagini.append(str(img))
            
    immagini_stringa = ", ".join(link_immagini)
    
    prompt = f"""
    Analizza questo veicolo. Ti fornisco i dati testuali dell'annuncio e i link delle immagini reali caricate dal venditore.
    
    Titolo: {dati_veicolo['titolo']}
    Prezzo: {dati_veicolo['prezzo']}
    Descrizione: {dati_veicolo['descrizione']}
    Link Immagini da ispezionare: [{immagini_stringa}]
    
    Rispondi ESCLUSIVAMENTE in un formato JSON valido. Non aggiungere testo prima o dopo il JSON. Usa esattamente questa struttura:
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
                
                if dati_veicolo["immagini"]:
                    prima_img = dati_veicolo["immagini"][0]
                    url_img = prima_img.get("url") if isinstance(prima_img, dict) else prima_img
                    if url_img:
                        st.image(url_img, width=400, caption="Foto principale dell'annuncio")
                
                with st.spinner("Gemini sta analizzando testo e immagini alla ricerca di anomalie..."):
                    risultato = analizza_veicolo_completo(dati_veicolo)
                    
                    if "errore" in risultato:
                        st.error(risultato["errore"])
                    else:
                        val = risultato.get("valutazione", "ONESTO")
                        if val == "OTTIMO": st.metric("Verdetto Convenienza", "🟢 OTTIMO AFFARE")
                        elif val == "ONESTO": st.metric("Verdetto Convenienza", "🟡 PREZZO ONESTO")
                        else: st.metric("Verdetto Convenienza", "🔴 SOVRAPPREZZO")
                        
                        st.write(f"**Analisi:** {risultato.get('motivazione', '')}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("⚠️ Criticità e Danni Individuati")
                            for c in risultato.get("criticita_rilevate", []): st.error(f"• {c}")
                        with col2:
                            st.subheader("✅ Punti di Forza del mezzo")
                            for p in resultado.get("punti_forza", []): st.success(f"• {p}")
