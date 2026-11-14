async original => {
  const strictEqual = (actual, expected, label) => {
    if (actual !== expected) throw Error(`${label}: ${JSON.stringify(actual)} !== ${JSON.stringify(expected)}`);
  };
  const origin = new URL(original.url()).origin;
  const vendor = 'https://vlico39.ru';
  const conversationId = '11111111-1111-4111-8111-111111111111';
  const sample = 'Тестовый адрес и контакт';
  const launches = [];

  for (const mobile of [false, true]) {
    const context = await original.context().browser().newContext({
      viewport: { width: mobile ? 390 : 1440, height: mobile ? 750 : 900 },
      isMobile: mobile, hasTouch: mobile, serviceWorkers: 'block',
    });
    try {
      const page = await context.newPage();
      const entries = [];
      let requests = 0;
      let historyReads = 0;
      let failure = 'accepted';
      let channelId;
      let accountId;
      let clockOffset = 0;
      const makeMessage = (text, senderType) => ({
        id: String(entries.length + 1), text, senderType, conversationId, channelId,
        createdAt: new Date(Date.now() + clockOffset).toISOString(), attachments: [],
      });
      const emit = async (text, senderType) => {
        const message = makeMessage(text, senderType);
        entries.push(message);
        await page.evaluate(({ key, id, item }) => {
          localStorage.setItem(`${key}-conversation-id`, id);
          const historyKey = `${key}-chat-widget-messages`;
          const history = JSON.parse(localStorage.getItem(historyKey) || '[]');
          history.push({ id: item.id, text: item.text, createdAt: item.createdAt, isUser: item.senderType === 'user' });
          localStorage.setItem(historyKey, JSON.stringify(history));
          const signal = document.createComment('Eva rendered an update');
          document.querySelector('#chat-widget-container').shadowRoot.append(signal);
          signal.remove();
        }, { key: `${accountId}-${channelId}`, id: conversationId, item: message });
      };
      await page.routeWebSocket('**/socket.io/**', socket => socket.close());
      await page.route('**/*', async route => {
        const request = route.request();
        const url = new URL(request.url());
        if (url.origin !== origin) return route.abort();
        const path = url.pathname;
        if (path === '/socket.io/') return route.abort();
        if (path === '/api/dashboard/messages') {
          historyReads++;
          return route.fulfill({ json: { code: 200, items: entries } });
        }
        if (path.startsWith('/api/dashboard/channels/hook/')) {
          requests++;
          ({ message: { accountId } } = request.postDataJSON());
          await new Promise(resolve => setTimeout(resolve, failure === 'unsafe' ? 12000 : 400));
          if (failure === 'rejected') return route.fulfill({ status: mobile ? 200 : 422, json: { code: 422 } });
          if (failure === 'offline') return route.abort('internetdisconnected');
          if (failure === 'unsafe') return route.fulfill({ status: 502, body: '' });
          return route.fulfill({ status: 200, body: 'ok', contentType: 'text/plain' });
        }
        if (request.method() !== 'GET') return route.abort();
        if (path.startsWith('/api/dashboard/channels/config/')) {
          channelId = path.split('/').pop();
          return route.fulfill({ json: { code: 200, data: { id: channelId, name: 'Артем', props: {} } } });
        }
        if (path.startsWith('/widget/')) {
          // Real vendor assets via SpaceWeb. Docker on this host cannot negotiate upstream TLS.
          const response = await route.fetch({ url: vendor + path + url.search, timeout: 10000 });
          return route.fulfill({ response });
        }
        return route.continue();
      });
      await page.goto(origin + '/', { waitUntil: 'domcontentloaded' });
      const essential = page.locator('[data-privacy-essential]');
      if (await essential.isVisible()) await essential.click();
      await page.clock.install();
      const launcher = page.locator('#chat-widget-container .chat-bar');
      await launcher.click();
      const chat = page.locator('.chat-window:visible');
      const input = chat.locator('.chat-compose .message-input');
      const send = chat.locator('.send-btn');
      const notice = chat.locator('.vlico-chat-delivery');
      const check = notice.getByRole('button', { name: 'Проверить доставку' });
      const state = async text => {
        await notice.getByRole('status').getByText(text, { exact: true }).waitFor({ timeout: 5000 });
      };

      await input.fill(sample);
      await send.dblclick();
      await state('Отправляем сообщение…');
      await state('Сообщение принято. Ждём ответ…');
      strictEqual(requests, 1, 'double click');
      await page.clock.fastForward(25000);
      clockOffset += 25000;
      await state('Сообщение принято. Ответ пока не пришёл.');
      strictEqual(await input.isEditable(), true, 'waiting for an answer does not block composing');
      await emit(sample, 'user');
      await emit('Ответ для проверки', 'assistant');
      await notice.waitFor({ state: 'hidden' });

      failure = 'rejected';
      await input.fill('После явного отказа');
      await input.press('Enter');
      await state('Не удалось отправить сообщение. Попробуйте ещё раз.');
      strictEqual(await input.inputValue(), 'После явного отказа', 'rejected draft');
      failure = 'accepted';
      await send.click();
      await state('Сообщение принято. Ждём ответ…');
      strictEqual(requests, 3, 'manual retry after rejection');
      await emit('После явного отказа', 'user');
      await emit('Ответ на повтор', 'assistant');
      await notice.waitFor({ state: 'hidden' });

      failure = mobile ? 'offline' : 'unsafe';
      await input.fill(sample);
      await send.click();
      await state('Отправляем сообщение…');
      await notice.getByText('Не удалось подтвердить доставку. Проверьте переписку перед повтором.', { exact: true }).waitFor({ timeout: 15000 });
      strictEqual(await input.inputValue(), sample, 'uncertain draft');
      const fits = await chat.evaluate(element => element.scrollWidth <= element.clientWidth + 1);
      strictEqual(fits, true, 'status at available width');
      await check.click();
      await state('Доставка пока не подтверждена. Если нужен ответ, оставьте заявку через форму.');
      await send.click();
      await state('Доставка пока не подтверждена. Если нужен ответ, оставьте заявку через форму.');
      strictEqual(requests, 4, 'no duplicate POST while delivery is unknown');
      strictEqual(historyReads, 2, 'both checks use the known conversation history');

      await chat.getByRole('button', { name: 'Закрыть чат' }).click();
      await launcher.click();
      await state('Доставка пока не подтверждена. Если нужен ответ, оставьте заявку через форму.');
      strictEqual(await input.inputValue(), sample, 'draft survives closing and reopening the chat');
      entries.push(makeMessage(sample, 'user'));
      await check.click();
      await state('Сообщение принято.');
      strictEqual(requests, 4, 'history confirms the original POST without resending');

      failure = 'accepted';
      await input.fill('Следующий вопрос');
      await send.click();
      await state('Сообщение принято. Ждём ответ…');
      strictEqual(requests, 5, 'continue the conversation after reconnect');
      launches.push({ mobile, requests, historyReads });
    } finally {
      await context.close();
    }
  }
  return launches;
}
