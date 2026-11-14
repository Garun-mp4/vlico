// Real vendor UI assets, synthetic configuration and messages. No Eva generations.
async original => {
  const origin = new URL(original.url()).origin;
  if (!['http://localhost:8000', 'https://vlico39.ru'].includes(origin)) throw Error('Open VLICO first');
  const results = [];
  const assets = new Map();
  const verify = (value, label) => { if (!value) throw Error(label); };
  for (const mobile of [false, true]) {
    for (const [index, variant] of ['base', 'estimate', 'lighting', 'measurement', 'offer'].entries()) {
      const context = await original.context().browser().newContext({
        viewport: {width: mobile ? 390 : 1440, height: mobile ? 844 : 900},
        isMobile: mobile, hasTouch: mobile, serviceWorkers: 'block',
        reducedMotion: variant === 'measurement' ? 'reduce' : 'no-preference',
      });
      let sends = 0;
      const errors = [];
      try {
        const page = await context.newPage();
        page.on('pageerror', error => errors.push(error.message));
        await page.clock.install();
        await page.addInitScript(fraction => {
          const random = crypto.getRandomValues.bind(crypto);
          crypto.getRandomValues = array => {
            if (array instanceof Uint32Array && array.length === 1) { array[0] = Math.floor(fraction * 4294967296); return array; }
            return random(array);
          };
        }, (index + .5) / 5);
        await page.routeWebSocket('**/socket.io/**', socket => socket.close());
        await page.route('**/*', async route => {
          const url = new URL(route.request().url());
          if (route.request().method() !== 'GET') { sends++; return route.abort(); }
          if (url.origin !== origin || url.pathname === '/socket.io/') return route.abort();
          if (url.pathname === '/api/chat-offer/') return route.fulfill({json: {text: 'Подтверждённый подбор света при заказе потолков.', expires_at: null}});
          if (url.pathname.startsWith('/widget/')) {
            const asset = 'https://vlico39.ru' + url.pathname + url.search;
            if (!assets.has(asset)) assets.set(asset, original.request.get(asset, {headers: {cookie: ''}}));
            return route.fulfill({response: await assets.get(asset)});
          }
          if (url.pathname.startsWith('/api/dashboard/channels/config/')) return route.fulfill({json: {code: 200, data: {id: url.pathname.split('/').pop(), name: 'Артем', props: {}}}});
          if (url.pathname.startsWith('/api/dashboard/')) return route.fulfill({json: {code: 200, items: []}});
          return route.continue();
        });
        await page.goto(origin + '/', {waitUntil: 'domcontentloaded'});
        const launcher = page.locator('#chat-widget-container .chat-bar');
        await launcher.waitFor({state: 'visible'});
        const invitation = page.locator('.vlico-chat-invitation');
        verify(!await invitation.isVisible(), 'Invitation appeared on arrival');
        if (variant === 'base') {
          await page.clock.fastForward(6100);
          verify(!await invitation.isVisible(), 'Invitation over consent panel');
          const panel = await page.locator('[data-privacy-panel]').boundingBox();
          const button = await launcher.boundingBox();
          verify(button.y + button.height < panel.y, 'Launcher overlaps consent');
        }
        const essential = page.locator('[data-privacy-essential]');
        if (await essential.isVisible()) await essential.click();
        await page.clock.fastForward(6400);
        await invitation.waitFor({state: 'visible'});
        verify(await invitation.getAttribute('data-variant') === variant, 'Wrong invitation variant');
        verify((await invitation.innerText()).includes('ИИ-консультант VLICO'), 'Missing AI disclosure');
        verify(await invitation.locator('img').evaluate(el => el.complete && el.naturalWidth > 0), 'Avatar failed to load');
        const shown = await invitation.locator('[data-chat-invitation-copy]').textContent();
        await page.clock.fastForward(60000);
        verify(await invitation.locator('[data-chat-invitation-copy]').textContent() === shown, 'Visible copy rotated');
        if (variant === 'measurement') {
          verify(await invitation.evaluate(el => getComputedStyle(el).animationName) === 'none', 'Reduced motion ignored');
        }
        if (variant === 'base') {
          await page.clock.fastForward(300);
          await page.screenshot({path: `C:/Users/admin/AppData/Local/Temp/vlico-m5-${mobile ? 'mobile' : 'desktop'}-invitation.png`, animations: 'disabled'});
          const start = invitation.getByRole('link', {name: 'Получить консультацию'});
          if (mobile) await start.tap();
          else await start.click();
          const chat = page.locator('.chat-window:visible');
          await chat.waitFor({state: 'visible'});
          await page.clock.fastForward(350);
          const input = chat.locator('.message-input');
          verify(await input.isEditable(), 'Chat is not ready for input');
          verify(await chat.getAttribute('aria-label') === 'Артем · ИИ-консультант VLICO', 'Dialog has no accessible name');
          verify(await chat.locator('.vlico-chat-avatar').count() === 1, 'Header avatar duplicated or missing');
          verify(await chat.locator('h3').evaluate(el => getComputedStyle(el).fontFamily.includes('Manrope')), 'Heading font');
          verify(await input.evaluate(el => getComputedStyle(el).fontFamily.includes('IBM Plex Mono')), 'Body font');
          if (mobile) verify(await input.evaluate(el => parseFloat(getComputedStyle(el).fontSize)) >= 16, 'iOS input zoom');
          await chat.locator('.messages').evaluate(el => {
            const row = document.createElement('div'); row.className = 'message';
            const bubble = document.createElement('div'); bubble.className = 'message-bubble';
            bubble.textContent = 'Пример ответа для проверки оформления. Контакты для начала консультации не нужны.';
            row.append(bubble); el.replaceChildren(row);
          });
          verify(await chat.locator('.message-bubble').last().evaluate(el => getComputedStyle(el).backgroundColor) === 'rgb(235, 234, 231)', 'Assistant bubble color');
          if (mobile) {
            await chat.locator('.close-btn').focus();
            await page.keyboard.press('Shift+Tab');
            verify(await input.evaluate(el => el.getRootNode().activeElement === el), 'Mobile focus escaped the chat');
            await page.keyboard.press('Tab');
            verify(await chat.locator('.close-btn').evaluate(el => el.getRootNode().activeElement === el), 'Mobile focus loop');
            await page.evaluate(() => {
              Object.defineProperty(visualViewport, 'height', {configurable: true, get: () => 420});
              visualViewport.dispatchEvent(new Event('resize'));
            });
            await page.waitForTimeout(150);
            verify(await input.isVisible(), 'Compose area hidden with keyboard viewport');
            const panel = await chat.boundingBox(); const compose = await chat.locator('.chat-compose').boundingBox();
            verify(compose.y + compose.height <= panel.y + panel.height + 2, 'Compose area outside chat');
            await page.evaluate(() => { delete visualViewport.height; visualViewport.dispatchEvent(new Event('resize')); });
          }
          await page.screenshot({path: `C:/Users/admin/AppData/Local/Temp/vlico-m5-${mobile ? 'mobile' : 'desktop'}-chat.png`, animations: 'disabled'});
          if (mobile) await chat.locator('.close-btn').tap();
          else {
            await chat.locator('.close-btn').focus();
            await page.keyboard.press('Escape');
          }
          await page.clock.fastForward(350);
          await chat.waitFor({state: 'hidden'});
          verify(await launcher.evaluate(el => el.getRootNode().activeElement === el), 'Focus did not return to launcher');
          if (mobile) {
            const sticky = page.locator('[data-home-sticky-cta]');
            await sticky.evaluate(el => {el.hidden = false;});
            await page.waitForTimeout(50);
            const panel = await sticky.boundingBox(); const button = await launcher.boundingBox();
            verify(panel && button.y + button.height < panel.y, 'Launcher overlaps sticky action');
            await sticky.evaluate(el => {el.hidden = true;});
          }
          await page.goto(origin + '/contacts/', {waitUntil: 'domcontentloaded'});
          await page.clock.fastForward(7000);
          verify(await page.locator('.vlico-chat-invitation').count() === 0, 'Invitation repeated after navigation');
        } else {
          if (variant === 'estimate') await page.locator('input[name="name"]').last().focus();
          else if (mobile && variant === 'lighting') await invitation.getByRole('button', {name: 'Закрыть приглашение'}).tap();
          else {
            await invitation.getByRole('button', {name: 'Закрыть приглашение'}).focus();
            await page.keyboard.press('Escape');
          }
          verify(!await invitation.isVisible(), 'Invitation did not dismiss by keyboard');
          await page.reload({waitUntil: 'domcontentloaded'});
          await page.clock.fastForward(7000);
          verify(await page.locator('.vlico-chat-invitation').count() === 0, 'Invitation repeated after reload');
        }
        verify(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), 'Horizontal overflow');
        verify(sends === 0, 'A message was sent');
        verify(errors.length === 0, errors.join('; '));
        results.push({mobile, variant, sends, passed: true});
      } finally {
        await Promise.all(context.pages().map(page => page.unrouteAll({behavior: 'wait'})));
        await context.close();
      }
    }
  }
  return results;
}
