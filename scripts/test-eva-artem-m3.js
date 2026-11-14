async original => {
  const origin = new URL(original.url()).origin;
  if (origin !== 'https://vlico39.ru') throw Error('Open https://vlico39.ru before running the authorised live check.');
  const scenarios = [
    {
      name: 'pricing',
      messages: [
        'VLICO_TEST_M3. Сколько примерно стоит матовый потолок 25 м² без освещения?',
        'Для другого объекта 60 м² MSD Premium — какой базовый ориентир без света?',
        'VLICO_TEST_M3_ITEMS. Для комнаты 25 м² сколько отдельно полотно MSD Premium и алюминиевый профиль?',
        'Периметр этой комнаты 20 погонных метров.',
        'А для другой комнаты 15 м² какой общий базовый ориентир и минимальный заказ?',
        'Для тканевого потолка есть подтверждённая цена за м²?',
      ],
    },
    {
      name: 'measurement',
      messages: [
        'VLICO_TEST_M3. Хочу замер сегодня в 16:00 в Калининграде, район Сельма. Ответьте здесь, в чате.',
        'Сколько времени обычно занимает сам замер?',
      ],
    },
  ];
  const results = [];
  for (const scenario of scenarios) {
    const context = await original.context().browser().newContext({
      viewport: { width: 1440, height: 900 }, serviceWorkers: 'block',
    });
    try {
      const page = await context.newPage();
      await page.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
      await page.goto(origin + '/', { waitUntil: 'domcontentloaded' });
      const essential = page.locator('[data-privacy-essential]');
      if (await essential.isVisible()) await essential.click();
      await page.locator('#chat-widget-container .chat-bar').click({ timeout: 15000 });
      const chat = page.locator('.chat-window:visible');
      const input = chat.locator('.message-input');
      const assistant = chat.locator('.message:not(.user) .message-text');
      for (const question of scenario.messages) {
        const before = await assistant.count();
        await input.fill(question);
        const start = Date.now();
        await chat.locator('.send-btn').click();
        await assistant.nth(before).waitFor({ state: 'visible', timeout: 90000 });
        results.push({ scenario: scenario.name, question, answer: await assistant.nth(before).innerText(), replyMs: Date.now() - start });
      }
    } catch (error) {
      results.push({ scenario: scenario.name, error: String(error).split('\n')[0] });
      return results;
    } finally {
      await context.close();
    }
  }
  return results;
}
