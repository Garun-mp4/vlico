// M4 safety cases with M5's stable, once-per-session invitation contract.
// Native UI assets, synthetic responses, no messages or Eva generations.
async original => {
  const origin = new URL(original.url()).origin;
  if (!['http://localhost:8000', 'https://vlico39.ru'].includes(origin)) throw Error('Open VLICO first');
  const results = [], assets = new Map();
  for (const mobile of [false, true]) {
    for (const scenario of ['disabled', 'changed', 'expired', 'network', 'plaintext', 'deadline', 'expires-before-show', 'unavailable']) {
      const context = await original.context().browser().newContext({
        viewport: {width: mobile ? 390 : 1440, height: 900}, isMobile: mobile, hasTouch: mobile, serviceWorkers: 'block',
      });
      let calls = 0, sends = 0;
      try {
        const page = await context.newPage();
        await page.clock.install();
        await page.addInitScript(() => {
          const random = crypto.getRandomValues.bind(crypto);
          crypto.getRandomValues = array => {
            if (array instanceof Uint32Array && array.length === 1) {array[0] = 4294967295; return array;}
            return random(array);
          };
        });
        let offer = {text: scenario === 'plaintext' ? '<img src=x onerror=alert(1)>' : 'Подбор света при заказе потолков.', expires_at: null};
        if (scenario === 'expired') offer.expires_at = new Date(Date.now() - 60000).toISOString();
        if (scenario === 'deadline') offer.expires_at = new Date(Date.now() + 15000).toISOString();
        if (scenario === 'expires-before-show') offer.expires_at = new Date(Date.now() + 1000).toISOString();
        let fail = scenario === 'network';
        await page.routeWebSocket('**/socket.io/**', socket => socket.close());
        await page.route('**/*', async route => {
          const url = new URL(route.request().url());
          if (route.request().method() !== 'GET') {sends++; return route.abort();}
          if (url.origin !== origin || url.pathname === '/socket.io/') return route.abort();
          if (url.pathname === '/api/chat-offer/') {
            calls++;
            return fail ? route.fulfill({status: 503}) : route.fulfill({json: offer});
          }
          if (url.pathname.startsWith('/widget/')) {
            if (scenario === 'unavailable') return route.abort();
            const asset = 'https://vlico39.ru' + url.pathname + url.search;
            if (!assets.has(asset)) assets.set(asset, original.request.get(asset, {headers: {cookie: ''}}));
            return route.fulfill({response: await assets.get(asset)});
          }
          if (url.pathname.startsWith('/api/dashboard/channels/config/')) return route.fulfill({json: {code: 200, data: {id: url.pathname.split('/').pop(), name: 'Артем', props: {}}}});
          if (url.pathname.startsWith('/api/dashboard/')) return route.fulfill({json: {code: 200, items: []}});
          return route.continue();
        });
        await page.goto(origin + '/', {waitUntil: 'domcontentloaded'});
        if (scenario !== 'unavailable') await page.locator('#chat-widget-container .chat-bar').waitFor({state: 'visible'});
        const accept = page.locator('[data-privacy-essential]');
        if (await accept.isVisible()) await accept.click();
        await page.clock.fastForward(6400);
        const invitation = page.locator('.vlico-chat-invitation');
        if (scenario === 'unavailable') {
          if (await invitation.isVisible()) throw Error('Invitation promotes an unavailable chat');
          if (!await page.locator('[data-vlico-chat-fallback]').isVisible()) throw Error('No form fallback');
        } else {
          await invitation.waitFor({state: 'visible'});
          const copy = invitation.locator('[data-chat-invitation-copy]');
          if (['expired', 'network', 'expires-before-show'].includes(scenario)) {
            if (await invitation.getAttribute('data-variant') === 'offer') throw Error('Invalid offer displayed');
          } else {
            if (await copy.textContent() !== offer.text) throw Error('Approved public copy missing');
            if (await copy.locator('img').count()) throw Error('HTML injection');
            const frozen = await copy.textContent();
            if (scenario === 'deadline') await page.clock.fastForward(16000);
            else {
              if (scenario === 'disabled') offer = {};
              else if (scenario === 'changed') offer = {text: 'Новая редакция приглашения', expires_at: null};
              else fail = true;
              await page.clock.fastForward(30100);
            }
            await invitation.waitFor({state: 'hidden'});
            if (await copy.textContent() !== frozen) throw Error('Invitation text replaced while reading');
            const stopped = calls;
            await page.clock.fastForward(60000);
            if (calls !== stopped) throw Error('Polling continues after retirement');
          }
        }
        if (sends) throw Error('A message was sent');
        results.push({mobile, scenario, passed: true, sends});
      } finally {
        await Promise.all(context.pages().map(page => page.unrouteAll({behavior: 'wait'})));
        await context.close();
      }
    }
  }
  return results;
}
