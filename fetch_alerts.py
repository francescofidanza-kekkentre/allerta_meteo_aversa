from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import re
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
import requests


def get_campania_alert_status():
  """Rileva l'allerta meteo ESCLUSIVAMENTE dai comunicati ufficiali della Protezione Civile Campania."""
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

  # Cerca i comunicati ufficiali pubblicati su regione.campania.it nelle ultime 12 ore
  rss_url = "https://news.google.com/rss/search?q=site:regione.campania.it+%22allerta+meteo%22+when:12h&hl=it&gl=IT&ceid=IT:it"

  try:
    response = requests.get(rss_url, headers=headers, timeout=10)

    if response.status_code == 200:
      soup = BeautifulSoup(response.content, "xml")
      items = soup.find_all("item")
      now_utc = datetime.now(timezone.utc)

      for item in items:
        title = item.title.text.lower()
        pub_date_str = item.pubDate.text if item.pubDate else None

        # Verifica orario di pubblicazione (max 12 ore fa)
        if pub_date_str:
          try:
            pub_dt = parsedate_to_datetime(pub_date_str)
            age_hours = (now_utc - pub_dt).total_seconds() / 3600
            if age_hours > 12 and "prorog" not in title:
              continue
          except Exception:
            pass

        # Ignora i bollettini ufficiali di revoca o fine allerta
        if any(
            w in title
            for w in [
                "revocat",
                "termina",
                "scade",
                "fine",
                "cessat",
                "verde",
                "rientr",
                "scadut",
            ]
        ):
          continue

        # Rileva il colore del bollettino ufficiale
        if "rossa" in title:
          status = "ROSSA"
          raw_message = (
              "Allerta meteo ROSSA diramata dalla Protezione Civile Campania"
              " per la Zona 1 (Piana Campana)."
          )
          break
        elif "arancione" in title:
          status = "ARANCIONE"
          raw_message = (
              "Allerta meteo ARANCIONE diramata dalla Protezione Civile Campania"
              " per la Zona 1 (Piana Campana)."
          )
          break
        elif "gialla" in title:
          status = "GIALLA"
          raw_message = (
              "Allerta meteo GIALLA diramata dalla Protezione Civile Campania"
              " per la Zona 1 (Piana Campana)."
          )
          break

  except Exception as e:
    print(f"⚠️ Errore durante la consultazione della Protezione Civile: {e}")

  return status, raw_message


def check_aversa_school_status():
  """Verifica prima il sito del Comune di Aversa. Se non c'è nulla, passa ai giornali locali."""
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }

  # 1. Verifica sul sito UFFICIALE del Comune di Aversa
  comune_rss = "https://news.google.com/rss/search?q=site:comune.aversa.ce.it+(scuole+OR+ordinanza)+when:24h&hl=it&gl=IT&ceid=IT:it"
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
    print(f"⚠️ Errore durante la verifica sul sito del Comune: {e}")

  # 2. Consultazione dei GIORNALI LOCALI (solo se l'allerta non è verde)
  news_rss = "https://news.google.com/rss/search?q=chiusura+scuole+aversa+when:12h&hl=it&gl=IT&ceid=IT:it"
  try:
    resp_news = requests.get(news_rss, headers=headers, timeout=10)
    if resp_news.status_code == 200:
      soup_news = BeautifulSoup(resp_news.content, "xml")
      items_news = soup_news.find_all("item")
      for item in items_news[:5]:
        title = item.title.text.lower()
        if (
            ("scuole" in title or "scuola" in title)
            and ("chius" in title or "sospens" in title or "stop" in title)
            and "aversa" in title
        ):
          if not any(
              w in title
              for w in ["aperta", "aperte", "regolare", "smentita", "falso"]
          ):
            return True
  except Exception as e:
    print(f"⚠️ Errore durante la verifica sui giornali locali: {e}")

  return False


def clean_weather_message(raw_message):
  """Pulisce il testo del messaggio."""
  if not raw_message:
    return "Bollettino meteo in aggiornamento."

  pattern = (
      r"(?i)(i quotidiani locali|i giornali|il comune|ordinanza).*?(chiusura|scuole).*?\."
  )
  cleaned = re.sub(pattern, "", raw_message).strip()
  return cleaned if cleaned else raw_message


def fetch_and_update_alert():
  print("Avvio aggiornamento dati meteo e scuole...")

  # 1. Rileva l'allerta SOLO dai comunicati ufficiali della Protezione Civile Campania
  status, raw_message = get_campania_alert_status()
  print(f"📡 Stato Allerta Ufficiale Rilevato: {status}")

  # 2. Rileva lo stato delle scuole solo se l'allerta non è VERDE
  schools_closed = False
  if status != "VERDE":
    schools_closed = check_aversa_school_status()

  # 3. Pulisce il messaggio
  message = clean_weather_message(raw_message)

  # 4. Salva il file JSON con orario italiano (Europe/Rome)
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
