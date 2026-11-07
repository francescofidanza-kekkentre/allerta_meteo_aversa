from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import json
import re
import sys
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
import requests


class AlertSourceError(Exception):
    """Il bollettino ufficiale non è disponibile o non è interpretabile."""


def get_campania_alert_status():
    """Rileva l'allerta meteo interrogando l'API JSON ufficiale del Centro Funzionale per la Zona 1.

    Solleva AlertSourceError se il dato non è affidabile (API irraggiungibile,
    risposta non valida, Zona 1 assente o livello non riconosciuto), così da
    non pubblicare mai un VERDE "di default".
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    api_url = "https://centrofunzionale.regione.campania.it/CentroFunzionalePortaleRest/rest/bollettinometeo/findLastBollettinoInserito/"

    try:
        response = requests.get(api_url, headers=headers, timeout=20)
        response.raise_for_status()
        dati = response.json()
    except (requests.RequestException, ValueError) as e:
        raise AlertSourceError(f"API Centro Funzionale non disponibile: {e}") from e

    area = next(
        (a for a in dati.get("bollettinoMeteoBindList") or [] if a.get("zona") == 1),
        None,
    )
    if area is None:
        raise AlertSourceError("Zona 1 assente nel bollettino del Centro Funzionale.")

    descrizione = (area.get("livelloDesc") or "").upper()
    fenomeni = area.get("fenomeni") or ""

    if "ROSS" in descrizione:
        status = "ROSSA"
    elif "ARANCION" in descrizione:
        status = "ARANCIONE"
    elif "GIALL" in descrizione:
        status = "GIALLA"
    elif "VERD" in descrizione:
        status = "VERDE"
    else:
        raise AlertSourceError(f"Livello di allerta non riconosciuto: {descrizione!r}")

    if status != "VERDE":
        raw_message = (
            f"Allerta meteo {status} confermata dal bollettino del "
            f"Centro Funzionale Multirischi Campania per la Zona 1. {fenomeni}"
        )
    elif fenomeni:
        raw_message = f"Condizioni per la Zona 1: {fenomeni}"
    else:
        raw_message = (
            "Nessuna allerta meteo in vigore. Condizioni meteorologiche nella norma"
            " per la Zona 1 (Piana Campana)."
        )

    print(f"✅ Stato allerta Zona 1: {status} (bollettino {dati.get('dataEmissione')})")
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


# ---------------------------------------------------------------------------
# Chiusura scuole: fonti ufficiali del Comune di Aversa
# ---------------------------------------------------------------------------
ALBO_URL = "https://aversa.nuvolapalitalsoft.it/?page_id=35624"  # Albo pretorio online
COMUNE_FEED_URL = "https://comune.aversa.ce.it/feed/?post_type=notizia"  # Novità del sito istituzionale
ROME = ZoneInfo("Europe/Rome")

MESI = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6,
    "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}
# Un atto riguarda la chiusura generale delle scuole se cita le scuole, una
# chiusura/sospensione e un ambito generale (tutte le scuole o motivo meteo).
RE_SCUOLE = re.compile(r"scuol|scolastic|didattic|istitut\w* comprensiv")
RE_CHIUSURA = re.compile(r"chius|sospension|sospes|interruzion")
RE_AMBITO = re.compile(
    r"ogni ordine|tutte le scuole|tutti gli istituti|tutti i plessi|intero territorio"
    r"|territorio comunale|allerta|meteo|maltempo|avvers|precipitazion|vento|neve"
    r"|protezione civile"
)
# Ordinanze di viabilità ("Via X: chiusura al traffico presso il plesso scolastico")
RE_VIABILITA = re.compile(r"circolazione|\bsosta\b|viabilit|traffico")


def _date_nel_testo(testo, riferimento):
    """Estrae le date citate nel testo ("12 novembre 2026", "11 e 12 novembre", "12/11/2026")."""
    date = []
    for g, m, a in re.findall(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b", testo):
        try:
            date.append(datetime(int(a), int(m), int(g)).date())
        except ValueError:
            pass
    pattern_mese = (
        r"((?:\d{1,2}\s*(?:,|e|ed|-|al|/)?\s*)+)(" + "|".join(MESI) + r")(?:\s+(\d{4}))?"
    )
    for giorni, mese, anno in re.findall(pattern_mese, testo):
        for g in re.findall(r"\d{1,2}", giorni):
            anno_val = int(anno) if anno else riferimento.year
            try:
                d = datetime(anno_val, MESI[mese], int(g)).date()
            except ValueError:
                continue
            if not anno and (d - riferimento).days < -180:  # es. atto di dicembre per gennaio
                d = d.replace(year=d.year + 1)
            date.append(d)
    return date


def _valuta_atto(testo, data_atto, oggi):
    """Restituisce "chiusura", "revoca" o None per un atto, considerando le sue date.

    Se l'atto cita delle date, conta solo se il periodo tocca oggi o domani;
    altrimenti vale solo se emesso oggi o ieri.
    """
    t = testo.lower()
    if not (RE_SCUOLE.search(t) and RE_CHIUSURA.search(t)) or RE_VIABILITA.search(t):
        return None
    if "revoc" in t:
        return "revoca" if (oggi - data_atto).days <= 2 else None
    if not RE_AMBITO.search(t):
        return None

    date = _date_nel_testo(t, data_atto)
    if date:
        domani = oggi + timedelta(days=1)
        attivo = min(date) <= domani and max(date) >= oggi
    else:
        attivo = 0 <= (oggi - data_atto).days <= 1
    return "chiusura" if attivo else None


def _atti_albo_pretorio(headers):
    """Atti in pubblicazione sull'albo pretorio: (testo, data atto, link)."""
    resp = requests.get(ALBO_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "lxml")
    tabella = soup.find("table", id="tabella_risultati")
    if tabella is None or tabella.tbody is None:
        raise ValueError("tabella dell'albo pretorio non trovata")
    atti = []
    for riga in tabella.tbody.find_all("tr"):
        celle = [td.get_text(" ", strip=True) for td in riga.find_all("td")]
        if len(celle) < 7:
            continue
        tipo, numero, data_str, oggetto = celle[2], celle[3], celle[4], celle[5]
        try:
            data_atto = datetime.strptime(data_str, "%d/%m/%Y").date()
        except ValueError:
            continue
        link = riga.find("a", href=True)
        atti.append((
            f"{tipo} n. {numero} del {data_str}: {oggetto}",
            data_atto,
            link["href"] if link else ALBO_URL,
        ))
    return atti


def _notizie_sito_comune(headers):
    """Novità pubblicate sul sito del Comune: (titolo + estratto, data, link)."""
    resp = requests.get(COMUNE_FEED_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "xml")
    notizie = []
    for item in soup.find_all("item"):
        if not (item.title and item.pubDate):
            continue
        estratto = BeautifulSoup(item.description.text, "lxml").get_text(" ", strip=True) if item.description else ""
        data = parsedate_to_datetime(item.pubDate.text).astimezone(ROME).date()
        notizie.append((
            f"{item.title.text.strip()} - {estratto}",
            data,
            item.link.text.strip() if item.link else COMUNE_FEED_URL,
        ))
    return notizie


def check_aversa_school_status():
    """Verifica sulle fonti ufficiali del Comune se le scuole di Aversa sono chiuse.

    Restituisce (chiuse, avviso) dove avviso è {"text", "url"} dell'atto trovato,
    oppure None se nessuna fonte è raggiungibile (stato non determinabile).
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    oggi = datetime.now(ROME).date()

    atti, fonti_ok = [], 0
    for nome, fonte in (("albo pretorio", _atti_albo_pretorio), ("sito del Comune", _notizie_sito_comune)):
        try:
            risultati = fonte(headers)
            print(f"🏫 {nome}: {len(risultati)} atti/notizie letti")
            atti.extend(risultati)
            fonti_ok += 1
        except Exception as e:
            print(f"⚠️ Errore lettura {nome}: {e}")
    if fonti_ok == 0:
        return None

    chiusure, revoche = [], []
    for testo, data_atto, link in atti:
        esito = _valuta_atto(testo, data_atto, oggi)
        if esito == "chiusura":
            chiusure.append((data_atto, testo, link))
        elif esito == "revoca":
            revoche.append((data_atto, testo, link))

    if not chiusure:
        return False, None
    data_c, testo_c, link_c = max(chiusure, key=lambda x: x[0])
    if revoche and max(revoche, key=lambda x: x[0])[0] >= data_c:
        print(f"🏫 Chiusura revocata: {max(revoche, key=lambda x: x[0])[1]}")
        return False, None
    print(f"🏫 Chiusura scuole trovata: {testo_c}")
    return True, {"text": testo_c, "url": link_c}


def _stato_scuole_precedente():
    try:
        with open("alert.json", encoding="utf-8") as f:
            precedente = json.load(f)
        return precedente.get("schools_closed", False), precedente.get("schools_notice")
    except (OSError, ValueError):
        return False, None


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

    try:
        status, raw_message = get_campania_alert_status()
    except AlertSourceError as e:
        # Non sovrascrivere alert.json: resta pubblicato l'ultimo dato valido
        # e il workflow fallisce, rendendo l'errore visibile in GitHub Actions.
        print(f"❌ {e}")
        print("❌ alert.json NON aggiornato: resta valido l'ultimo stato pubblicato.")
        sys.exit(1)

    weather_data = get_aversa_open_meteo_forecast()
    
    print(f"📡 STATO FINALE ALLERTA: {status}")

    scuole = check_aversa_school_status()
    if scuole is None:
        # Fonti del Comune non raggiungibili: mantieni l'ultimo stato noto.
        print("⚠️ Stato scuole non verificabile: mantengo l'ultimo valore pubblicato.")
        schools_closed, schools_notice = _stato_scuole_precedente()
    else:
        schools_closed, schools_notice = scuole
    print(f"🏫 Scuole: {'CHIUSE' if schools_closed else 'APERTE'}")

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
        "schools_notice": schools_notice,
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
