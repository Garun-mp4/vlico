async page => {
  const check = (condition, message) => { if (!condition) throw Error(message); };
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('https://yandex.ru/**', route => route.fulfill({ contentType: 'text/html', body: '<p>Widget fixture</p>' }));
  await page.goto('http://127.0.0.1:8000/');
  const panel = page.locator('[data-privacy-panel]');
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await page.evaluate(() => localStorage.removeItem('vlicoPrivacy'));
    await page.reload();
    check(await panel.isVisible(), 'Initial cookie notice is absent');
    if (width <= 760) {
      const bounds = await panel.boundingBox();
      const gap = 844 - bounds.y - bounds.height;
      check(gap >= 11 && gap <= 13, 'Cookie notice is not anchored to the bottom');
      check(bounds.y >= 68, 'Cookie notice covers the header');
    }
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
  return { widths: [1440, 390, 320], controls: 'accept/reject without checkboxes', persistence: 'both choices retained', widgets: 'present before and after either choice', errors };
}
