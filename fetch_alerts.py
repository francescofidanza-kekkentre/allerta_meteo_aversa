from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import re
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
import requests


def get_campania_alert_status():
  """Rileva l'allerta meteo ESCLUSIVAMENTE dal sito ufficiale della Protezione Civile Campania

  (Centro Funzionale / Regione Campania).
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

  # 1. Ricerca ristretta ESCLUSIVAMENTE al dominio ufficiale regione.campania.it nelle ultime 24h
  rss_url = "https://news.google.com/rss/search?q=site:regione.campania.it+%22allerta+meteo%22+when:24h&hl=it&gl=IT&ceid=IT:it"

  try:
    response = requests.get(rss_url, headers=headers, timeout=10)
    found_official = False

    if response.status_code == 200:
      soup = BeautifulSoup(response.content, "xml")
      items = soup.find_all("item")
      now_utc = datetime.now(timezone.utc)

      for item in items:
        title = item.title.text.lower()
        pub_date_str = item.pubDate.text if item.pubDate else None

        if pub_date_str:
          try:
            pub_dt = parsedate_to_datetime(pub_date_str)
            age_hours = (now_utc - pub_dt).total_seconds() / 3600
            if age_hours > 24:
              continue
          except Exception:
            pass

        # Ignora i bollettini ufficiali di revoca o termine allerta
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

        if "rossa" in title:
          status = "ROSSA"
          raw_message = (
              "Allerta meteo ROSSA diramata dalla Protezione Civile Campania"
              " per la Zona 1 (Piana Campana)."
          )
          found_official = True
          break
        elif "arancione" in title:
          status = "ARANCIONE"
          raw_message = (
              "Allerta meteo ARANCIONE diramata dalla Protezione Civile Campania"
              " per la Zona 1 (Piana Campana)."
          )
          found_official = True
          break
        elif "gialla" in title:
          status = "GIALLA"
          raw_message = (
              "Allerta meteo GIALLA diramata dalla Protezione Civile Campania"
              " per la Zona 1 (Piana Campana)."
          )
          found_official = True
          break

    # 2. Controllo diretto sul portale del Centro Funzionale se non trova post recenti
    if not found_official:
      cf_url = "https://centrofunzionale.regione.campania.it/"
      cf_resp = requests.get(cf_url, headers=headers, timeout=8)
      if cf_resp.status_code == 200:
        cf_soup = BeautifulSoup(cf_resp.text, "html.parser")
        page_text = cf_soup.get_text().lower()

        if (
            "allerta rossa" in page_text
            or "criticità elevata (rossa)" in page_text
        ):
          status = "ROSSA"
          raw_message = (
              "Allerta meteo ROSSA attiva dal Centro Funzionale della"
              " Protezione Civile Campania."
          )
        elif (
            "allerta arancione" in page_text
            or "criticità moderata (arancione)" in page_text
        ):
          status = "ARANCIONE"
          raw_message = (
              "Allerta meteo ARANCIONE attiva dal Centro Funzionale della"
              " Protezione Civile Campania."
          )
        elif (
            "allerta gialla" in page_text
            or "criticità ordinaria (gialla)" in page_text
        ):
          status = "GIALLA"
          raw_message = (
              "Allerta meteo GIALLA attiva dal Centro Funzionale della"
              " Protezione Civile Campania."
          )

  except Exception as e:
    print(
        "⚠️ Errore durante la consultazione ufficiale della Protezione Civile:"
        f" {e}"
    )

  return status, raw_message


def check_aversa_school_status():
  """Verifica prima il sito del Comune di Aversa.

  Se non c'è nulla, passa alla scansione dei giornali locali.
  """
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }

  # --- FASE 1: Verifica sul sito UFFICIALE del Comune di Aversa ---
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
          print(
              "🏫 Chiusura scuole CONFERMATA dal sito UFFICIALE del Comune di"
              " Aversa"
          )
          return True
  except Exception as e:
    print(f"⚠️ Errore durante la verifica sul sito del Comune: {e}")

  # --- FASE 2: Fallback sui GIORNALI LOCALI (se il Comune non ha pubblicato nulla) ---
  print(
      "ℹ️ Nessun avviso sul sito del Comune. Consultazione dei giornali"
      " locali..."
  )
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
            print(
                "📰 Chiusura scuole rilevata dai giornali locali:"
                f" {item.title.text}"
            )
            return True
  except Exception as e:
    print(f"⚠️ Errore durante la verifica sui giornali locali: {e}")

  return False


def clean_weather_message(raw_message):
  """Pulisce il testo da eventuali residui inutili."""
  if not raw_message:
    return "Bollettino meteo in aggiornamento."

  pattern = (
      r"(?i)(i quotidiani locali|i giornali|il comune|ordinanza).*?(chiusura|scuole).*?\."
  )
  cleaned = re.sub(pattern, "", raw_message).strip()
  return cleaned if cleaned else raw_message


def fetch_and_update_alert():
  print("Avvio aggiornamento dati meteo e scuole...")

  # 1. Rileva l'allerta SOLO dai canali ufficiali della Protezione Civile Campania
  status, raw_message = get_campania_alert_status()
  print(f"📡 Stato Allerta Ufficiale Rilevato: {status}")

  # 2. Rileva lo stato delle scuole (Comune -> Giornali locali) solo in presenza di maltempo
  schools_closed = False
  if status != "VERDE":
    schools_closed = check_aversa_school_status()
    print(f"🏫 Scuole Chiuse: {schools_closed}")

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
