from datetime import datetime
import json
import re
from bs4 import BeautifulSoup
import requests


def get_campania_alert_status():
  """Rileva automaticamente il livello di allerta meteo della Protezione Civile Campania

  analizzando le pubblicazioni delle ultime 24 ore.
  Ritorna lo stato (VERDE, GIALLA, ARANCIONE, ROSSA) e un messaggio generato.
  """
  # Cerca notizie esatte sull'allerta meteo in Campania diramate nelle ultime 24h
  rss_url = "https://news.google.com/rss/search?q=%22allerta+meteo%22+campania+when:24h&hl=it&gl=IT&ceid=IT:it"
  
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/120.0.0.0 Safari/537.36"
      )
  }

  status = "VERDE"
  raw_message = "Nessuna allerta meteo. Condizioni meteorologiche nella norma per la Zona 1 (Piana Campana)."

  try:
    response = requests.get(rss_url, headers=headers, timeout=10)
    if response.status_code == 200:
      soup = BeautifulSoup(response.content, "xml")
      items = soup.find_all("item")

      for item in items:
        title = item.title.text.lower()
        
        # Se il bollettino parla di allerta revocata, terminata o in scadenza, ignoriamo
        if "revocat" in title or "termina" in title or "scade" in title or "fine" in title:
            continue

        # Scala di priorità: controlliamo prima la gravità massima
        if "rossa" in title:
            status = "ROSSA"
            raw_message = "Allerta meteo ROSSA per precipitazioni molto intense e rischio idrogeologico per la Zona 1 (Piana Campana)."
            break
        elif "arancione" in title:
            status = "ARANCIONE"
            raw_message = "Allerta meteo ARANCIONE per fenomeni temporaleschi intensi e instabilità per la Zona 1 (Piana Campana)."
            break
        elif "gialla" in title:
            status = "GIALLA"
            raw_message = "Allerta meteo GIALLA per possibili rovesci e temporali locali per la Zona 1 (Piana Campana)."
            break

  except Exception as e:
    print(f"⚠️ Errore durante il recupero del bollettino meteo: {e}")

  return status, raw_message


def check_aversa_school_status():
  """Verifica se è stata emessa un'ordinanza di chiusura scuole ad Aversa."""
  rss_url = "https://news.google.com/rss/search?q=chiusura+scuole+aversa+when:24h&hl=it&gl=IT&ceid=IT:it"
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }

  try:
    response = requests.get(rss_url, headers=headers, timeout=10)
    if response.status_code == 200:
      soup = BeautifulSoup(response.content, "xml")
      items = soup.find_all("item")

      for item in items[:5]:
        title = item.title.text.lower()
        if (
            ("scuole" in title or "scuola" in title)
            and ("chius" in title or "sospens" in title or "stop" in title)
            and "aversa" in title
        ):
          return True
  except Exception as e:
    print(f"⚠️ Errore controllo notizie scuole: {e}")

  return False


def clean_weather_message(raw_message):
  """Assicura che il testo finale non contenga frasi fuorvianti generate dai giornali."""
  if not raw_message:
    return "Bollettino meteo in aggiornamento."

  pattern = r"(?i)(i quotidiani locali|i giornali|il comune|ordinanza).*?(chiusura|scuole).*?\."
  cleaned = re.sub(pattern, "", raw_message).strip()
  return cleaned if cleaned else raw_message


def fetch_and_update_alert():
  print("Avvio aggiornamento dati meteo e scuole...")

  # 1. Rileva dinamicamente l'Allerta Meteo per la Regione Campania
  status, raw_message = get_campania_alert_status()
  print(f"📡 Stato Allerta Rilevato: {status}")

  # 2. Ottimizzazione: Rileva lo stato delle scuole SOLO se l'allerta non è VERDE
  schools_closed = False
  if status != "VERDE":
      schools_closed = check_aversa_school_status()
      print(f"🏫 Scuole Chiuse: {schools_closed}")

  # 3. Pulisce il messaggio
  message = clean_weather_message(raw_message)

  # 4. Compila il file JSON dinamico
  alert_data = {
      "status": status,
      "message": message,
      "schools_closed": schools_closed,
      "updated_at": datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
  }

  # 5. Salva su alert.json
  try:
    with open("alert.json", "w", encoding="utf-8") as f:
      json.dump(alert_data, f, ensure_ascii=False, indent=2)
    print("✅ File alert.json generato con successo e 100% dinamico!")
  except Exception as e:
    print(f"❌ Errore durante il salvataggio di alert.json: {e}")


if __name__ == "__main__":
  fetch_and_update_alert()
