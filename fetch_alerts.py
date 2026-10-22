import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup


def check_aversa_school_status():
  """Scansiona Google News / testate locali per verificare se c'è un'ordinanza

  di chiusura scuole ad Aversa rilasciata nelle ultime ore.
  """
  rss_url = "https://news.google.com/rss/search?q=chiusura+scuole+aversa&hl=it&gl=IT&ceid=IT:it"

  try:
    response = requests.get(rss_url, timeout=10)
    if response.status_code == 200:
      soup = BeautifulSoup(response.content, "xml")
      items = soup.find_all("item")

      for item in items[:8]:  # Controlla le notizie più recenti
        title = item.title.text.lower()
        # Se il titolo parla esplicitamente di chiusura/sospensione ad Aversa
        if "scuole" in title and ("chius" in title or "sospens" in title) and "aversa" in title:
          return True
  except Exception as e:
    print(f"Errore controllo news scuole: {e}")

  return False


def fetch_and_update_alert():
  # 1. Recupera lo stato delle scuole tramite web scraping
  schools_closed = check_aversa_school_status()

  # 2. Esempio recupero dati bollettino Protezione Civile Campania (o logica esistente)
  # Qui imposti lo stato rilevato dal bollettino ufficiale (VERDE, GIALLA, ARANCIONE, ROSSA)
  status = "GIALLA"  # Questo valore lo leggi dal PDF/API della Protezione Civile
  message = "Allerta meteo Gialla per precipitazioni e temporali nella Zona 2 (Agro Aversano)."

  # 3. Compila il file JSON di output
  data = {
      "status": status,
      "message": message,
      "schools_closed": schools_closed,
      "updated_at": datetime.now().strftime("%d/%m/%Y, %H:%M"),
  }

  # 4. Salva in alert.json
  with open("alert.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

  print("File alert.json aggiornato con successo.")


if __name__ == "__main__":
  fetch_and_update_alert()
