async page => {
  const check = (condition, message) => { if (!condition) throw Error(message); };
  const waitForState = async (predicate, label) => {
    try { await page.waitForFunction(predicate, undefined, { timeout: 5000 }); }
    catch (error) { throw Error(`${label}: ${error.message}`); }
  };
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const baseUrl = /^https?:/.test(page.url()) ? new URL('/', page.url()).href : 'http://127.0.0.1:8000/';
  let slowHeroImage = false;
  await page.route('**/home-hero/room-*.webp', async route => {
    slowHeroImage = true;
    await new Promise(resolve => setTimeout(resolve, 700));
    await route.continue();
  });
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });
  const imageBoxBeforeLoad = await page.locator('.home-hero-image').boundingBox();
  await page.locator('.home-hero-image').evaluate(image => image.decode());
  const imageBoxAfterLoad = await page.locator('.home-hero-image').boundingBox();
  check(slowHeroImage, 'Slow-network image route was not exercised');
  check(imageBoxBeforeLoad && imageBoxAfterLoad && Math.abs(imageBoxBeforeLoad.width - imageBoxAfterLoad.width) < 1 && Math.abs(imageBoxBeforeLoad.height - imageBoxAfterLoad.height) < 1, 'Hero image changed the reserved layout after loading');
  await page.unroute('**/home-hero/room-*.webp');
  if (await page.locator('[data-privacy-panel]').isVisible()) await page.getByRole('button', { name: 'Отклонить', exact: true }).click();
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(async () => Promise.all([...document.querySelectorAll('.home-hero-image,.home-solution-image img')].map(image => image.decode().catch(() => {}))));

  const sizes = [[320,568],[360,720],[390,844],[412,780],[640,360],[641,600],[768,700],[820,600],[1024,600],[1280,720],[1440,900],[1920,1080],[2560,1080]];
  const results = [];
  const inspect = async () => page.evaluate(() => {
    const hero = document.querySelector('.home-hero');
    const image = document.querySelector('.home-hero-image');
    const cards = [...document.querySelectorAll('[data-home-solution]')];
    const rail = document.querySelector('[data-home-solutions]');
    const first = cards[0]?.getBoundingClientRect();
    const next = cards[1]?.getBoundingClientRect();
    const proof = document.querySelector('.home-hero-proof').getBoundingClientRect();
    const primary = document.querySelector('.home-hero-primary').getBoundingClientRect();
    return {
      overflow: document.documentElement.scrollWidth > innerWidth + 1,
      hero: Boolean(hero),
      heading: document.querySelector('#hero-title')?.textContent.trim(),
      proof: [...document.querySelectorAll('.home-hero-proof li')].map(item => item.textContent.trim()),
      cardCount: cards.length,
      imagesLoaded: [image, ...document.querySelectorAll('.home-solution-image img')].every(item => item.complete && item.naturalWidth > 0),
      cardsInViewport: cards.every(card => { const rect = card.getBoundingClientRect(); return rect.top >= 0 && rect.bottom <= innerHeight + 1; }),
      nextCardPeek: rail && first && next ? Math.max(0, rail.getBoundingClientRect().right - next.left) : 0,
      railScrollable: rail ? rail.scrollWidth > rail.clientWidth + 2 : false,
      proofInViewport: proof.top >= 0 && proof.bottom <= innerHeight,
      primaryInViewport: primary.top >= 0 && primary.bottom <= innerHeight,
      reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
      scrollSnapType: rail ? getComputedStyle(rail).scrollSnapType : '',
    };
  });

  for (const [width, height] of sizes) {
    await page.setViewportSize({ width, height });
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    await page.locator('.home-hero-image').evaluate(image => image.decode());
    await page.evaluate(() => {
      scrollTo(0, 0);
      const rail = document.querySelector('[data-home-solutions]');
      if (rail) rail.scrollLeft = 0;
    });
    const state = await inspect();
    check(state.hero, 'Homepage hero is absent');
    check(!state.overflow, `Document overflow at ${width}x${height}`);
    check(state.heading === 'Потолки и свет, продуманные вместе.', 'Homepage H1 changed');
    check(JSON.stringify(state.proof) === JSON.stringify(['17 лет опыта', 'Сложные дизайнерские решения', 'Детальная смета']), 'Confirmed proof items are missing or changed');
    check(state.cardCount === 4, 'Expected four solution cards, received ' + state.cardCount);
    check(state.imagesLoaded, 'A first-screen image failed to load at ' + width);
    check(state.reducedMotion && (width > 760 || state.scrollSnapType === 'none'), 'Reduced-motion settings are not respected at ' + width);
    if (width === 320 || width === 390) {
      check(state.railScrollable, 'Mobile solution rail is not horizontally scrollable at ' + width);
      check(state.nextCardPeek >= 12, 'The next card is not visible at ' + width + ': ' + JSON.stringify(state));
      check(await page.locator('.home-hero-primary').isVisible(), 'Primary project CTA is hidden at ' + width);
      check(await page.locator('[data-home-sticky-cta]').isHidden(), 'Sticky CTA covers first-screen copy before the hero CTA has passed at ' + width);
      if (width === 320) check(state.proofInViewport && state.primaryInViewport, 'Proof line or primary CTA falls below the 320px first viewport');
    }
    if (width === 1280 || width === 1440 || width === 1920) check(state.cardsInViewport, `All four cards do not fit in the first viewport at ${width}x${height}`);
    if (width === 390) await page.locator('.home-hero').screenshot({ path: '.playwright-cli/mobile-hero-m01.png' });
    if (width === 320) await page.locator('.home-hero').screenshot({ path: '.playwright-cli/mobile-hero-320-m01.png' });

    await page.evaluate(() => {
      document.querySelectorAll('.home-hero-copy h1,.home-hero-copy p,.home-hero-copy a,.home-solution-title,.home-solution-summary,.home-solution-detail p,.home-solution-detail a').forEach(node => {
        const size = parseFloat(getComputedStyle(node).fontSize);
        node.style.setProperty('font-size', `${size * 2}px`, 'important');
      });
    });
    const largerText = await inspect();
    check(!largerText.overflow, `Document overflow with larger text at ${width}x${height}`);
    await page.evaluate(() => document.querySelectorAll('.home-hero-copy h1,.home-hero-copy p,.home-hero-copy a,.home-solution-title,.home-solution-summary,.home-solution-detail p,.home-solution-detail a').forEach(node => node.style.removeProperty('font-size')));
    results.push({ width, height, normal: 'passed', largerText: 'passed' });
  }

  const summaries = page.locator('[data-home-solution] > summary');
  const panels = page.locator('[data-hero-intro], [data-home-solution]');
  const layout = page.locator('[data-hero-layout]');
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.mouse.move(5, 5);
  await page.reload();
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  const initial = await panels.evaluateAll(items => items.map(item => item.getBoundingClientRect().width));
  for (const index of [1, 4, 2, 3]) {
    const bounds = await panels.nth(index).boundingBox();
    await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 4);
    await page.waitForFunction(({index, width}) => {
      const items = [...document.querySelectorAll('[data-hero-intro], [data-home-solution]')];
      return document.querySelector('[data-hero-layout]').dataset.heroActive === String(index)
        && Math.abs(items[index].getBoundingClientRect().width - width) < 1;
    }, {index, width: initial[0]});
    const widths = await panels.evaluateAll(items => items.map(item => item.getBoundingClientRect().width));
    check(widths.every((width, i) => i === index || Math.abs(width - initial[1]) < 1), 'Inactive panels did not all return to rail width');
    const body = panels.nth(index).locator('.home-solution-detail');
    check(await body.locator('h3').isVisible() && await body.getByRole('link').isVisible(), 'Expanded panel is missing its heading or CTA');
  }
  await page.mouse.move(5, 5);
  check(await layout.getAttribute('data-hero-active') === '3', 'Leaving the hero collapsed the active panel');
  await page.keyboard.press('Tab');
  await summaries.nth(1).press('Enter');
  check(await layout.getAttribute('data-hero-active') === '2', 'Keyboard did not switch the wide panel');
  check(await layout.getAttribute('data-hero-motion') === null, 'Keyboard selection unexpectedly animated');
  await panels.nth(2).getByRole('link').focus();
  await page.keyboard.press('Escape');
  check(await layout.getAttribute('data-hero-active') === '0', 'Escape did not restore the overview');
  let disclosures;
  await page.emulateMedia({ reducedMotion: 'reduce' });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => scrollTo(0, 0));
  await page.locator('[data-home-solution]').nth(1).dispatchEvent('pointerenter', { pointerType: 'touch' });
  disclosures = await page.locator('[data-home-solution]').evaluateAll(cards => cards.map(card => ({ open: card.open, expanded: card.querySelector('summary').getAttribute('aria-expanded') })));
  check(!disclosures[1].open, 'Touch pointer entry triggered a mouse-only hover preview');
  await summaries.nth(1).click();
  disclosures = await page.locator('[data-home-solution]').evaluateAll(cards => cards.map(card => ({ open: card.open, expanded: card.querySelector('summary').getAttribute('aria-expanded') })));
  check(disclosures.filter(card => card.open).length === 1 && disclosures[1].open && disclosures[1].expanded === 'true', 'Click did not open and pin the selected card');
  check(disclosures.filter(card => card.expanded === 'true').length === 1, 'aria-expanded does not match the open card');
  await page.locator('[data-home-solution]').nth(1).locator('a').focus();
  await page.keyboard.press('Escape');
  disclosures = await page.locator('[data-home-solution]').evaluateAll(cards => cards.map(card => ({ open: card.open, expanded: card.querySelector('summary').getAttribute('aria-expanded') })));
  check(!disclosures.some(card => card.open || card.expanded === 'true'), 'Escape did not close the card');
  check(await summaries.nth(1).evaluate(node => document.activeElement === node), 'Escape moved keyboard focus away from the active card');
  await summaries.nth(2).focus();
  disclosures = await page.locator('[data-home-solution]').evaluateAll(cards => cards.map(card => ({ open: card.open, expanded: card.querySelector('summary').getAttribute('aria-expanded') })));
  check(disclosures[2].open && disclosures[2].expanded === 'true', 'Keyboard focus did not reveal the focused card');

  await page.evaluate(() => {
    const button = document.querySelector('.home-hero-primary').getBoundingClientRect();
    // Test the persistent action away from the solution rail, where it intentionally yields to card controls.
    const about = document.querySelector('#about').getBoundingClientRect();
    scrollTo(0, scrollY + about.top + 100);
  });
  await waitForState(() => !document.querySelector('[data-home-sticky-cta]').hidden, 'Sticky CTA did not appear after the hero CTA left view');
  const sticky = page.locator('[data-home-sticky-cta]');
  const stickyBounds = await sticky.boundingBox();
  check(stickyBounds && stickyBounds.y + stickyBounds.height <= 844 - 11, 'Mobile sticky CTA does not respect the viewport and safe-area edge');
  const menuSummary = page.locator('[data-header-mobile] > summary');
  const menuBounds = await menuSummary.boundingBox();
  check(menuBounds, 'Mobile menu toggle is unavailable');
  await page.mouse.click(menuBounds.x + menuBounds.width / 2, menuBounds.y + menuBounds.height / 2);
  await waitForState(() => document.querySelector('[data-header-mobile]').open && document.querySelector('[data-home-sticky-cta]').hidden, 'Sticky CTA did not yield to the open mobile menu');
  await page.mouse.click(menuBounds.x + menuBounds.width / 2, menuBounds.y + menuBounds.height / 2);
  await waitForState(() => !document.querySelector('[data-header-mobile]').open && !document.querySelector('[data-home-sticky-cta]').hidden, 'Sticky CTA did not return after closing the mobile menu');
  await sticky.click();
  await waitForState(() => location.hash === '#contact' && document.activeElement.id === 'contact-title', 'Sticky CTA did not focus the contact heading');
  check(await sticky.isHidden(), 'Mobile sticky CTA remains visible over the contact form');

  const links = await page.locator('.home-hero-actions a').evaluateAll(nodes => nodes.map(node => node.getAttribute('href')));
  check(links.some(href => href === '#contact') && links.some(href => href === '#calculator') && links.some(href => href.includes('measurement')) && links.some(href => href === '#projects'), 'A primary hero destination is missing');
  check(await page.locator('#special-offer, #calculator, #projects, #contact').count() === 4, 'A same-page hero destination has no matching section');
  const destinationLinks = await page.locator('[data-home-solution] .home-solution-detail a[href^="/"]').evaluateAll(nodes => nodes.map(node => node.getAttribute('href')));
  const destinationStatuses = await page.evaluate(async hrefs => Promise.all(hrefs.map(async href => (await fetch(href, { credentials: 'same-origin' })).status)), destinationLinks);
  check(destinationStatuses.length === 3 && destinationStatuses.every(status => status === 200), 'A solution-card destination failed: ' + destinationStatuses.join(', '));
  const contactLinks = await page.locator('.home-hero-contact a').evaluateAll(nodes => nodes.map(node => ({ href: node.getAttribute('href'), rel: node.getAttribute('rel') })));
  check(contactLinks.some(link => link.href === 'tel:+79097888844'), 'Phone link is incorrect');
  check(contactLinks.some(link => link.href === 'https://t.me/vlico_39' && link.rel.includes('noopener')), 'Telegram link is incorrect or unsafe');
  check(contactLinks.some(link => link.href === 'https://wa.me/79097888844' && link.rel.includes('noopener')), 'WhatsApp link is incorrect or unsafe');
  const heroText = await page.locator('.home-hero').textContent();
  check(!heroText.includes('100 м²') && !heroText.includes('октябрь'), 'Unconfirmed offer conditions were published');

  const touchContext = await page.context().browser().newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const touchPage = await touchContext.newPage();
  touchPage.on('pageerror', error => errors.push(error.message));
  await touchPage.goto(baseUrl);
  if (await touchPage.locator('[data-privacy-panel]').isVisible()) await touchPage.getByRole('button', { name: 'Отклонить', exact: true }).click();
  await touchPage.locator('[data-home-solution] > summary').nth(1).tap();
  const touchState = await touchPage.locator('[data-home-solution]').evaluateAll(cards => cards.map(card => ({ open: card.open, expanded: card.querySelector('summary').getAttribute('aria-expanded') })));
  check(touchState.filter(card => card.open).length === 1 && touchState[1].open && touchState[1].expanded === 'true', 'Touch did not open the selected solution');
  await touchPage.locator('[data-home-solution] > summary').nth(2).tap();
  check(await touchPage.locator('[data-home-solution]').nth(2).locator('a').isVisible(), 'Touch cannot reach the selected solution link');
  check(!await touchPage.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), 'Touch layout overflows the viewport');
  await touchContext.close();

  await page.route('**/home-hero*.js', route => route.abort());
  await page.goto(baseUrl);
  const nativeCards = page.locator('[data-home-solution]');
  check(await nativeCards.nth(0).locator('summary').isVisible(), 'Native no-JavaScript offer disclosure is not available');
  check(await nativeCards.nth(1).locator('summary').getAttribute('aria-expanded') === null, 'Enhanced aria state leaked into the no-JavaScript fallback');
  await nativeCards.nth(1).locator('summary').click();
  check(await nativeCards.nth(1).evaluate(card => card.open), 'Native no-JavaScript disclosure did not open');
  check(await nativeCards.nth(1).locator('a').isVisible(), 'Native no-JavaScript solution link is unavailable');
  await page.unroute('**/home-hero*.js');
  await page.goto(baseUrl);
  check(!errors.length, errors.join('; '));

  return { viewports: results, interactions: 'full-width panel exchange, stable rail widths, touch taps, keyboard focus, Escape, no-JavaScript disclosure and aria-expanded passed', sticky: 'safe-area position, menu suppression, contact focus and form clearance passed', links: 'project, calculator, measurement, phone and messaging destinations passed', errors };
}
