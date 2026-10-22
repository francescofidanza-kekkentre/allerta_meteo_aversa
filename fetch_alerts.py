from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import re
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
import requests


def get_campania_alert_status():
  """Rileva l'allerta meteo dai comunicati ufficiali della Protezione Civile Campania.

  Usa una finestra temporale di 2 ore per azzerare i falsi positivi da
  bollettini scaduti.
  """
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

  # Cerca solo comunicati recentissimi pubblicati nelle ultime 2 ore su regione.campania.it
  rss_url = "https://news.google.com/rss/search?q=site:regione.campania.it+%22allerta+meteo%22+when:2h&hl=it&gl=IT&ceid=IT:it"

  try:
    response = requests.get(rss_url, headers=headers, timeout=10)

    if response.status_code == 200:
      soup = BeautifulSoup(response.content, "xml")
      items = soup.find_all("item")
      now_utc = datetime.now(timezone.utc)

      print(f"🔍 Articoli trovati da Protezione Civile nelle ultime 2h: {len(items)}")

      for item in items:
        title = item.title.text.lower()
        pub_date_str = item.pubDate.text if item.pubDate else None
        print(f"  📰 Titolo: {item.title.text} | Data: {pub_date_str}")

        # Filtro orario stringente (max 2.5 ore fa)
        if pub_date_str:
          try:
            pub_dt = parsedate_to_datetime(pub_date_str)
            age_hours = (now_utc - pub_dt).total_seconds() / 3600
            if age_hours > 2.5 and "prorog" not in title:
              print(
                  f"  ⏳ Scartato perché vecchio ({age_hours:.1f} ore fa) e non"
                  " è una proroga."
              )
              continue
          except Exception as e:
            print(f"  ⚠️ Errore parsing data: {e}")

        # Ignora comunicati di revoca o fine allerta
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
          print("  ✅ Scartato perché indica fine o revoca dell'allerta.")
          continue

        # Rileva il colore dell'allerta
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
