async page => {
  const base = 'http://127.0.0.1:8000';
  const check = (condition, message) => { if (!condition) throw Error(message); };
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(base + '/contacts/');
  await page.evaluate(() => {
    const version = JSON.parse(document.getElementById('site-config').textContent).consent_version;
    localStorage.setItem('vlicoPrivacy', JSON.stringify({ version, expires: Date.now() + 86400000, analytics: false, external: false }));
  });
  const routes = ['/services/', '/services/shadow/', '/services/floating/', '/services/light-lines/', '/services/tracks/', '/services/cornices/', '/services/fabric/', '/partners/', '/contacts/', '/privacy/', '/consent/', '/cookies/'];
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of routes) {
      const response = await page.goto(base + path);
      check(response.status() === 200, path + ' did not load');
      check(await page.locator('h1').count() === 1, path + ' needs exactly one H1');
      check(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), path + ' overflows at ' + width);
      check((await page.locator('iframe').count() > 0) === (path === '/contacts/'), 'Unexpected widget presence');
      check(await page.locator('script[src*="mc.yandex.ru"]').count() === 0, 'Local analytics loaded');
      check(await page.locator('img').evaluateAll(async images => (await Promise.all(images.map(async img => { img.loading = 'eager'; try { await img.decode(); return img.naturalWidth > 0; } catch { return false; } }))).every(Boolean)), path + ' has broken images');
    }
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(base + '/services/shadow/');
  await page.getByRole('link', { name: 'Обсудить решение ↗', exact: true }).click();
  check(await page.locator('select[name=service] option:checked').innerText() === 'Теневые потолки', 'Service context was lost');
  await page.goto(base + '/partners/');
  await page.getByRole('link', { name: 'Отправить проект ↗', exact: true }).click();
  check(await page.locator('[name=kind]').inputValue() === 'partner', 'Partner CTA picked wrong lead kind');
  check(await page.locator('[name=interest]').inputValue() === 'Сотрудничество', 'Partner context was lost');

  // Use the real served HTML and site.js, but intercept the vendor library and intake.
  // No statistics or notifications leave this browser test.
  await page.addInitScript(() => { window.__metricCalls = []; window.ym = (...args) => window.__metricCalls.push(args); });
  let vendorRequests = 0;
  let heldVendor, vendorReady;
  const vendorRequested = new Promise(resolve => { vendorReady = resolve; });
  await page.route('https://mc.yandex.ru/**', route => { vendorRequests++; heldVendor = route; vendorReady(); });
  await page.route('**/request/consultation/**', async route => {
    const response = await route.fetch();
    await route.fulfill({ response, body: (await response.text()).replace('"analytics_enabled": false', '"analytics_enabled": true') });
  });
  await page.goto(base + '/request/consultation/?contact=private-query@example.test');
  check(vendorRequests === 0, 'Analytics ignored refusal');
  await page.locator('[data-privacy-open]').last().click();
  await page.getByRole('button', { name: 'Принять', exact: true }).click();
  await vendorRequested;
  check(vendorRequests === 1, 'Analytics script loaded more than once');
  const reference = await page.evaluate(() => crypto.randomUUID());
  let submissions = 0;
  await page.route('**/api/leads/', route => {
    submissions++;
    return route.fulfill({ status: submissions === 1 ? 400 : 201, contentType: 'application/json', body: JSON.stringify(submissions === 1 ? { ok: false, errors: { contact: ['Проверьте контакт'] } } : { ok: true, kind: 'consultation', reference, message: 'Заявка сохранена.' }) });
  });
  const form = page.locator('[data-lead-form]');
  await form.locator('[name=name]').fill('QA private name');
  await form.locator('[name=contact]').fill('private-contact@example.test');
  await form.locator('[name=comment]').fill('private-comment');
  await form.locator('[name=consent]').check();
  await form.locator('button[type=submit]').click();
  await page.getByText('Проверьте контакт', { exact: true }).first().waitFor();
  check((await page.evaluate(() => window.__metricCalls.filter(call => call[1] === 'reachGoal').length)) === 0, 'Failed request counted as success');
  await form.locator('button[type=submit]').click();
  await page.waitForFunction(() => document.querySelector('[data-lead-form]').dataset.submitted === 'true');
  await heldVendor.fulfill({ contentType: 'text/javascript', body: '/* intercepted slow analytics library */' });
  await page.waitForFunction(() => window.__metricCalls.some(call => call[1] === 'hit'));
  await page.evaluate(reference => {
    for (let i = 0; i < 2; i++) document.dispatchEvent(new CustomEvent('vlico:lead-saved', { detail: { kind: 'consultation', reference } }));
  }, reference);
  const calls = await page.evaluate(() => window.__metricCalls);
  check(calls.filter(call => call[1] === 'reachGoal' && call[2] === 'lead_consultation').length === 1, 'Duplicate or missing conversion');
  check(calls.filter(call => call[1] === 'reachGoal' && call[2] === 'lead_success').length === 1, 'Generic success goal is missing');
  const serialized = JSON.stringify(calls);
  for (const sensitive of ['QA private name', 'private-contact', 'private-comment', 'private-query', reference]) check(!serialized.includes(sensitive), 'Analytics leaked ' + sensitive);
  await page.locator('[data-privacy-open]').last().click();
  await page.getByRole('button', { name: 'Отклонить', exact: true }).click();
  check(await page.evaluate(() => window.__metricCalls.some(call => call[1] === 'destruct')), 'Analytics did not stop');
  check(await page.locator('script[src*="mc.yandex.ru"]').count() === 0, 'Analytics script was not removed');
  await page.unroute('**/request/consultation/**'); await page.unroute('**/api/leads/'); await page.unroute('https://mc.yandex.ru/**');
  check(!errors.length, errors.join('; '));
  return { pages: routes.length, widths: [1440, 390, 320], context: 'service and partner passed', analytics: 'opt-in, errors, success, deduplication, privacy and revocation passed', errors };
}
