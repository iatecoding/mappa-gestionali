/* Rende le immagini social (Poster 1200x1200) da scripts/social/*.html.
   Requisiti: node + playwright-core (browser Chromium di playwright già installato).
   Uso: node scripts/social/render_social.js  (serve un http server sul root del repo) */
const path = require('path');
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');

const BASE = process.env.SOCIAL_BASE_URL || 'http://127.0.0.1:8124';
const EXEC = process.env.CHROMIUM_PATH || undefined;

const JOBS = [
  { page: 'scripts/social/reddit-mercato.html', out: 'web/social/reddit-mercato.png' },
  { page: 'scripts/social/reddit-hardware.html', out: 'web/social/reddit-hardware.png' }
];

(async () => {
  const browser = await chromium.launch(EXEC ? { executablePath: EXEC } : {});
  const page = await browser.newPage({ viewport: { width: 1200, height: 1200 }, deviceScaleFactor: 2 });
  for (const job of JOBS) {
    await page.goto(`${BASE}/${job.page}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(300);
    await page.screenshot({ path: job.out, clip: { x: 0, y: 0, width: 1200, height: 1200 } });
    console.log('scritto', job.out);
  }
  await browser.close();
})();
