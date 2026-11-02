from datetime import datetime
import json
import re
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
import requests

def get_campania_alert_status():
    """Rileva l'allerta meteo interrogando l'API JSON ufficiale del Centro Funzionale per la Zona 1."""
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

    api_url = "https://centrofunzionale.regione.campania.it/CentroFunzionalePortaleRest/rest/bollettinometeo/findLastBollettinoInserito/"

    try:
        response = requests.get(api_url, headers=headers, timeout=10)

        if response.status_code == 200:
            dati = response.json()
            for area in dati.get("bollettinoMeteoBindList", []):
                if area.get("zona") == 1:
                    descrizione = area.get("livelloDesc", "").upper()
                    
                    if "ROSS" in descrizione:
                        status = "ROSSA"
                    elif "ARANCION" in descrizione:
                        status = "ARANCIONE"
                    elif "GIALL" in descrizione:
                        status = "GIALLA"
                    else:
                        status = "VERDE"
                    
                    if status != "VERDE":
                        raw_message = (
                            f"Allerta meteo {status} confermata dal bollettino del "
                            f"Centro Funzionale Multirischi Campania per la Zona 1."
                        )
                    
                    print(f"✅ Stato allerta Zona 1: {status}")
                    break

    except Exception as e:
        print(f"⚠️ Errore durante l'interrogazione dell'API allerte: {e}")

    return status, raw_message


def get_campania_weather_forecast():
    """Estrae le previsioni meteo dettagliate e le icone per la Zona 1 (versione di debug)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    meteo_url = "https://centrofunzionale.regione.campania.it/CentroFunzionalePortaleRest/rest/bollettinometeo/findLastMeteo/"
    
    forecast_data = {
        "general_desc": "Previsioni meteo in aggiornamento.",
        "today_forecast": "Nessun dettaglio disponibile.",
        "icon_cielo": "",
        "icon_vento": ""
    }

    try:
        response = requests.get(meteo_url, headers=headers, timeout=10)
        print(f"📡 Status Code API Meteo: {response.status_code}")
        
        if response.status_code == 200:
            dati = response.json()
            # Stampa le chiavi principali ricevute per capire la struttura
            print(f"🔑 Chiavi JSON ricevute: {list(dati.keys()) if isinstance(dati, dict)	is not None else 'Non è un dizionario'}")
            
            forecast_data["general_desc"] = dati.get("esameSinottico", "")
            
            giorni = dati.get("previsioniPerGiornoList", [])
            print(f"📅 Giorni trovati nella lista: {len(giorni)}")
            
            if giorni:
                oggi = giorni[0]
                for zona_info in oggi.get("meteoPerZona", []):
                    if zona_info.get("zona") == 1:
                        forecast_data["today_forecast"] = zona_info.get("previsione", "")
                        break
                
                for mappa in oggi.get("meteoMappa", []):
                    if mappa.get("idZona") == 1:
                        forecast_data["icon_cielo"] = mappa.get("mattinaCielo", "")
                        forecast_data["icon_vento"] = mappa.get("mattinaVento", "")
                        break

    except Exception as e:
        print(f"⚠️ Errore dettagliato nel recupero delle previsioni meteo: {e}")

    return forecast_data


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
    print("Avvio aggiornamento dati meteo, allerte e scuole...")

    status, raw_message = get_campania_alert_status()
    weather_info = get_campania_weather_forecast()
    
    print(f"📡 STATO FINALE ALLERTA: {status}")

    schools_closed = False
    if status != "VERDE":
        schools_closed = check_aversa_school_status()

    message = clean_weather_message(raw_message)

    alert_data = {
        "status": status,
        "message": message,
        "weather_summary": weather_info["today_forecast"],
        "synopsis": weather_info["general_desc"],
        "icon_cielo": f"https://centrofunzionale.regione.campania.it/{weather_info['icon_cielo']}" if weather_info['icon_cielo'] else "",
        "icon_vento": f"https://centrofunzionale.regione.campania.it/{weather_info['icon_vento']}" if weather_info['icon_vento'] else "",
        "schools_closed": schools_closed,
        "updated_at": datetime.now(ZoneInfo("Europe/Rome")).strftime(
            "%d/%m/%Y, %H:%M:%S"
        ),
    }

    try:
        with open("alert.json", "w", encoding="utf-8") as f:
            json.dump(alert_data, f, ensure_ascii=False, indent=2)
        print("✅ File alert.json generato con tutte le previsioni dettagliate!")
    except Exception as e:
        print(f"❌ Errore durante il salvataggio di alert.json: {e}")


if __name__ == "__main__":
    fetch_and_update_alert()
