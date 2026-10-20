const { chromium } = require('playwright');
const fs = require('fs');
const axios = require('axios');
const xml2js = require('xml2js');

async function runScraper() {
  console.log('--- Avvio Scraping Meteo & Ordinanze Aversa ---');
  
  let browser;
  let statusAllerta = 'VERDE';
  let dettaglioAllerta = 'Nessuna allerta meteo critica in vigore per la Zona 2 (Agro Aversano).';
  let infoOrdinanzaScuole = null;

  try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    });
    const page = await context.newPage();

    // METODO 1: Scraping Bollettino Protezione Civile Campania (Attuale & Previsto)
    console.log('1. Controllo Bollettino Protezione Civile Campania...');
    try {
      await page.goto('https://centrofunzionale.regione.campania.it/', { timeout: 35000, waitUntil: 'networkidle' });
      
      const fullText = await page.textContent('body');

      // Helper per valutare la gravità del livello
      function getLevelScore(text) {
        if (/ROSSA/i.test(text)) return 3;
        if (/ARANCIONE/i.test(text)) return 2;
        if (/GIALLA/i.test(text)) return 1;
        return 0;
      }

      let maxScore = 0;

      // Analizza tutto il testo visibile nella pagina cercando i blocchi di allerta
      if (/ARANCIONE/i.test(fullText)) {
        maxScore = Math.max(maxScore, 2);
      }
      if (/ROSSA/i.test(fullText)) {
        maxScore = Math.max(maxScore, 3);
      }
      if (/GIALLA/i.test(fullText) && maxScore < 1) {
        maxScore = 1;
      }

      // Assegna lo stato in base al rischio più alto (Attuale o Previsto)
      if (maxScore === 3) {
        statusAllerta = 'ROSSA';
        dettaglioAllerta = 'Allerta meteo ROSSA (Criticità Elevata) prevista/in vigore per la Zona 2 (Agro Aversano).';
      } else if (maxScore === 2) {
        statusAllerta = 'ARANCIONE';
        dettaglioAllerta = 'Allerta meteo ARANCIONE per rischio idrogeologico e temporali prevista/in vigore per la Zona 2 (Agro Aversano).';
      } else if (maxScore === 1) {
        statusAllerta = 'GIALLA';
        dettaglioAllerta = 'Allerta meteo GIALLA per temporali e locali allagamenti per la Zona 2 (Agro Aversano).';
      }

    } catch (e) {
      console.warn('⚠️ Errore durante lo scraping della Protezione Civile:', e.message);
    }

    // Se c'è un'allerta (Gialla, Arancione o Rossa), verifica le ordinanze comunali sulle scuole
    if (statusAllerta !== 'VERDE') {
      
      // METODO 2: Scraping Albo Pretorio / Notizie del Comune di Aversa
      console.log('2. Scraping Notizie dal sito del Comune di Aversa...');
      try {
        await page.goto('https://www.comune.aversa.ce.it/', { timeout: 20000, waitUntil: 'domcontentloaded' });
        const comuneText = await page.textContent('body');

        const regexScuole = /(chiusura|sospensione).*scuole|scuole.*chiuse|ordinanza.*scuole/i;
        if (regexScuole.test(comuneText)) {
          infoOrdinanzaScuole = 'Disposta la chiusura delle scuole e delle strutture pubbliche ad Aversa con ordinanza comunale.';
        }
      } catch (e) {
        console.warn('⚠️ Errore scraping Comune di Aversa:', e.message);
      }

      // METODO 3: Analisi Google News RSS per testate locali casertane
      if (!infoOrdinanzaScuole) {
        console.log('3. Analisi Notizie Locali via Feed RSS Google News...');
        try {
          const rssUrl = 'https://news.google.com/rss/search?q=chiusura+scuole+aversa&hl=it&gl=IT&ceid=IT:it';
          const response = await axios.get(rssUrl, { timeout: 10000 });
          const parser = new xml2js.Parser();
          const result = await parser.parseStringPromise(response.data);

          const items = result.rss.channel[0].item || [];
          for (const item of items) {
            const title = item.title ? item.title[0] : '';
            if (/scuole/i.test(title) && /chius|sospens/i.test(title) && /aversa/i.test(title)) {
              infoOrdinanzaScuole = 'I quotidiani locali riportano la disposizione di chiusura delle scuole ad Aversa.';
              break;
            }
          }
        } catch (e) {
          console.warn('⚠️ Errore analisi Feed RSS:', e.message);
        }
      }
    }

  } catch (err) {
    console.error('❌ Errore generale durante lo scraping:', err.message);
  } finally {
    if (browser) await browser.close();
  }

  // Costruzione del messaggio per il riquadro giallo della PWA
  let messaggioFinale = dettaglioAllerta;
  if (infoOrdinanzaScuole) {
    messaggioFinale += ' ' + infoOrdinanzaScuole;
  } else if (statusAllerta === 'ARANCIONE' || statusAllerta === 'ROSSA') {
    messaggioFinale += ' Si consiglia di verificare l\'albo pretorio del Comune di Aversa per eventuali ordinanze sindacali dell\'ultimo minuto.';
  }

  const outputData = {
    status: statusAllerta,
    message: messaggioFinale,
    scuole_chiuse: !!infoOrdinanzaScuole,
    updated_at: new Date().toLocaleString('it-IT', { timeZone: 'Europe/Rome' })
  };

  fs.writeFileSync('./alert.json', JSON.stringify(outputData, null, 2));
  console.log('✅ File alert.json aggiornato con successo:', outputData);
}

runScraper();
