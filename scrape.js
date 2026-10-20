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

    // METODO 1: Scraping Bollettino Protezione Civile Campania
    console.log('1. Controllo Bollettino Protezione Civile Campania...');
    try {
      await page.goto('https://centrofunzionale.regione.campania.it/', { timeout: 30000, waitUntil: 'domcontentloaded' });
      const content = await page.textContent('body');

      if (/ARANCIONE/i.test(content) && /Zona 2|Agro Aversano/i.test(content)) {
        statusAllerta = 'ARANCIONE';
        dettaglioAllerta = 'Previsti temporali di forte intensità con rischio idrogeologico sulla Zona 2.';
      } else if (/GIALLA/i.test(content) && /Zona 2|Agro Aversano/i.test(content)) {
        statusAllerta = 'GIALLA';
        dettaglioAllerta = 'Previsti fenomeni temporaleschi e locali allagamenti per la Zona 2.';
      } else if (/ROSSA/i.test(content) && /Zona 2|Agro Aversano/i.test(content)) {
        statusAllerta = 'ROSSA';
        dettaglioAllerta = 'Allerta di livello massimo diramata per il territorio.';
      }
    } catch (e) {
      console.warn('⚠️ Errore durante lo scraping della Protezione Civile:', e.message);
    }

    // Se l'allerta non è verde, esegue i controlli per le scuole ad Aversa
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

  // Costruzione del messaggio per il riquadro giallo
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
