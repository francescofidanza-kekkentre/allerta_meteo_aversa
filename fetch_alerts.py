from datetime import datetime
import json
import re
from bs4 import BeautifulSoup
import requests


def check_aversa_school_status():
  """Scansiona i feed di notizie e le testate locali per verificare se è stata

  emessa un'ordinanza reale di chiusura delle scuole ad Aversa.
  """
  rss_url = "https://news.google.com/rss/search?q=chiusura+scuole+aversa&hl=it&gl=IT&ceid=IT:it"

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/120.0.0.0 Safari/537.36"
      )
  }

  try:
    response = requests.get(rss_url, headers=headers, timeout=10)
    if response.status_code == 200:
      soup = BeautifulSoup(response.content, "xml")
      items = soup.find_all("item")

      for item in items[:10]:
        title = item.title.text.lower()
        if (
            ("scuole" in title or "scuola" in title)
            and ("chius" in title or "sospens" in title or "stop" in title)
            and "aversa" in title
        ):
          print(f"Trovata notizia di chiusura: {item.title.text}")
          return True
  except Exception as e:
    print(f"⚠️ Errore durante lo scraping delle notizie: {e}")

  return False


def clean_weather_message(raw_message):
  """Pulisce il testo rimuovendo riferimenti obsoleti o errati alla Zona 2

  e frasi fuorvianti sulle scuole.
  """
  if not raw_message:
    return "Bollettino meteo in aggiornamento per la Zona 1 (Piana Campana)."

  # Corregge eventuali residui di 'Zona 2' con 'Zona 1'
  message = raw_message.replace("Zona 2", "Zona 1").replace(
      "Agro Aversano", "Piana Campana"
  )

  # Rimuove frasi o riferimenti arbitrari alle scuole
  pattern = (
      r"(?i)(i quotidiani locali|i giornali|il comune|ordinanza).*?(chiusura|scuole).*?\."
  )
  cleaned = re.sub(pattern, "", message).strip()

  return (
      cleaned
      if cleaned
      else "Allerta meteo in vigore per la Zona 1 (Piana Campana)."
  )


def fetch_and_update_alert():
  """Funzione principale di aggiornamento dati."""
  print("Avvio aggiornamento alert.json...")

  # 1. Scraping dinamico per lo stato scuole
  schools_closed = check_aversa_school_status()

  # 2. Definizione stato e messaggio aggiornato con Zona 1
  status = "GIALLA"
  raw_message = (
      "Allerta meteo GIALLA per temporali e locali allagamenti per la Zona 1"
      " (Piana Campana)."
  )

  # Pulisce il testo
  message = clean_weather_message(raw_message)

  # 3. Strutturazione JSON
  alert_data = {
      "status": status.upper(),
      "message": message,
      "schools_closed": schools_closed,
      "updated_at": datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
  }

  # 4. Scrittura su file alert.json
  try:
    with open("alert.json", "w", encoding="utf-8") as f:
      json.dump(alert_data, f, ensure_ascii=False, indent=2)
    print("alert.json aggiornato con successo con la Zona 1!")
    print(json.dumps(alert_data, indent=2, ensure_ascii=False))
  except Exception as e:
    print(f"❌ Errore durante la scrittura di alert.json: {e}")


if __name__ == "__main__":
  fetch_and_update_alert()
