async page => {
  const check = (value, message) => { if (!value) throw Error(message); };
  const pageOrigin = new URL(page.url()).origin;
  const origin = pageOrigin === 'null' ? 'http://127.0.0.1:8000' : pageOrigin;
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));

  const viewports = [
    { name: 'desktop', width: 1440, height: 1000 },
    { name: 'tablet', width: 820, height: 1024 },
    { name: 'mobile', width: 390, height: 844 },
  ];
  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto(origin + '/', {waitUntil:'domcontentloaded'});
    if (await page.locator('[data-privacy-panel]').isVisible()) {
      await page.getByRole('button', { name: 'Отклонить', exact: true }).click();
    }
    check((await page.locator('.partners-home-entry > a').innerText()).replace(/\s+/g, ' ').trim() === 'Стать партнёром ↗', 'Homepage partner entry is missing at ' + viewport.name);
    check(await page.getByRole('link', { name: 'Обсудить проект', exact: true }).count() > 0, 'Primary project action is missing at ' + viewport.name);
    await page.evaluate(() => document.querySelector('.partners-home-entry > a')?.focus({ preventScroll: true }));
    check(await page.evaluate(() => document.activeElement === document.querySelector('.partners-home-entry > a')), 'Homepage partner entry cannot receive keyboard focus at ' + viewport.name);
    await page.locator('.partners-home-entry > a').click();

    check(await page.locator('h1').textContent() === 'Партнёрство, в котором продумана каждая деталь', 'Partner heading mismatch at ' + viewport.name);
    check((await page.locator('.partners-intro .page-intro').innerText()).includes('Сотрудничаем с дизайнерами, архитекторами и строительными компаниями.'), 'Partner introduction is missing at ' + viewport.name);
    check(await page.locator('.partners-benefit-list li').count() === 4, 'Partner benefits count mismatch at ' + viewport.name);
    check(await page.locator('.partners-step-list li').count() === 3, 'Partner process count mismatch at ' + viewport.name);
    check(await page.getByRole('link', { name: /Обсудить сотрудничество/ }).first().getAttribute('href') === '#partner-form', 'Partner CTA does not open the SSR route');
    check(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), 'Horizontal overflow at ' + viewport.name);
    await page.screenshot({ path: 'C:/Users/admin/AppData/Local/Temp/vlico-m04-partners-' + viewport.name + '.png', fullPage: true });

    await page.goto(origin + '/request/partner/', {waitUntil:'domcontentloaded'});
    const form = page.locator('[data-lead-form]');
    check(await form.getAttribute('enctype') === 'multipart/form-data', 'Partner form is not multipart');
    check(await form.locator('[name=company]').count() === 1, 'Optional company field is missing');
    check(await form.locator('[name=attachment]').count() === 1, 'Optional project file is missing');
    check(await form.locator('[name=name]').getAttribute('required') !== null, 'Partner name is not required in the browser');
    check(await form.locator('[name=contact]').getAttribute('required') !== null, 'Partner phone is not required in the browser');
    check(await form.locator('[name=company]').getAttribute('required') === null, 'Company is not optional');
    check(await form.locator('[name=attachment]').getAttribute('required') === null, 'Project file is not optional');
    check((await form.locator('label[for=id_name]').innerText()).includes('обязательно'), 'Required name hint is missing');
    check((await form.locator('label[for=id_contact]').innerText()).includes('обязательно'), 'Required phone hint is missing');
    check((await form.locator('label[for=id_company]').innerText()).includes('необязательно'), 'Optional company hint is missing');
    check((await form.locator('label[for=id_attachment]').innerText()).includes('необязательно'), 'Optional file hint is missing');
    await form.locator('[name=contact]').focus();
    check(await page.evaluate(() => document.activeElement === document.querySelector('[name=contact]')), 'Phone field cannot receive keyboard focus');
    check(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), 'Partner form overflows horizontally at ' + viewport.name);
  }

  let requests = 0;
  let retriedPayload = '';
  await page.route('**/api/leads/', async route => {
    requests += 1;
    const body = route.request().postData() || '';
    if (requests === 1) return route.abort('failed');
    if (requests === 2) return route.fulfill({
      status: 400,
      contentType: 'application/json',
      body: JSON.stringify({ ok: false, errors: { attachment: ['Прикрепите проект в формате PDF, JPG или PNG.'] } }),
    });
    retriedPayload = body;
    return route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, kind: 'partner', reference: 'browser-test-only', message: 'Спасибо! Ваша заявка успешно отправлена. Наш специалист свяжется с вами в ближайшее время.' }),
    });
  });
  const form = page.locator('[data-lead-form]');
  await form.locator('[name=name]').fill('Тестовый дизайнер');
  await form.locator('[name=contact]').fill('+7 900 000-00-02');
  await form.locator('[name=company]').fill('Studio North');
  await form.locator('[name=attachment]').setInputFiles({ name: 'project.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\nUI-only fixture') });
  await form.locator('[name=consent]').check();
  await form.locator('button[type=submit]').click();
  await page.waitForFunction(() => document.querySelector('[data-lead-errors]')?.innerText.includes('Связь прервалась'));
  check(await form.getAttribute('data-submitted') !== 'true', 'Network failure incorrectly marked the partner form as submitted');
  check(await form.locator('[name=attachment]').isEnabled(), 'Network failure cleared or disabled the selected file');

  await form.locator('button[type=submit]').click();
  await form.locator('[data-field-error]').waitFor({ state: 'visible' });
  const attachment = form.locator('[name=attachment]');
  const attachmentError = form.locator('[data-field-error]');
  check(await attachment.getAttribute('aria-invalid') === 'true', 'Server validation did not associate the error with the attachment field');
  const describedBy = await attachment.getAttribute('aria-describedby');
  check(describedBy?.includes(await attachmentError.getAttribute('id')), 'Server validation did not connect the attachment to its error text');
  await attachment.setInputFiles({ name: 'revised-project.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\nUI-only fixture') });
  check(await form.locator('[data-field-error]').count() === 0, 'Editing the attachment left its stale server error visible');
  check(!(await form.locator('[data-lead-errors]').isVisible()), 'Editing the attachment left a stale summary validation visible');
  check(await attachment.getAttribute('aria-invalid') === null, 'Editing the attachment left aria-invalid set');
  check(!(await attachment.getAttribute('aria-describedby') || '').includes('server-error'), 'Editing the attachment left a stale aria-describedby reference');
  await form.locator('button[type=submit]').click();
  await page.waitForFunction(() => document.querySelector('[data-lead-form]')?.dataset.submitted === 'true');
  check(requests === 3, 'Network and validation retries did not issue exactly three requests');
  check(retriedPayload.includes('name="company"') && retriedPayload.includes('Studio North'), 'Company was not included in FormData');
  check(retriedPayload.includes('filename="revised-project.pdf"'), 'Corrected project file was not included in FormData');
  check(await form.locator('[data-lead-status]').innerText() === 'Спасибо! Ваша заявка успешно отправлена. Наш специалист свяжется с вами в ближайшее время.', 'Successful retry did not show saved status');
  check(await form.locator('[data-field-error]').count() === 0, 'A field error remained after the successful retry');
  check(!(await page.locator('body').innerText()).includes('Прикрепите проект в формате PDF, JPG или PNG.'), 'A stale attachment error remained after success');
  await page.unroute('**/api/leads/');

  const browser = page.context().browser();
  const noJsContext = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  try {
    const noJsPage = await noJsContext.newPage();
    let nativeRequest = false;
    await noJsPage.route('**/request/partner/', async route => {
      if (route.request().method() !== 'POST') return route.continue();
      nativeRequest = true;
      const contentType = route.request().headers()['content-type'] || '';
      const body = route.request().postData() || '';
      check(contentType.includes('multipart/form-data; boundary='), 'No-JS form did not submit multipart data');
      check(body.includes('filename="project.pdf"'), 'No-JS form omitted the project file');
      return route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: '<!doctype html><html lang="ru"><h1>Заявка принята</h1></html>' });
    });
    await noJsPage.goto(origin + '/request/partner/', {waitUntil:'domcontentloaded'});
    const nativeForm = noJsPage.locator('[data-lead-form]');
    await nativeForm.locator('[name=name]').fill('Тест без JavaScript');
    await nativeForm.locator('[name=contact]').fill('+7 900 000-00-03');
    await nativeForm.locator('[name=attachment]').setInputFiles({ name: 'project.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\nUI-only fixture') });
    await nativeForm.locator('[name=consent]').check();
    await nativeForm.locator('button[type=submit]').click();
    await noJsPage.waitForFunction(() => document.querySelector('h1')?.textContent === 'Заявка принята');
    check(nativeRequest, 'No-JS form did not submit natively');
  } finally {
    await noJsContext.close();
  }

  check(!errors.length, errors.join('; '));
  return { viewports: viewports.map(item => item.name), networkAndValidationRetry: requests === 3, noJavaScriptMultipart: true, errors };
}
