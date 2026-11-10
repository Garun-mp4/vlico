async page => {
  const base = /^https?:/.test(page.url()) ? new URL('/', page.url()).origin : 'http://127.0.0.1:8001';
  const checks = [];
  let estimateRequests = 0;
  page.on('request', request => {
    if (new URL(request.url()).pathname === '/api/calculate/') estimateRequests += 1;
  });

  async function checkEntry(path, width, height) {
    await page.setViewportSize({ width, height });
    await page.goto(base + path);
    const section = page.locator('.quick-calculator');
    await section.scrollIntoViewIfNeeded();
    const fields = section.locator('[data-quick-fields] [name]');
    if (new Set(await fields.evaluateAll(nodes => nodes.map(node => node.name))).size !== 3) throw new Error(`${path} at ${width}px does not have exactly three quick fields`);
    if (await section.locator('[data-configurator]').count()) throw new Error(`${path} still renders the legacy configurator`);
    if (await section.locator('[data-quick-result]').isVisible()) throw new Error(`${path} shows a result before user input`);
    if ((await section.innerText()).includes('₽')) throw new Error(`${path} displays a numeric price`);
    const geometry = await section.evaluate(node => ({ width: node.getBoundingClientRect().width, scrollWidth: node.scrollWidth }));
    if (geometry.scrollWidth > geometry.width + 1) throw new Error(`${path} overflows its ${width}px layout: ${JSON.stringify(geometry)}`);

    await page.locator('input[type="radio"][value="apartment"]').check();
    await page.getByLabel('Площадь потолка, м²').fill('24,5');
    await page.locator('input[type="radio"][value="classic"]').check();
    await section.getByRole('button', { name: 'Получить предварительный расчёт' }).click();
    await section.getByText('Для предварительного расчёта уточним детали.', { exact: true }).waitFor();
    if (!(await section.locator('[data-quick-contact]').isVisible())) throw new Error(`${path} did not reveal contact fields after the quote action`);
    if (await section.innerText().then(text => text.includes('₽'))) throw new Error(`${path} fabricated a price after the quote action`);
    await page.getByLabel('Площадь потолка, м²').fill('25');
    if (!(await section.locator('[data-quick-contact]').isHidden())) throw new Error(`${path} did not collapse the result after an answer changed`);
    if (await page.getByLabel('Площадь потолка, м²').inputValue() !== '25') throw new Error(`${path} discarded the changed area`);
    checks.push(`${path} ${width}x${height}: three fields, quote action, no amount, edit and preservation`);
  }

  for (const [path, width, height] of [
    ['/', 1440, 960], ['/calculator/', 1440, 960],
    ['/', 390, 844], ['/calculator/', 390, 844],
  ]) await checkEntry(path, width, height);
  if (estimateRequests) throw new Error(`The public flow called the v2 estimate API ${estimateRequests} times`);
  checks.push('No public interaction called /api/calculate/');

  await page.setViewportSize({ width: 1440, height: 960 });
  await page.goto(base + '/');
  const section = page.locator('.quick-calculator');
  await section.scrollIntoViewIfNeeded();
  await page.locator('input[type="radio"][value="house"]').check();
  await page.getByLabel('Площадь потолка, м²').fill('130');
  await page.locator('input[type="radio"][value="consultation"]').check();
  await section.getByRole('button', { name: 'Получить предварительный расчёт' }).click();
  await section.getByLabel('Как к вам обращаться').fill('M02 Browser Test');
  const contactField = section.getByLabel('Телефон, email или Telegram');
  const originalDescription = await contactField.getAttribute('aria-describedby');
  await contactField.fill('+7 900 000-00-02');
  await section.locator('input[name="consent"]').check();

  await page.route('**/api/leads/', route => route.abort('internetdisconnected'));
  await section.getByRole('button', { name: 'Передать ответы специалисту' }).click();
  await page.waitForFunction(() => document.querySelector('[data-lead-errors]')?.textContent.includes('Связь прервалась'));
  if (await section.getByLabel('Как к вам обращаться').inputValue() !== 'M02 Browser Test') throw new Error('Network failure discarded the visitor name');
  if (await section.getByLabel('Площадь потолка, м²').inputValue() !== '130') throw new Error('Network failure discarded the calculation answers');
  await page.unroute('**/api/leads/');
  checks.push('Network failure leaves contact and quick answers in the form');

  let validationRequests = 0;
  await page.route('**/api/leads/', async route => {
    validationRequests += 1;
    await route.fulfill({ status: 400, contentType: 'application/json', body: JSON.stringify({
      ok: false, errors: { contact: ['Укажите корректный контакт.'] },
    }) });
  });
  await section.getByRole('button', { name: 'Передать ответы специалисту' }).click();
  await page.waitForFunction(() => document.querySelector('#id_quick_contact')?.getAttribute('aria-invalid') === 'true');
  if (await section.getByLabel('Как к вам обращаться').inputValue() !== 'M02 Browser Test') throw new Error('Server validation discarded the visitor name');
  if (await section.getByLabel('Телефон, email или Telegram').inputValue() !== '+7 900 000-00-02') throw new Error('Server validation discarded the visitor contact');
  if (await section.getByLabel('Площадь потолка, м²').inputValue() !== '130') throw new Error('Server validation discarded the calculation answers');
  if (validationRequests !== 1) throw new Error(`Server validation made ${validationRequests} requests`);
  await contactField.fill('+7 900 000-00-03');
  if (await section.locator('[data-lead-errors]').isVisible()) throw new Error('Correcting the contact left a stale summary error visible');
  if (await contactField.getAttribute('aria-invalid')) throw new Error('Correcting the contact left aria-invalid set');
  if (await contactField.getAttribute('aria-describedby') !== originalDescription) throw new Error('Correcting the contact left a stale error description attached');
  await page.unroute('**/api/leads/');
  checks.push('Server validation marks the contact, preserves answers, and clears inline and summary errors on correction');

  let leadRequests = 0;
  await page.route('**/api/leads/', async route => {
    leadRequests += 1;
    await new Promise(resolve => setTimeout(resolve, 250));
    await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({
      ok: true, kind: 'calculator', reference: 'mocked-m02',
      message: 'Заявка принята. Мы свяжемся с вами по указанному контакту.',
    }) });
  });
  await section.getByRole('button', { name: 'Передать ответы специалисту' }).evaluate(button => { button.click(); button.click(); });
  await page.waitForFunction(() => document.querySelector('[data-lead-status]')?.textContent.includes('Заявка принята'));
  if (leadRequests !== 1) throw new Error(`Rapid double submit made ${leadRequests} lead requests`);
  const persisted = await page.evaluate(() => JSON.stringify({
    local: Object.fromEntries(Array.from({ length: localStorage.length }, (_, i) => { const key = localStorage.key(i); return [key, localStorage.getItem(key)]; })),
    session: Object.fromEntries(Array.from({ length: sessionStorage.length }, (_, i) => { const key = sessionStorage.key(i); return [key, sessionStorage.getItem(key)]; })),
  }));
  if (persisted.includes('M02 Browser Test') || persisted.includes('+7 900 000-00-02') || persisted.includes('130')) throw new Error('Personal data or quick answers were stored in browser storage');
  await page.unroute('**/api/leads/');
  checks.push('Rapid double submit makes one mocked request; no personal data or answers persist in browser storage');

  const browser = page.context().browser();
  const noJsContext = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  const noJsPage = await noJsContext.newPage();
  await noJsPage.goto(base + '/calculator/');
  const noJsSection = noJsPage.locator('.quick-calculator');
  await noJsSection.locator('input[type="radio"][value="house"]').check();
  await noJsSection.getByLabel('Площадь потолка, м²').fill('130');
  await noJsSection.locator('input[type="radio"][value="consultation"]').check();
  await noJsPage.locator('.quick-calculator').getByRole('button', { name: 'Получить предварительный расчёт' }).click();
  await noJsSection.getByText('Для предварительного расчёта уточним детали.', { exact: true }).waitFor();
  if (!(await noJsSection.locator('[data-quick-contact]').isVisible())) throw new Error('No-JS server response did not reveal the contact fields');
  if (await noJsSection.getByLabel('Площадь потолка, м²').inputValue() !== '130') throw new Error('No-JS quote did not preserve its answers');
  if ((await noJsSection.innerText()).includes('₽')) throw new Error('No-JS quote displayed a numeric amount');
  await noJsContext.close();
  checks.push('No-JS POST renders the honest result and preserves all three answers without creating a lead');

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(base + '/calculator/');
  const finalSection = page.locator('.quick-calculator');
  await finalSection.scrollIntoViewIfNeeded();
  await finalSection.locator('input[type="radio"][value="apartment"]').check();
  await finalSection.getByLabel('Площадь потолка, м²').fill('24,5');
  await finalSection.locator('input[type="radio"][value="designer_light"]').check();
  await finalSection.getByRole('button', { name: 'Получить предварительный расчёт' }).click();
  await finalSection.getByText('Для предварительного расчёта уточним детали.', { exact: true }).waitFor();
  return { checks, estimateRequests, leadRequests, finalUrl: page.url() };
}
