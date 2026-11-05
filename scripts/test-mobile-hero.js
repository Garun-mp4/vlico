async page => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('http://127.0.0.1:8000/');
  if (await page.locator('[data-privacy-panel]').isVisible()) await page.getByRole('button', { name: 'Отклонить', exact: true }).click();
  await page.evaluate(() => document.fonts.ready);
  const results = [];
  for (const [width, height] of [[320,568],[360,720],[390,844],[412,780],[640,360],[641,600],[768,700],[820,600],[1024,600],[1280,720],[1440,768],[1920,900],[2560,1080]]) {
    await page.setViewportSize({ width, height });
    await page.evaluate(() => scrollTo(0,0));
    const inspect = async () => page.evaluate(() => {
      const selectors = ['.hero-kicker','.hero-wordmark','.hero-bottom','.hero .scroll-cue'];
      const rects = selectors.map(selector => document.querySelector(selector).getBoundingClientRect());
      const logo = document.querySelector('.hero-wordmark').getBoundingClientRect();
      const content = ['.hero-offer','.hero-side'].map(selector => document.querySelector(selector).getBoundingClientRect());
      return { overlap: rects.some((rect,index) => index && rect.top < rects[index-1].bottom + 8) || content.some(rect => rect.top < logo.bottom + 8),
        clipped: rects.some(rect => rect.bottom > document.querySelector('.hero').getBoundingClientRect().bottom),
        overflow: document.documentElement.scrollWidth > innerWidth + 1 };
    });
    let state = await inspect();
    if (state.overlap || state.clipped || state.overflow) throw Error(JSON.stringify({width,height,...state}));
    if (width === 390) await page.locator('.hero').screenshot({ path: '.playwright-cli/mobile-hero-fixed.png' });
    // Simulate larger system text without changing the decorative wordmark.
    await page.locator('.hero h1,.hero-offer>p,.hero-side p,.hero-side dl div,.hero-actions a').evaluateAll(nodes => nodes.forEach(node => { node.style.fontSize = parseFloat(getComputedStyle(node).fontSize) * 1.5 + 'px'; }));
    state = await inspect();
    if (state.overlap || state.clipped || state.overflow) throw Error('Large text: ' + JSON.stringify({width,height,...state}));
    await page.locator('.hero [style]').evaluateAll(nodes => nodes.forEach(node => node.removeAttribute('style')));
    results.push({ width, height, normal: 'passed', largerText: 'passed' });
  }
  if (errors.length) throw Error(errors.join('; '));
  return { results, errors };
}
