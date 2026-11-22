# Pubblicazione su Google Play

Sito servito da Cloudflare Pages: https://allerta-meteo-aversa.pages.dev
Pacchetto Android: `dev.pages.allerta_meteo_aversa.twa`

## 1. Generare il pacchetto Android (ultima: versione 3 / 1.2.0)

Il sito riconosce l'app dal referrer `android-app://dev.pages.allerta_meteo_aversa.twa`,
quindi l'URL di avvio deve essere semplicemente `/`.
Il vecchio codice `?app_license=...` non è più accettato: il pacchetto del 10/11/2026
(versionCode 1) mostra la schermata di acquisto ed è stato sostituito.

Le modifiche al sito (testi, grafica, allerte) arrivano da sole all'app installata:
serve un nuovo pacchetto solo se cambiano nome/icona sul telefono, indirizzo di avvio,
versione minima di Android o chiave di firma.

**Opzione A – PWABuilder (come la prima volta)**
1. Apri https://www.pwabuilder.com, inserisci `https://allerta-meteo-aversa.pages.dev`.
2. Package for stores → Android → Options:
   - Package ID: `dev.pages.allerta_meteo_aversa.twa`
   - Version code: `3`, Version name: `1.2.0`
   - URL di avvio: `/` (senza `?app_license`)
   - Signing key: **Use mine** → carica `signing.keystore` della cartella
     "Meteo Aversa - Google Play package" (alias `my-key-alias`, password in `signing-key-info.txt`).
3. Carica il nuovo `.aab` in Play Console.

**Opzione B – Bubblewrap (dal terminale)**
Serve JDK 17 + Android SDK (Bubblewrap li scarica alla prima esecuzione).
```
cd android
bubblewrap update --skipVersionUpgrade
bubblewrap build
```
La configurazione è in `android/twa-manifest.json`; la keystore resta fuori dal repo.
A ogni nuova versione incrementa `appVersionCode`.

## 2. Collegare la chiave di firma di Google Play (assetlinks) – FATTO

`.well-known/assetlinks.json` contiene già le impronte della chiave di upload e della chiave
con cui Google Play firma davvero l'app installata (`F3:FE:20…:D1:6D`).
Senza l'impronta giusta l'app installata dallo store mostra la barra degli indirizzi di Chrome.

Da rifare solo se Google cambia la chiave di firma:
1. Play Console → l'app → Test e rilascio → Configurazione → **Integrità dell'app** → Firma dell'app.
2. Copia "Impronta del certificato SHA-256" della **chiave di firma dell'app**.
3. Aggiungila a `sha256_cert_fingerprints` in `.well-known/assetlinks.json`.
4. Verifica (deve rispondere `"linked": true`):
   `https://digitalassetlinks.googleapis.com/v1/assetlinks:check?source.web.site=https://allerta-meteo-aversa.pages.dev&relation=delegate_permission/common.handle_all_urls&target.android_app.package_name=dev.pages.allerta_meteo_aversa.twa&target.android_app.certificate.sha256_fingerprint=<IMPRONTA>`

## 3. Scheda dello store

File pronti in questa cartella:
- `icon-512.png` – icona dell'app (512×512)
- `feature-graphic.png` – grafica in evidenza (1024×500)

**Screenshot (già caricati in Play Console, in quest'ordine):** cartella `screenshots/`, 1080×2160
1. `04-fenomeni-meteo.png` – allerta verde con fenomeni meteo previsti
2. `01-meteo-allerta.png` – meteo e allerta
3. `02-grafico-temperature.png` – grafico orario
4. `03-previsioni-48h.png` – previsioni 48 ore

Dichiarazione asset AI: "Non etichettare gli asset" (sono screenshot reali dell'app).

**Nome (max 30):** Aversa Scuola & Allerte

**Descrizione breve (max 80):**
Allerte meteo, chiusura scuole e previsioni per Aversa e l'agro aversano.

**Descrizione completa:**
```
Aversa Scuola & Allerte riunisce in un'unica schermata le informazioni utili ogni mattina a chi vive ad Aversa e nell'agro aversano.

• Allerta meteo per la Zona 1 (Piana Campana), aggiornata dai bollettini pubblici della Protezione Civile
• Stato delle scuole di Aversa, con link all'avviso o all'ordinanza del Comune quando presente
• Meteo attuale: temperatura, vento, umidità, minime e massime
• Grafico orario della temperatura con cursore e probabilità di pioggia
• Previsioni per i prossimi giorni
• Nessun account, nessuna pubblicità, nessun dato personale raccolto

Dati meteo: Open-Meteo. Allerte: bollettini pubblici della Protezione Civile (Centro Funzionale Regione Campania e Dipartimento nazionale). Scuole: atti pubblici del Comune di Aversa.

App indipendente: non è affiliata né approvata dalla Protezione Civile, dalla Regione Campania o dal Comune di Aversa. In caso di emergenza fai sempre riferimento ai canali ufficiali.
```

**Categoria:** Meteo
**Email di contatto:** quella già indicata nella privacy policy
**Privacy policy:** https://allerta-meteo-aversa.pages.dev/privacy.html

## 4. Moduli di Play Console

**Sicurezza dei dati**
- L'app raccoglie o condivide dati utente? **No**
  (salva sul dispositivo solo un indicatore di sblocco, che non lascia il telefono;
  le richieste a Open-Meteo non contengono dati personali, la posizione è fissa su Aversa)
- Crittografia in transito: **Sì** (solo HTTPS)
- Eliminazione dati: non applicabile (nessun account)

**Classificazione dei contenuti:** questionario IARC → categoria "Utilità/Altro", nessun contenuto sensibile.
**Pubblico di destinazione:** 18+ oppure 13+ (evita "bambini": richiederebbe le norme Famiglie).
**Annunci:** No.
**App governative:** No (l'app non è sviluppata per conto di un ente pubblico).
**Funzionalità relative a notizie/informazioni governative:** dichiara che mostra informazioni pubbliche
e indica le fonti sopra elencate.
