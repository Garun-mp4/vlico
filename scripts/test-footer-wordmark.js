async page => {
  const check = (value, message) => { if (!value) throw Error(message); };
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('http://127.0.0.1:8000/');
  if (await page.locator('[data-privacy-panel]').isVisible()) await page.getByRole('button', { name: 'Отклонить', exact: true }).click();
  await page.evaluate(() => document.fonts.ready);
  const word = page.locator('[data-footer-wordmark]');
  for (const width of [320,390,768,1440,1920]) {
    await page.setViewportSize({ width, height: 1000 });
    await word.scrollIntoViewIfNeeded();
    const bounds = await word.boundingBox(), band = await page.locator('.footer-bottom').boundingBox();
    check(bounds.x >= 0 && bounds.x + bounds.width <= width, 'Wordmark overflows at ' + width);
    check(bounds.y + bounds.height + 20 <= band.y, 'Wordmark overlaps footer bar at ' + width);
    check(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), 'Page overflows at ' + width);
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await word.scrollIntoViewIfNeeded();
  let bounds = await word.boundingBox();
  await page.mouse.move(bounds.x + bounds.width * .45, bounds.y + bounds.height * .5);
  await page.waitForFunction(() => getComputedStyle(document.querySelector('.footer-wordmark-highlight')).opacity === '1');
  check(await word.locator('.footer-wordmark-highlight').evaluate(n => getComputedStyle(n).fill) === 'rgb(39, 190, 130)', 'Highlight is not the brand color');
  const first = await word.locator('[data-footer-spot]').getAttribute('style');
  await page.mouse.move(bounds.x + bounds.width * .75, bounds.y + bounds.height * .5);
  await page.waitForFunction(previous => document.querySelector('[data-footer-spot]').getAttribute('style') !== previous, first);
  await page.locator('.site-footer').screenshot({ path: '.playwright-cli/footer-highlight.png' });
  await page.mouse.move(0,0);
  check(!await word.evaluate(n => n.classList.contains('is-highlighted')), 'Effect remains active after leave');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.mouse.move(bounds.x + bounds.width * .5, bounds.y + bounds.height * .5);
  check(!await word.evaluate(n => n.classList.contains('is-highlighted')), 'Reduced motion still tracks pointer');
  const context = await page.context().browser().newContext({ viewport: { width:390,height:844 }, isMobile:true, hasTouch:true });
  const mobile = await context.newPage();
  await mobile.goto('http://127.0.0.1:8000/');
  await mobile.getByRole('button', { name:'Отклонить',exact:true }).click();
  await mobile.evaluate(() => document.fonts.ready);
  await mobile.locator('[data-footer-wordmark]').tap();
  check(!await mobile.locator('[data-footer-wordmark]').evaluate(n => n.classList.contains('is-highlighted')), 'Touch activated pointer effect');
  await mobile.locator('.site-footer').screenshot({ path: '.playwright-cli/footer-mobile.png' });
  await context.close();
  check(!errors.length, errors.join('; '));
  return { widths:[320,390,768,1440,1920], layout:'full word and clear footer bar', pointer:'local brand highlight follows pointer and stops on leave', reducedMotion:'static', touch:'static', errors };
}
