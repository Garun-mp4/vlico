async page => {
  const check = (value, message) => { if (!value) throw Error(message); };
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.emulateMedia({ reducedMotion:'reduce' });
  await page.goto('http://127.0.0.1:8000/');
  if (await page.locator('[data-privacy-panel]').isVisible()) await page.getByRole('button',{name:'Отклонить',exact:true}).click();
  const grid = page.locator('.home-project-grid');
  const originalCount = await grid.locator(':scope>.portfolio-card').count();
  check(originalCount <= 6, 'More than six projects on homepage');
  const dimensions = [];
  for (const [width, columns] of [[1920,3],[1440,3],[1100,3],[820,2],[641,2],[390,1],[320,1]]) {
    await page.setViewportSize({ width,height:1000 });
    await grid.scrollIntoViewIfNeeded();
    const actual = await grid.evaluate(node => getComputedStyle(node).gridTemplateColumns.split(' ').length);
    check(actual === columns, 'Wrong column count at ' + width);
    check(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), 'Overflow at ' + width);
    dimensions.push({width,columns:actual});
  }
  await page.setViewportSize({width:1440,height:1000});
  await grid.scrollIntoViewIfNeeded();
  const gallery = grid.locator('[data-project-carousel]').first();
  if (await gallery.count()) {
    await gallery.getByRole('button',{name:'Следующая фотография',exact:true}).click();
    check(await gallery.locator('[data-photo-number]').innerText() === '2', 'Gallery arrows stopped working');
    await gallery.locator('.project-carousel-track').press('ArrowLeft');
    check(await gallery.locator('[data-photo-number]').innerText() === '1', 'Gallery keyboard navigation stopped working');
  }
  await page.locator('#projects').screenshot({path:'.playwright-cli/home-projects-compact.png'});
  // Six-card layout fixture lives only in the browser, never in the database.
  await grid.evaluate(node => { while(node.children.length < 6 && node.firstElementChild) node.append(node.firstElementChild.cloneNode(true)); });
  const rows = await grid.locator(':scope>.portfolio-card').evaluateAll(nodes => new Set(nodes.map(node=>Math.round(node.getBoundingClientRect().top))).size);
  check(rows === 2, 'Six cards do not form two rows');
  await page.locator('.home-project-footer a').click();
  check(new URL(page.url()).pathname === '/projects/', 'View-all does not open the catalogue');
  check(await page.locator('.portfolio-grid>.portfolio-card').count() >= originalCount, 'Catalogue lost projects');
  check(!errors.length, errors.join('; '));
  return { maximum:6, dimensions, sixCards:'two rows on desktop', catalogue:'opens with all published work', gallery:'arrows and keyboard preserved', errors };
}
