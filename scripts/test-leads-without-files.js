async page => {
  const check = (value, message) => { if (!value) throw Error(message); };
  const pageOrigin = new URL(page.url()).origin;
  const origin = pageOrigin === 'null' ? 'http://127.0.0.1:8000' : pageOrigin;
  const errors = [], sent = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/leads/', route => {
    const body = route.request().postData() || '';
    check(!body.includes('filename=') && !body.includes('name="attachments"'), 'Upload data is still being sent');
    sent.push(route.request().url());
    return route.fulfill({ status:201,contentType:'application/json',body:JSON.stringify({ok:true,kind:'project',reference:'ui-no-file-test',message:'Заявка принята. Мы свяжемся с вами по указанному контакту.'}) });
  });
  for (const path of ['/', '/request/consultation/', '/request/measurement/', '/request/project/']) {
    await page.goto(origin + path);
    if (await page.locator('[data-privacy-panel]').isVisible()) await page.getByRole('button',{name:'Отклонить',exact:true}).click();
    check(await page.locator('input[type=file]').count() === 0, 'Upload control remains at ' + path);
    const forms = page.locator('[data-lead-form]');
    for (let index = 0; index < await forms.count(); index += 1) {
      check(await forms.nth(index).locator('input[type=file]').count() === 0, 'Upload control remains in a form at ' + path);
    }
    const form = path === '/' ? page.locator('#contact-form') : forms.first();
    await form.locator('[name=name]').fill('Тест интерфейса');
    await form.locator('[name=contact]').fill('no-files@example.invalid');
    await form.locator('[name=consent]').check();
    await form.locator('button[type=submit]').click();
    const formSelector = path === '/' ? '#contact-form' : '[data-lead-form]';
    await page.waitForFunction(selector => document.querySelector(selector)?.dataset.submitted === 'true', formSelector);
    const confirmation = await form.locator('[data-lead-status]').innerText();
    check(confirmation.includes('Заявка принята.') && !confirmation.includes('ui-no-file-test'), 'Confirmation exposes an internal reference at ' + path);
  }
  await page.goto(origin + '/calculator/');
  check(await page.locator('input[type=file]').count() === 0, 'Calculator still has an upload control');
  check(await page.locator('[data-config-upload],[data-upload-progress]').count() === 0, 'Upload progress remains');
  await page.unroute('**/api/leads/');
  check(!errors.length, errors.join('; '));
  return { forms:sent.length, calculator:'no upload controls', errors };
}
