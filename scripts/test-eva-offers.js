// Run with playwright-cli run-code --filename=scripts/test-eva-offers.js on localhost:8000 or vlico39.ru.
// Synthetic HTTP responses; no messages or requests to the Eva assistant.
async original => {
  const origin = new URL(original.url()).origin;
  if (!['http://localhost:8000', 'https://vlico39.ru'].includes(origin)) throw Error('Open the VLICO local or production site first');
  const results = [];
  for (const mobile of [false, true]) {
    const context = await original.context().browser().newContext({
      viewport: { width: mobile ? 390 : 1440, height: 900 },
      isMobile: mobile, hasTouch: mobile, serviceWorkers: 'block',
    });
    try {
      const page = await context.newPage();
      await page.clock.install();
      let offer = { text: 'При заказе потолков поможем подобрать освещение.', expires_at: null };
      let fail = false;
      let calls = 0;
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route('**/*', route => {
        const url = new URL(route.request().url());
        if (url.origin !== origin || url.pathname.startsWith('/widget/') || url.pathname.startsWith('/socket.io/')) return route.abort();
        if (url.pathname === '/api/chat-offer/') {
          calls++;
          return fail ? route.fulfill({ status: 503 }) : route.fulfill({ json: offer });
        }
        if (route.request().method() !== 'GET') throw Error('Unexpected mutation');
        return route.continue();
      });
      await page.goto(origin + '/', { waitUntil: 'domcontentloaded' });
      const copy = page.locator('.vlico-chat-invitation [data-chat-invitation-copy]');
      await copy.waitFor({ state: 'attached' });
      const assertCopy = async expected => {
        try {
          await page.waitForFunction(expected => document.querySelector('.vlico-chat-invitation [data-chat-invitation-copy]')?.textContent === expected, expected, {timeout: 5000, polling: 50});
        } catch {
          throw Error(JSON.stringify({expected,actual:await copy.textContent(),calls,hidden:await page.evaluate(()=>document.hidden)}));
        }
      };
      const baseline = 'Помогу подобрать потолок и освещение. Бесплатная консультация — прямо сейчас.';
      await assertCopy(offer.text);
      const essential = page.locator('[data-privacy-essential]');
      if (await essential.isVisible()) await essential.click();
      await page.clock.fastForward(6100);
      await page.locator('.vlico-chat-invitation').waitFor({ state: 'visible' });
      if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw Error('Horizontal overflow');
      offer = {};
      // Stop just after the refresh interval, before its network timeout elapses.
      await page.clock.fastForward(24000);
      await assertCopy(baseline);
      offer = { text: 'Expired offer must not display', expires_at: new Date(Date.now() - 60000).toISOString() };
      await page.clock.fastForward(30000);
      await assertCopy(baseline);
      offer = { text: '<img src=x onerror=alert(1)>', expires_at: null };
      await page.clock.fastForward(30000);
      await assertCopy(offer.text);
      if (await copy.locator('img').count()) throw Error('Invitation HTML injection');
      fail = true;
      await page.clock.fastForward(30000);
      await assertCopy(baseline);
      await page.getByRole('button', { name: 'Закрыть приглашение' }).click();
      const before = calls;
      await page.clock.fastForward(60000);
      if (calls !== before) throw Error('Polling continued after dismissal');
      if (errors.length) throw Error(errors.join('; '));
      results.push({ mobile, checks: ['approved', 'six-second invitation', 'disabled', 'expired', 'plain text', 'network fallback', 'dismissal'], calls });
    } finally {
      await context.close();
    }
  }
  return results;
}
