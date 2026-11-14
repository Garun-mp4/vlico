// Run against VLICO with playwright-cli run-code. Does not send messages or leads.
async page => {
  const origin = new URL(page.url()).origin;
  const check = (value, message) => { if (!value) throw Error(message); };
  const results = [];
  const errors = [];
  await page.emulateMedia({reducedMotion: 'reduce'});
  page.on('pageerror', error => errors.push(error.message));
  for (const path of ['/', '/contacts/']) {
    for (const [width, height] of [[1440, 900], [1024, 768], [761, 600], [760, 600], [390, 844], [320, 568], [844, 390]]) {
      await page.setViewportSize({width, height});
      await page.goto(origin + path, {waitUntil: 'domcontentloaded'});
      await page.evaluate(() => localStorage.removeItem('vlicoPrivacy'));
      await page.reload({waitUntil: 'domcontentloaded'});
      const panel = page.locator('[data-privacy-panel]');
      const launcher = page.locator('#chat-widget-container .chat-bar');
      await launcher.waitFor({state: 'visible'});
      await page.evaluate(() => document.fonts.ready);
      const before = await launcher.boundingBox();
      const cookie = await panel.boundingBox();
      check(cookie && before, 'Missing cookie notice or launcher');
      check(before.x + before.width <= cookie.x || before.x >= cookie.x + cookie.width
        || before.y + before.height <= cookie.y || before.y >= cookie.y + cookie.height,
      `Cookie overlaps launcher: ${path} ${width}`);
      check(cookie.y >= 80 && cookie.y + cookie.height <= height, `Cookie outside usable viewport: ${width}`);
      await panel.getByRole('button', {name: 'Отклонить', exact: true}).click();
      await page.waitForTimeout(150);
      const after = await launcher.boundingBox();
      check(Math.abs(before.y - after.y) < 1, `Cookie moves launcher: ${path} ${width} (${before.y} -> ${after.y})`);
      check(Math.abs(height - after.y - after.height - (width <= 760 ? 16 : 24)) < 1, `Unexpected launcher anchor: ${width}`);
      await launcher.click();
      const chat = page.locator('.chat-window:visible');
      await chat.waitFor({state: 'visible'});
      check(await chat.locator('.message-input').isEditable(), 'Chat input unavailable');
      const chatBounds = await chat.boundingBox();
      check(chatBounds.y >= 0 && chatBounds.y + chatBounds.height <= height,
        `Chat outside viewport: ${width}x${height}`);
      await chat.locator('.close-btn').click();
      await chat.waitFor({state: 'hidden'});
      await launcher.waitFor({state: 'visible'});
      await page.locator('footer [data-privacy-open]').focus();
      await page.keyboard.press('Enter');
      await panel.waitFor({state: 'visible'});
      await page.waitForTimeout(150);
      check(Math.abs((await launcher.boundingBox()).y - after.y) < 1, `Reopening cookie moves launcher: ${width}`);
      await panel.getByRole('button', {name: 'Принять', exact: true}).click();
      check(await page.evaluate(() => JSON.parse(localStorage.getItem('vlicoPrivacy')).analytics), 'Accept not saved');
      check(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), `Overflow: ${width}`);
      results.push({path, width, height, passed: true});
    }
  }
  check(!errors.length, errors.join('; '));
  return {results, errors};
}
