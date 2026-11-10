async page => {
  const check = (condition, message) => { if (!condition) throw Error(message); };
  const origin = /^https?:/.test(page.url()) ? new URL(page.url()).origin : 'http://127.0.0.1:8000';
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 1180 });
  await page.goto(origin + '/');
  await page.evaluate(() => {
    const version = JSON.parse(document.getElementById('site-config').textContent).consent_version;
    localStorage.setItem('vlicoPrivacy', JSON.stringify({ version, expires: Date.now() + 86400000, analytics: false, external: false }));
  });
  await page.reload();
  const section = page.locator('#reviews');
  const sections = await page.locator('main > section').evaluateAll(nodes => nodes.map(node => node.id));
  const aboutIndex = sections.indexOf('about');
  const offerIndex = sections.indexOf('special-offer');
  const reviewsIndex = sections.indexOf('reviews');
  const projectsIndex = sections.indexOf('projects');
  check(aboutIndex >= 0 && offerIndex > aboutIndex && reviewsIndex > offerIndex && projectsIndex > reviewsIndex, 'Reviews must follow the existing offer and precede the project gallery');
  check(await page.locator('iframe').count() > 0, 'Widgets require consent');
  check(await section.getByRole('link', { name: 'Все отзывы на Яндекс Картах ↗', exact: true }).getAttribute('href') === 'https://yandex.ru/maps/org/studiya_potolkov_vlico/164382623295/reviews/', 'All-reviews link changed');
  check((await section.getByRole('link', { name: 'Оставить отзыв ↗', exact: true }).getAttribute('href')).endsWith('reviews/?add-review=true'), 'Write-review link changed');
  const iframe = section.locator('[data-external-widget=reviews] iframe');
  await iframe.waitFor();
  const frame = page.frameLocator('#reviews [data-external-widget=reviews] iframe');
  await frame.locator('.comment').nth(2).waitFor({ state: 'visible', timeout: 20000 });
  await frame.locator('body').evaluate(() => document.fonts.ready);
  check(await iframe.getAttribute('src') === 'https://yandex.ru/maps-reviews-widget/164382623295?comments', 'Reviews are not from the official widget');
  const preference = await page.evaluate(() => JSON.parse(localStorage.getItem('vlicoPrivacy')));
  check(preference.analytics === false, 'Loading reviews must not enable analytics');
  const viewports = [];
  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: width < 768 ? 844 : 1180 });
    await iframe.scrollIntoViewIfNeeded();
    await frame.locator('.badge__comments').evaluate(() => new Promise(resolve => requestAnimationFrame(resolve)));
    const visible = await frame.locator('.badge__comments').evaluate(container => {
      const bounds = container.getBoundingClientRect();
      return [...container.querySelectorAll('.comment')].filter(node => {
        const rect = node.getBoundingClientRect();
        return rect.top >= bounds.top - 1 && rect.bottom <= bounds.bottom + 1;
      }).length;
    });
    check(visible >= 3, 'Fewer than three original review previews fit at ' + width);
    check((await iframe.boundingBox()).width >= 300, 'Widget is narrower than supported at ' + width);
    check(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), 'Overflow at ' + width);
    viewports.push({ width, visible });
    if (width === 1440 || width === 390) await section.screenshot({ path: `.playwright-cli/reviews-after-${width}.png` });
  }
  await page.locator('footer [data-privacy-open]').click();
  await page.getByRole('button', { name: 'Отклонить', exact: true }).click();
  check(await page.locator('iframe').count() > 0, 'Refusing analytics removed reviews');
  await page.goto(origin + '/contacts/');
  const contactsFrame = page.locator('[data-external-widget=reviews] iframe');
  check((await contactsFrame.boundingBox()).width >= 300, 'Contacts widget is narrower than supported on small phones');
  check(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), 'Contacts overflow on small phones');
  check(!errors.length, errors.join('; '));
  return { section: 'after the offer, before projects', source: 'unmodified live Yandex widget', viewports, privacy: 'reviews stay visible with analytics refused', links: 'all reviews and write-review preserved', errors };
}
