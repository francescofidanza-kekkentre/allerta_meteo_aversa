from datetime import datetime
import json
import re
from bs4 import BeautifulSoup
import requests


def check_aversa_school_status():
  """Scansiona i feed di notizie e le testate locali per verificare se è stata

  emessa un'ordinanza reale di chiusura delle scuole ad Aversa.
  """
  # Feed RSS di Google News filtrato sulle notizie locali di Aversa e scuole
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

      for item in items[:10]:  # Analizza le prime 10 notizie più recenti
        title = item.title.text.lower()

        # Condizione: la notizia deve menzionare Aversa, le scuole e la chiusura/sospensione
        if (
            ("scuole" in title or "scuola" in title)
            and ("chius" in title or "sospens" in title or "stop" in title)
            and "aversa" in title
        ):
          print(f" Trovata notizia di chiusura: {item.title.text}")
          return True
  except Exception as e:
    print(f"⚠️ Errore durante lo scraping delle notizie: {e}")

  return False


def clean_weather_message(raw_message):
  """Rimuove frasi o riferimenti arbitrari alle scuole dal testo del bollettino

  per evitare incongruenze con la voce 'schools_closed'.
  """
  if not raw_message:
    return "Bollettino meteo in aggiornamento per la Zona 2 (Agro Aversano)."

  # Pattern regex per rimuovere frasi relative alle scuole dal testo
  pattern = (
      r"(?i)(i quotidiani locali|i giornali|il comune|ordinanza).*?(chiusura|scuole).*?\."
  )
  cleaned = re.sub(pattern, "", raw_message).strip()

  return (
      cleaned
      if cleaned
      else "Allerta meteo in vigore per la Zona 2 (Agro Aversano)."
  )


def fetch_and_update_alert():
  """Funzione principale di aggiornamento dati."""
  print("Avvio aggiornamento alert.json...")

  # 1. Scraping dinamico per lo stato scuole
  schools_closed = check_aversa_school_status()

  # 2. Definizione stato ed estrazione testo bollettino
  # (Sostituire status e raw_message con la logica di lettura dal bollettino Protezione Civile Campania)
  status = "GIALLA"
  raw_message = (
    "Allerta meteo GIALLA per temporali e locali allagamenti per la Zona 1"
    " (Piana campana, Napoli, Isole e Area vesuviana)."
  )

  # Pulisce il testo da eventuali frasi fuorvianti
  message = clean_weather_message(raw_message)

  # 3. Strutturazione del file JSON finale
  alert_data = {
      "status": status.upper(),
      "message": message,
      "schools_closed": schools_closed,
      "updated_at": datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
  }

  # 4. Scrittura su alert.json
  try:
    with open("alert.json", "w", encoding="utf-8") as f:
      json.dump(alert_data, f, ensure_ascii=False, indent=2)
    print(" alert.json aggiornato con successo.")
    print(json.dumps(alert_data, indent=2, ensure_ascii=False))
  except Exception as e:
    print(f"❌ Errore durante la scrittura di alert.json: {e}")


if __name__ == "__main__":
  fetch_and_update_alert()
