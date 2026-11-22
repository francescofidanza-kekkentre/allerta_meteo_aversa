// Worker "allerta-meteo-cron": ogni 30 minuti avvia il workflow GitHub che
// aggiorna alert.json. Gli orari pianificati di GitHub Actions vengono spesso
// ritardati di ore; il timer di Cloudflare invece è puntuale.
//
// Segreto richiesto: GITHUB_TOKEN (fine-grained token, solo questo repository,
// permesso "Actions: Read and write").

const REPO = 'francescofidanza-kekkentre/allerta_meteo_aversa';
const WORKFLOW = 'update-alert.yml';

export default {
  async scheduled(controller, env, ctx) {
    if (!env.GITHUB_TOKEN) {
      console.error('GITHUB_TOKEN mancante: impostalo nei segreti del Worker.');
      return;
    }
    const res = await fetch(
      `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${env.GITHUB_TOKEN}`,
          Accept: 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28',
          'User-Agent': 'allerta-meteo-cron',
        },
        body: JSON.stringify({ ref: 'main' }),
      },
    );
    if (res.status === 204) {
      console.log(`Workflow ${WORKFLOW} avviato (${controller.cron}).`);
    } else {
      // Un errore qui fa risultare fallita l'esecuzione nei log del Worker.
      throw new Error(`GitHub ha risposto ${res.status}: ${await res.text()}`);
    }
  },
};
