async page => {
  const check = (value, message) => { if (!value) throw Error(message); };
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('http://127.0.0.1:8000/');
  if (await page.locator('[data-privacy-panel]').isVisible()) await page.getByRole('button', { name: 'Отклонить', exact: true }).click();
  await page.evaluate(() => document.fonts.ready);
  const word = page.locator('[data-footer-wordmark]');
  // SVG use clones need typography on the source, not an ancestor CSS selector.
  check((await word.locator('#footer-letters').getAttribute('font-family')).startsWith('Manrope'), 'SVG highlight source must explicitly use Manrope');
  check(await word.locator('#footer-letters').getAttribute('letter-spacing') === '0', 'SVG clone spacing differs from base text');
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
  const originalShape = await word.locator('[data-footer-blob-shape]').getAttribute('d');
  check(originalShape?.includes('C') && !await word.locator('circle').count(), 'Organic mask is missing');
  const inertia = await word.evaluate(async node => {
    const spot=node.querySelector('[data-footer-spot]'),rect=node.querySelector('svg').getBoundingClientRect();
    const before=spot.style.transform;
    node.dispatchEvent(new PointerEvent('pointermove',{pointerType:'mouse',clientX:rect.left+rect.width*.75,clientY:rect.top+rect.height*.5}));
    const immediate=spot.style.transform;
    await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    return {deferred:before===immediate,lag:Math.abs(new DOMMatrix(getComputedStyle(spot).transform).e-750)};
  });
  check(inertia.deferred && inertia.lag>10,'Highlight jumps to pointer instead of following with inertia');
  await page.mouse.move(bounds.x + bounds.width * .75, bounds.y + bounds.height * .5);
  await page.waitForFunction(previous => document.querySelector('[data-footer-spot]').getAttribute('style') !== previous, first);
  await page.waitForFunction(previous=>document.querySelector('[data-footer-blob-shape]').getAttribute('d')!==previous,originalShape);
  await page.locator('.site-footer').screenshot({ path: '.playwright-cli/footer-highlight.png' });
  // Allow the documented 1.1s settling window, then verify there is no idle loop.
  await page.waitForTimeout(1400);
  const settled=await word.locator('[data-footer-blob-shape]').getAttribute('d');
  await page.waitForTimeout(250);
  check(await word.locator('[data-footer-blob-shape]').getAttribute('d')===settled,'Mask keeps animating while pointer is idle');
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
  return { widths:[320,390,768,1440,1920], layout:'full word and clear footer bar', pointer:'organic shape, inertial following, bounded settling and no idle loop', inertia, reducedMotion:'static', touch:'static', errors };
}
