async page => {
  const check = (condition, message) => { if (!condition) throw Error(message); };
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('https://yandex.ru/**', route => route.fulfill({ contentType: 'text/html', body: '<p>Widget fixture</p>' }));
  const baseUrl = /^https?:/.test(page.url()) ? new URL('/', page.url()).href : 'http://127.0.0.1:8000/';
  await page.goto(baseUrl);
  const panel = page.locator('[data-privacy-panel]');
  for (const width of [1440, 1280, 1024, 390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await page.evaluate(() => localStorage.removeItem('vlicoPrivacy'));
    await page.reload();
    await page.evaluate(() => {
      document.documentElement.style.scrollBehavior = 'auto';
      scrollTo(0, 0);
    });
    await page.evaluate(() => document.fonts.ready);
    check(await panel.isVisible(), 'Initial cookie notice is absent');
    check(await page.locator('[data-home-sticky-cta]').isHidden(), 'Mobile sticky CTA is visible behind the cookie notice');
    const bounds = await panel.boundingBox();
    const header = await page.locator('[data-site-header]').boundingBox();
    check(await panel.evaluate(el => getComputedStyle(el).position) === 'fixed', 'Cookie notice became a grid row');
    check(bounds.x >= 10 && bounds.x <= 22, 'Cookie notice is not anchored to the left');
    check(bounds.y >= header.y + header.height, 'Cookie notice covers the header');
    check(bounds.y + bounds.height <= 845 && bounds.y + bounds.height >= 820, 'Cookie notice is not anchored to the bottom');
    check(bounds.width <= Math.min(480, width - 24) + 1, 'Cookie notice spans the whole desktop row');
    check(await panel.locator('input[type=checkbox]').count() === 0, 'Initial notice still has checkboxes');
    check(await page.locator('iframe').count() >= 2, 'Widgets wait for consent');
    check(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), 'Overflow at ' + width);
    if (width !== 320) await panel.screenshot({ path: `.playwright-cli/cookie-banner-${width}.png` });
    await panel.getByRole('button', { name: 'Отклонить', exact: true }).click();
    check(!await panel.isVisible(), 'Refusal did not dismiss notice');
    check(await page.evaluate(() => JSON.parse(localStorage.getItem('vlicoPrivacy')).analytics) === false, 'Refusal enabled analytics');
    await page.reload();
    check(!await panel.isVisible(), 'Refusal did not persist');
    check(await page.locator('iframe').count() >= 2, 'Refusal removed ratings or reviews');
    await page.locator('footer [data-privacy-open]').click();
    await panel.getByRole('button', { name: 'Принять', exact: true }).click();
    check(await page.evaluate(() => JSON.parse(localStorage.getItem('vlicoPrivacy')).analytics) === true, 'Acceptance was not saved');
    await page.reload();
    check(!await panel.isVisible(), 'Acceptance did not persist');
    check(await page.locator('script[src*="mc.yandex.ru"]').count() === 0, 'Local environment loaded analytics');
  }
  check(!errors.length, errors.join('; '));
  await page.unroute('https://yandex.ru/**');
  return { widths: [1440, 1280, 1024, 390, 320], controls: 'accept/reject without checkboxes', persistence: 'both choices retained', widgets: 'present before and after either choice', errors };
}
