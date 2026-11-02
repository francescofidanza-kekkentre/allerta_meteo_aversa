from datetime import datetime
import json
import re
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
import requests

def get_campania_alert_status():
    """Rileva l'allerta meteo leggendo direttamente la dashboard del Centro Funzionale Multirischi Campania."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    status = "VERDE"
    raw_message = (
        "Nessuna allerta meteo in vigore. Condizioni meteorologiche nella norma"
        " per la Zona 1 (Piana Campana)."
    )

    # Interroghiamo direttamente la dashboard ufficiale del Centro Funzionale
    url = "https://centrofunzionale.regione.campania.it/"

    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Estraiamo tutto il testo della pagina mettendolo in maiuscolo per facilitare la ricerca
            text = soup.get_text(separator=" ", strip=True).upper()
            
            # Cerchiamo i blocchi "Stato di Allerta ATTUALE" e "PREVISTO" tramite regex
            match_attuale = re.search(r"STATO DI ALLERTA ATTUALE.*?LIVELLO DI ALLERTA.*?(ROSSA|ARANCIONE|GIALLA|VERDE)", text)
            match_previsto = re.search(r"STATO DI ALLERTA PREVISTO.*?LIVELLO DI ALLERTA.*?(ROSSA|ARANCIONE|GIALLA|VERDE)", text)
            
            # Fallback nel caso in cui cambino l'impaginazione ma lascino la dicitura generica
            match_generico = re.search(r"LIVELLO DI ALLERTA.*?IDROGEOLOGICA.*?(ROSSA|ARANCIONE|GIALLA|VERDE)", text)
            
            colori_trovati = []
            
            if match_attuale:
                colori_trovati.append(match_attuale.group(1))
                print(f"  🔍 Stato ATTUALE letto dalla dashboard: {match_attuale.group(1)}")
                
            if match_previsto:
                colori_trovati.append(match_previsto.group(1))
                print(f"  🔍 Stato PREVISTO letto dalla dashboard: {match_previsto.group(1)}")
                
            if not colori_trovati and match_generico:
                colori_trovati.append(match_generico.group(1))
                print(f"  🔍 Stato GENERICO letto dalla dashboard: {match_generico.group(1)}")

            # Determina la gravità massima tra l'allerta in corso e quella prevista
            if "ROSSA" in colori_trovati:
                status = "ROSSA"
            elif "ARANCIONE" in colori_trovati:
                status = "ARANCIONE"
            elif "GIALLA" in colori_trovati:
                status = "GIALLA"

            # Se trova un'allerta, aggiorna il messaggio da mostrare nell'app
            if status != "VERDE":
                raw_message = (
                    f"Allerta meteo {status} confermata dal Centro Funzionale Multirischi "
                    "della Regione Campania."
                )

    except Exception as e:
        print(f"⚠️ Errore durante la consultazione del Centro Funzionale: {e}")

    return status, raw_message


def check_aversa_school_status():
    """Verifica se è stata emessa un'ordinanza di chiusura scuole ad Aversa."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }

    comune_rss = "https://news.google.com/rss/search?q=site:comune.aversa.ce.it+(scuole+OR+ordinanza)+when:12h&hl=it&gl=IT&ceid=IT:it"
    try:
        resp_comune = requests.get(comune_rss, headers=headers, timeout=10)
        if resp_comune.status_code == 200:
            soup = BeautifulSoup(resp_comune.content, "xml")
            items = soup.find_all("item")
            for item in items[:5]:
                title = item.title.text.lower()
                if ("scuole" in title or "scuola" in title or "ordinanza" in title) and (
                    "chius" in title or "sospens" in title or "stop" in title
                ):
                    return True
    except Exception as e:
        print(f"⚠️ Errore controllo sito Comune: {e}")

    return False


def clean_weather_message(raw_message):
    if not raw_message:
        return "Bollettino meteo in aggiornamento."
    pattern = (
        r"(?i)(i quotidiani locali|i giornali|il comune|ordinanza).*?(chiusura|scuole).*?\."
    )
    cleaned = re.sub(pattern, "", raw_message).strip()
    return cleaned if cleaned else raw_message


def fetch_and_update_alert():
    print("Avvio aggiornamento dati meteo e scuole...")

    status, raw_message = get_campania_alert_status()
    print(f"📡 STATO FINALE ELABORATO: {status}")

    schools_closed = False
    if status != "VERDE":
        schools_closed = check_aversa_school_status()

    message = clean_weather_message(raw_message)

    alert_data = {
        "status": status,
        "message": message,
        "schools_closed": schools_closed,
        "updated_at": datetime.now(ZoneInfo("Europe/Rome")).strftime(
            "%d/%m/%Y, %H:%M:%S"
        ),
    }

    try:
        with open("alert.json", "w", encoding="utf-8") as f:
            json.dump(alert_data, f, ensure_ascii=False, indent=2)
        print("✅ File alert.json generato con successo!")
    except Exception as e:
        print(f"❌ Errore durante il salvataggio di alert.json: {e}")


if __name__ == "__main__":
    fetch_and_update_alert()
