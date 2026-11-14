async page => {
  const origin = new URL(page.url()).origin;
  if (!/^https?:\/\//.test(origin)) throw Error('Open the VLICO site in Playwright first.');

  const context = await page.context().browser().newContext({
    viewport: { width: 1440, height: 900 },
    serviceWorkers: 'block',
  });
  try {
    const diagnostic = await context.newPage();
    const marker = 'VLICO_TEST_M0_FAULT';
    const isHook = url => new URL(url).pathname.startsWith('/api/dashboard/channels/hook/');
    let injectedRequests = 0;

    await diagnostic.route('**/*', async route => {
      const request = route.request();
      const url = new URL(request.url());
      if (url.origin !== origin) return route.abort();
      if (request.method() === 'POST' && isHook(url)) {
        injectedRequests++;
        // Match the relay timeout for the widget's message POST without sending it to Eva.
        await new Promise(resolve => setTimeout(resolve, 12000));
        return route.fulfill({ status: 502, body: '' });
      }
      if (request.method() !== 'GET' || ['/socket.io/', '/api/dashboard/messages'].includes(url.pathname)) return route.abort();
      return route.continue();
    });
    await diagnostic.routeWebSocket('**/socket.io/**', socket => socket.close());

    await diagnostic.goto(origin + '/', { waitUntil: 'domcontentloaded', timeout: 15000 });
    const essential = diagnostic.locator('[data-privacy-essential]');
    if (await essential.isVisible()) await essential.click();
    await diagnostic.locator('#chat-widget-container .chat-bar').click({ timeout: 15000 });

    const chat = diagnostic.locator('.chat-window:visible');
    const input = chat.locator('.message-input');
    const send = chat.locator('.send-btn');
    const snapshot = async () => ({
      composerEnabled: await input.isEditable(),
      sendEnabled: await send.isEnabled(),
      draftIntact: await input.inputValue() === marker,
      sentBubbleCount: await chat.locator('.message.user .message-text').filter({ hasText: marker }).count(),
      errorVisible: await chat.getByText(/ошиб|попробуйте|не удалось|error|failed/i).filter({ visible: true }).count() > 0,
    });

    await input.fill(marker);
    const started = Date.now();
    const [, pending] = await Promise.all([
      diagnostic.waitForResponse(response => response.status() === 502 && isHook(response.url()), { timeout: 17000 }),
      send.click({ timeout: 5000 }).then(snapshot),
    ]);
    const responseMs = Date.now() - started;
    await input.evaluate(element => new Promise(resolve => requestAnimationFrame(resolve)));
    return { responseMs, injectedRequests, pending, after502: await snapshot() };
  } finally {
    await context.close();
  }
}
