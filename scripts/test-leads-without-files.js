async page => {
  const check = (value, message) => { if (!value) throw Error(message); };
  const errors = [], sent = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/leads/', route => {
    const body = route.request().postData() || '';
    check(!body.includes('filename=') && !body.includes('name="attachments"'), 'Upload data is still being sent');
    sent.push(route.request().url());
    return route.fulfill({ status:201,contentType:'application/json',body:JSON.stringify({ok:true,kind:'project',reference:'ui-no-file-test',message:'Заявка сохранена.'}) });
  });
  for (const path of ['/', '/request/consultation/', '/request/measurement/', '/request/project/', '/request/partner/']) {
    await page.goto('http://127.0.0.1:8000' + path);
    if (await page.locator('[data-privacy-panel]').isVisible()) await page.getByRole('button',{name:'Отклонить',exact:true}).click();
    check(await page.locator('input[type=file]').count() === 0, 'Upload control remains at ' + path);
    const form = page.locator('[data-lead-form]');
    await form.locator('[name=name]').fill('Тест интерфейса');
    await form.locator('[name=contact]').fill('no-files@example.invalid');
    await form.locator('[name=consent]').check();
    await form.locator('button[type=submit]').click();
    await page.waitForFunction(() => document.querySelector('[data-lead-form]').dataset.submitted === 'true');
  }
  await page.goto('http://127.0.0.1:8000/calculator/');
  check(await page.locator('input[type=file]').count() === 0, 'Calculator still has an upload control');
  check(await page.locator('[data-config-upload],[data-upload-progress]').count() === 0, 'Upload progress remains');
  await page.unroute('**/api/leads/');
  check(!errors.length, errors.join('; '));
  return { forms:sent.length, calculator:'no upload controls', errors };
}
