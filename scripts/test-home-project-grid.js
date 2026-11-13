async page => {
  const check = (value, message) => { if (!value) throw Error(message); };
  const base = new URL(page.url()).origin;
  const errors = [];
  const mediaErrors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => {
    if (/^\/project-media\/\d+\/(thumb|full)\/$/.test(new URL(response.url()).pathname) && response.status() >= 400) {
      mediaErrors.push(`${response.status()} ${response.url()}`);
    }
  });
  await page.emulateMedia({ reducedMotion:'reduce' });
  await page.goto(base + '/');
  if (await page.locator('[data-privacy-panel]').isVisible()) await page.getByRole('button',{name:'Отклонить',exact:true}).click();
  const aboutLayouts = [];
  for (const width of [320, 1440]) {
    await page.setViewportSize({width,height:960});
    await page.goto(base + '/');
    const about = page.locator('#about');
    const copy = about.locator('.about-copy');
    const founder = about.locator('.about-founder');
    const portrait = founder.locator('.about-founder-photo');
    const gallery = about.locator('.about-projects');
    check((await about.locator('#about-title').textContent()).trim() === 'ПОТОЛОК — ОСНОВА КРАСИВОГО ИНТЕРЬЕРА', 'About heading changed at ' + width);
    check((await copy.locator('.about-text').innerText()).includes('17 лет') && (await copy.locator('.about-text').innerText()).includes('премиальные потолочные системы') && (await copy.locator('.about-text').innerText()).includes('архитектурным освещением') && (await copy.locator('.about-text').innerText()).includes('сложные дизайнерские решения'), 'About copy lost a confirmed focus at ' + width);
    check((await founder.locator('figcaption').innerText()).replace(/\s+/g,' ').trim() === 'Владлен Гизерский — основатель и руководитель VLICO', 'Founder caption mismatch at ' + width);
    check(/vladlen-gizerskiy-portrait-640\.[a-f0-9]+\.webp/.test(await portrait.getAttribute('srcset')) && /vladlen-gizerskiy-portrait-960\.[a-f0-9]+\.webp/.test(await portrait.getAttribute('srcset')), 'Responsive founder portrait variants are missing');
    check((await portrait.getAttribute('alt')).includes('Владлена Гизерского'), 'Founder portrait has no descriptive alt text');
    check(await portrait.getAttribute('width') === '960' && await portrait.getAttribute('height') === '1280', 'Founder portrait dimensions are not reserved');
    await portrait.scrollIntoViewIfNeeded();
    await portrait.evaluate(img => img.decode());
    check(await about.locator('.about-founder-message').count() === 0, 'An unapproved founder message appeared on the public page');
    check(!(await about.innerHTML()).includes('about-lighting-editorial'), 'The placeholder visualization still occupies the founder portrait slot');
    check(await gallery.locator('.about-project-thumb').count() > 0, 'Existing published project photos disappeared from the about section');
    check(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), 'About section overflows at ' + width);
    const layout = await page.evaluate(() => {
      const copy = document.querySelector('.about-copy').getBoundingClientRect();
      const founder = document.querySelector('.about-founder').getBoundingClientRect();
      const gallery = document.querySelector('.about-projects').getBoundingClientRect();
      return {copy:{x:copy.x,y:copy.y,right:copy.right,bottom:copy.bottom,width:copy.width},founder:{x:founder.x,y:founder.y,right:founder.right,bottom:founder.bottom,width:founder.width},gallery:{y:gallery.y}};
    });
    if (width === 1440) check(layout.copy.right < layout.founder.x, 'Desktop about copy is not left of the founder portrait');
    if (width === 320) check(layout.copy.bottom < layout.founder.y && layout.founder.bottom < layout.gallery.y, 'Mobile about reading order must be copy, portrait and project gallery');
    await page.setViewportSize({width,height:2000});
    await page.evaluate(() => {
      const aboutTop = document.querySelector('#about').getBoundingClientRect().top + window.scrollY;
      window.scrollTo(0, Math.max(0, aboutTop - 100));
    });
    await about.screenshot({path:'.playwright-cli/m05-about-' + width + '.png'});
    aboutLayouts.push({width,copyWidth:Math.round(layout.copy.width),portraitWidth:Math.round(layout.founder.width),galleryPhotos:await gallery.locator('.about-project-thumb').count()});
  }
  await page.setViewportSize({width:720,height:2000});
  await page.goto(base + '/');
  check(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), 'About section overflows at the 200% zoom-equivalent CSS viewport');
  const zoomEquivalent = await page.locator('#about .about-founder-photo').evaluate(img => ({width:img.getBoundingClientRect().width,height:img.getBoundingClientRect().height}));
  check(zoomEquivalent.width > 220 && zoomEquivalent.height > 250, 'Founder portrait becomes too small in the 200% zoom-equivalent layout');
  await page.evaluate(() => {
    const aboutTop = document.querySelector('#about').getBoundingClientRect().top + window.scrollY;
    window.scrollTo(0, Math.max(0, aboutTop - 100));
  });
  await page.locator('#about').screenshot({path:'.playwright-cli/m05-about-720.png'});
  const grid = page.locator('.home-project-grid');
  const originalCount = await grid.locator(':scope>.portfolio-card').count();
  check(originalCount <= 6, 'More than six projects on homepage');
  await page.setViewportSize({width:390,height:844});
  const scrollCheck = await page.evaluate(() => {
    const primary = document.querySelector('.home-hero-primary').getBoundingClientRect();
    const projects = document.getElementById('projects').getBoundingClientRect();
    document.documentElement.style.scrollBehavior = 'auto';
    return {
      beforeProjects: Math.max(primary.bottom + scrollY + 100, projects.top + scrollY - innerHeight - 320),
    };
  });
  await page.evaluate(y => window.scrollTo(0,y), scrollCheck.beforeProjects);
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  check(await page.locator('[data-home-sticky-cta]').isHidden(), 'Sticky contact CTA appears before the calculator');
  await page.evaluate(() => {
    const projects = document.getElementById('projects').getBoundingClientRect();
    window.scrollTo(0, projects.top + scrollY + 200);
  });
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const stickyOrClear = await page.evaluate(() => {
    const cta = document.querySelector('[data-home-sticky-cta]');
    if (cta.hidden) return true;
    const bounds = cta.getBoundingClientRect();
    return [...document.querySelectorAll('#projects button, #projects a')].every(control => {
      const box = control.getBoundingClientRect();
      return !box.width || !box.height || box.bottom <= bounds.top || box.top >= bounds.bottom
        || box.right <= bounds.left || box.left >= bounds.right;
    });
  });
  check(stickyOrClear, 'Sticky contact CTA overlaps a portfolio control');
  const dimensions = [];
  for (const [width, columns] of [[1920,3],[1440,3],[1280,3],[1100,3],[1099,2],[1024,2],[801,2],[800,1],[768,1],[641,1],[390,1],[360,1],[320,1]]) {
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
    check(await gallery.locator('img[data-src]').count() > 0, 'Hidden carousel photos downloaded before interaction');
    const leadImage = gallery.locator('img').first();
    await leadImage.evaluate(img => img.decode());
    const imageContract = await leadImage.evaluate(img => ({
      srcset: img.srcset, sizes: img.sizes, currentSrc: img.currentSrc,
      width: img.width, height: img.height, naturalWidth: img.naturalWidth,
    }));
    check(imageContract.srcset.includes('/thumb/') && imageContract.srcset.includes('/full/'), 'Project preview does not offer responsive public derivatives');
    check(imageContract.sizes.includes('/ 3') && imageContract.width > 0 && imageContract.height > 0 && imageContract.naturalWidth > 0, 'Project image dimensions or sizes are missing');
    await gallery.getByRole('button',{name:'Следующая фотография',exact:true}).click();
    check(await gallery.locator('[data-photo-number]').innerText() === '2', 'Gallery arrows stopped working');
    await gallery.locator('.project-carousel-slide').nth(1).locator('img').evaluate(img => img.decode());
    await gallery.locator('.project-carousel-track').press('ArrowLeft');
    check(await gallery.locator('[data-photo-number]').innerText() === '1', 'Gallery keyboard navigation stopped working');
    const track = gallery.locator('.project-carousel-track');
    const box = await track.boundingBox();
    await page.mouse.move(box.x + box.width * .8, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * .2, box.y + box.height / 2, {steps:8});
    await page.mouse.up();
    await page.waitForFunction(() => document.querySelector('[data-photo-number]')?.textContent === '2');
    await track.press('ArrowLeft');
    check(await gallery.locator('[data-photo-number]').innerText() === '1', 'Gallery did not return to its saved cover');
  }
  const homeCards = grid.locator(':scope>.portfolio-card');
  for (let index = 0; index < await homeCards.count(); index += 1) {
    const image = homeCards.nth(index).locator('img').first();
    await image.scrollIntoViewIfNeeded();
    await image.evaluate(img => img.decode());
  }
  await grid.scrollIntoViewIfNeeded();
  await grid.screenshot({path:'.playwright-cli/home-projects-large.png'});
  // Six-card layout fixture lives only in the browser, never in the database.
  await grid.evaluate(node => { while(node.children.length < 6 && node.firstElementChild) node.append(node.firstElementChild.cloneNode(true)); });
  const rows = await grid.locator(':scope>.portfolio-card').evaluateAll(nodes => new Set(nodes.map(node=>Math.round(node.getBoundingClientRect().top))).size);
  check(rows === 2, 'Six cards do not form two desktop rows');
  const frames = await grid.locator(':scope>.portfolio-card').evaluateAll(cards => cards.map(card => { const box=card.getBoundingClientRect(); const image=card.querySelector('img').getBoundingClientRect(); return {width:box.width,height:box.height,ratio:image.width/image.height}; }));
  check(Math.max(...frames.map(x=>x.height))-Math.min(...frames.map(x=>x.height)) < 2, 'Homepage card heights differ');
  check(frames.every(x=>Math.abs(x.ratio-1.5)<.02), 'Homepage photos are not consistently 3:2');
  const textRows = await grid.locator(':scope>.portfolio-card').evaluateAll(cards=>cards.map(card=>({
    row:Math.round(card.getBoundingClientRect().top),
    location:card.querySelector('.portfolio-card-info>p').getBoundingClientRect().top,
    summary:card.querySelector('.project-card-summary').getBoundingClientRect().top,
    action:card.querySelector('.portfolio-card-info>.text-link').getBoundingClientRect().top,
  })));
  for(const row of new Set(textRows.map(card=>card.row))){
    const cards=textRows.filter(card=>card.row===row);
    for(const field of ['location','summary','action'])check(Math.max(...cards.map(card=>card[field]))-Math.min(...cards.map(card=>card[field]))<2,'Card '+field+' is not aligned when a project has no category');
  }

  const portraits = await grid.locator('img[src][data-portrait]').evaluateAll(nodes => nodes.map(img => ({width:img.getBoundingClientRect().width,height:img.getBoundingClientRect().height,fit:getComputedStyle(img).objectFit})));
  check(portraits.length > 0 && portraits.every(img => img.fit === 'contain' && Math.abs(img.width/img.height-1.5)<.02), 'Portrait photos must remain fully visible inside the common homepage frame');
  await page.locator('.home-project-footer a').click();
  check(new URL(page.url()).pathname === '/projects/', 'View-all does not open the catalogue');
  const catalogGrid = page.locator('.portfolio-grid');
  const catalogCount = await catalogGrid.locator(':scope>.portfolio-card').count();
  check(catalogCount >= originalCount, 'Catalogue lost projects');
  for (const width of [320,360,390,641,768,800,801,1024,1280,1440,1920]) {
    await page.setViewportSize({width,height:1000});
    await catalogGrid.scrollIntoViewIfNeeded();
    const actual = await catalogGrid.evaluate(node => getComputedStyle(node).gridTemplateColumns.split(' ').length);
    check(actual === (width <= 800 ? 1 : 2), 'Wrong catalogue column count at ' + width);
    check(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), 'Catalogue overflow at ' + width);
  }
  await page.setViewportSize({width:1440,height:1000});
  const coverImages = catalogGrid.locator(':scope>.portfolio-card img');
  const coverOrientations = [];
  for (let index = 0; index < catalogCount; index += 1) {
    const image = coverImages.nth(index);
    await image.scrollIntoViewIfNeeded();
    const naturalWidth = await image.evaluate(async img => {
      if (!img.complete || !img.naturalWidth) await new Promise(resolve => {
        img.addEventListener('load', () => resolve(), {once:true});
        img.addEventListener('error', () => resolve(), {once:true});
        setTimeout(resolve, 6000);
      });
      return img.naturalWidth;
    });
    check(naturalWidth > 0, 'A published portfolio cover failed to load at index ' + index);
    if (index < 2) {
      const dimensions = await image.evaluate(img => ({width:img.naturalWidth,height:img.naturalHeight}));
      coverOrientations.push(dimensions.width > dimensions.height ? 'landscape' : 'portrait');
    }
  }
  check(new Set(coverOrientations).size === 2, 'The catalogue did not exercise both landscape and portrait covers');
  const wideSource = await coverImages.first().evaluate(img => img.currentSrc);
  check(await catalogGrid.locator('img[data-portrait]').evaluateAll(nodes => nodes.every(img=>getComputedStyle(img).objectFit==='contain')), 'Catalogue portrait photos are cropped');
  check(wideSource.includes('/full/'), 'A large desktop card did not select the full-size WebP derivative');

  await page.setViewportSize({width:390,height:844});
  await page.goto(base + '/projects/');
  const mobileImage = page.locator('.portfolio-grid>.portfolio-card img').first();
  await mobileImage.scrollIntoViewIfNeeded();
  await mobileImage.evaluate(img => img.decode());
  check((await mobileImage.evaluate(img => img.currentSrc)).includes('/thumb/'), 'A mobile card did not select the thumbnail derivative');

  const portraitPath = await page.locator('.portfolio-grid>.portfolio-card').nth(1).locator('.portfolio-card-image').getAttribute('href');
  await page.goto(base + portraitPath);
  const caseCover = page.locator('.case-cover img');
  await caseCover.evaluate(img => img.decode());
  const caseCoverData = await caseCover.evaluate(img => ({
    naturalWidth:img.naturalWidth, naturalHeight:img.naturalHeight,
    objectFit:getComputedStyle(img).objectFit, srcset:img.srcset, currentSrc:img.currentSrc,
  }));
  check(caseCoverData.naturalHeight > caseCoverData.naturalWidth && caseCoverData.objectFit === 'contain', 'A portrait project cover was cropped on its detail page');
  check(caseCoverData.srcset.includes('/thumb/') && caseCoverData.srcset.includes('/full/'), 'A project detail cover lost responsive derivatives');
  await page.locator('.case-cover a').click();
  await page.locator('dialog.gallery-dialog[open]').waitFor();
  const dialogFit = await page.locator('.gallery-stage img').evaluate(img => getComputedStyle(img).objectFit);
  check(dialogFit === 'contain', 'The full-image viewer cropped a portrait photo');
  await page.keyboard.press('Escape');
  check(await page.locator('dialog.gallery-dialog[open]').count() === 0, 'Escape did not close the image viewer');

  const slowContext = await page.context().browser().newContext({viewport:{width:1440,height:960}});
  const slowPage = await slowContext.newPage();
  let slowImageRequests = 0;
  await slowPage.route('**/project-media/**', async route => {
    slowImageRequests += 1;
    await new Promise(resolve => setTimeout(resolve, 500));
    await route.continue();
  });
  await slowPage.goto(base + '/');
  const slowGrid = slowPage.locator('.home-project-grid');
  await slowGrid.scrollIntoViewIfNeeded();
  for (let attempt = 0; attempt < 25 && !slowImageRequests; attempt += 1) await slowPage.waitForTimeout(20);
  check(slowImageRequests > 0, 'The slow-network check did not intercept a portfolio image');
  const slowImage = slowGrid.locator('img').first();
  const boxBefore = await slowImage.boundingBox();
  await slowPage.waitForTimeout(120);
  const boxDuring = await slowImage.boundingBox();
  check(Math.abs(boxBefore.height - boxDuring.height) < 1, 'A delayed image shifted its reserved layout frame');
  await slowImage.evaluate(img => img.decode());
  const boxAfter = await slowImage.boundingBox();
  check(Math.abs(boxBefore.height - boxAfter.height) < 1, 'A loaded image shifted its reserved layout frame');
  await slowContext.close();
  check(!mediaErrors.length, mediaErrors.join('; '));
  check(!errors.length, errors.join('; '));
  return { aboutLayouts, zoomEquivalent, maximum:6, dimensions, sixCards:'two equal rows on desktop', catalogProjects:catalogCount, catalogue:'two-column desktop and one-column tablet/mobile', gallery:'arrows, keyboard, drag and full portrait viewing preserved', responsiveImages:'mobile thumbnail and desktop full derivative selected', stickyCta:'visible before portfolio and hidden while portfolio is in view', delayedImage:'reserved frame prevented layout shift', mediaErrors, errors };
}
