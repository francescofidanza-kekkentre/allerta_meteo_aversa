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
                    fenomeni = area.get("fenomeni", "")
                    
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
                            f"Centro Funzionale Multirischi Campania per la Zona 1. {fenomeni}"
                        )
                    else:
                        if fenomeni:
                            raw_message = f"Condizioni per la Zona 1: {fenomeni}"
                    
                    print(f"✅ Stato allerta Zona 1: {status}")
                    break

    except Exception as e:
        print(f"⚠️ Errore durante l'interrogazione dell'API allerte: {e}")

    return status, raw_message


def get_aversa_open_meteo_forecast():
    """Estrae le previsioni meteo dettagliate per Aversa tramite Open-Meteo."""
    # Coordinate geografiche di Aversa (CE)
    lat = 40.9731
    lon = 14.2043
    
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=Europe%2FRome"
    
    forecast_info = {
        "temp_current": None,
        "temp_max": None,
        "temp_min": None,
        "weather_desc": "Previsioni in aggiornamento",
        "wind_speed": None
    }

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            current = data.get("current", {})
            daily = data.get("daily", {})
            
            forecast_info["temp_current"] = current.get("temperature_2m")
            forecast_info["wind_speed"] = current.get("wind_speed_10m")
            
            if daily.get("temperature_2m_max"):
                forecast_info["temp_max"] = daily["temperature_2m_max"][0]
            if daily.get("temperature_2m_min"):
                forecast_info["temp_min"] = daily["temperature_2m_min"][0]
                
            # Codici meteo semplificati WMO
            wmo_code = current.get("weather_code", 0)
            forecast_info["weather_desc"] = translate_wmo_code(wmo_code)
            
            print("✅ Previsioni Open-Meteo per Aversa scaricate con successo!")
    except Exception as e:
        print(f"⚠️ Errore nel recupero dati Open-Meteo: {e}")

    return forecast_info


def translate_wmo_code(code):
    """Converte il codice numerico WMO in una descrizione testuale in italiano."""
    weather_map = {
        0: "Cielo sereno",
        1: "Principalmente sereno",
        2: "Parzialmente nuvoloso",
        3: "Coperto",
        45: "Nebbia",
        48: "Nebbia con brina",
        51: "Pioviggine leggera",
        53: "Pioviggine moderata",
        55: "Pioviggine densa",
        61: "Pioggia debole",
        63: "Pioggia moderata",
        65: "Pioggia forte",
        71: "Nevicata debole",
        73: "Nevicata moderata",
        75: "Nevicata forte",
        80: "Rovesci di pioggia deboli",
        81: "Rovesci di pioggia moderati",
        82: "Rovesci di pioggia violenti",
        95: "Temporale",
        96: "Temporale con grandine leggera",
        99: "Temporale con grandine forte"
    }
    return weather_map.get(code, "Variabile")


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
    print("Avvio aggiornamento dati allerte, meteo e scuole...")

    status, raw_message = get_campania_alert_status()
    weather_data = get_aversa_open_meteo_forecast()
    
    print(f"📡 STATO FINALE ALLERTA: {status}")

    schools_closed = False
    if status != "VERDE":
        schools_closed = check_aversa_school_status()

    message = clean_weather_message(raw_message)

    # Struttura dati completa inviata alla PWA tramite alert.json
    alert_data = {
        "status": status,
        "message": message,
        "weather_summary": weather_data["weather_desc"],
        "temperature": weather_data["temp_current"],
        "temp_max": weather_data["temp_max"],
        "temp_min": weather_data["temp_min"],
        "wind_speed": weather_data["wind_speed"],
        "schools_closed": schools_closed,
        "updated_at": datetime.now(ZoneInfo("Europe/Rome")).strftime(
            "%d/%m/%Y, %H:%M:%S"
        ),
    }

    try:
        with open("alert.json", "w", encoding="utf-8") as f:
            json.dump(alert_data, f, ensure_ascii=False, indent=2)
        print("✅ File alert.json generato con previsioni e allerte!")
    except Exception as e:
        print(f"❌ Errore durante il salvataggio di alert.json: {e}")


if __name__ == "__main__":
    fetch_and_update_alert()
