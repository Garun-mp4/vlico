async page => {
  const check = (condition, message) => { if (!condition) throw new Error(message); };
  const origin = /^https?:/.test(page.url()) ? new URL('/', page.url()).origin : 'http://127.0.0.1:8000';
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const widths = [320, 360, 390, 768, 1024, 1280, 1440, 1920];
  const paths = ['/#calculator', '/calculator/'];

  for (const path of paths) {
    for (const width of widths) {
      await page.setViewportSize({ width, height: 900 });
      let response = await page.goto(origin + path);
      if (!response) response = await page.reload();
      check(response?.status() === 200, `${path} did not load at ${width}px`);
      const section = page.locator('.quick-calculator');
      const fields = section.locator('[data-quick-fields] [name]');
      check(new Set(await fields.evaluateAll(nodes => nodes.map(node => node.name))).size === 3, `${path} must show exactly three quick fields at ${width}px`);
      check(await section.locator('[data-configurator]').count() === 0, `${path} rendered the retired multi-step UI`);
      check(!(await section.innerText()).includes('₽'), `${path} displayed an unsubstantiated amount`);
      check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${path} overflows at ${width}px`);

      await section.locator('input[type="radio"][value="apartment"]').check();
      await section.getByLabel('Площадь потолка, м²').fill('60');
      await section.locator('input[type="radio"][value="consultation"]').check();
      await section.getByRole('button', { name: 'Получить предварительный расчёт' }).click();
      await section.getByText('Для предварительного расчёта уточним детали.', { exact: true }).waitFor();
      check(await section.locator('[data-quick-contact]').isVisible(), `${path} did not reveal its contact step at ${width}px`);
      check(!(await section.innerText()).includes('₽'), `${path} fabricated a numeric quote at ${width}px`);
    }
  }

  check(errors.length === 0, errors.join('; '));
  return { paths, widths, fields: 3, quote: 'honest individual estimate, no amount', errors };
}
