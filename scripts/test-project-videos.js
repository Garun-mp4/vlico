async page => {
  const check = (condition, message) => { if (!condition) throw Error(message); };
  const base = new URL(page.url()).origin;
  const errors = [];
  const requestedVideos = [];
  const isVideo = url => /\/project-videos\/[^/]+\.mp4$/.test(new URL(url).pathname);
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => { if (isVideo(request.url())) requestedVideos.push(request.url()); });
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto(base + '/');
  if (await page.locator('[data-privacy-panel]').isVisible()) await page.getByRole('button', {name:'Отклонить',exact:true}).click();
  const section = page.locator('#project-videos');
  const rail = section.locator('.project-videos-rail');
  const links = section.locator('[data-project-video]');
  const dialog = page.locator('[data-video-dialog]');
  const player = dialog.locator('video');
  check(await links.count() === 7, 'All seven client videos must be present');
  check(await player.getAttribute('src') === null, 'Initial player already has a source');
  const nextSection = await section.evaluate(node => node.previousElementSibling.id);
  check(nextSection === 'solutions', 'Videos must immediately follow solutions');
  const layouts = [];
  for (const width of [320,390,768,800,801,1024,1099,1100,1440,1920]) {
    await page.setViewportSize({width,height:1000});
    await section.scrollIntoViewIfNeeded();
    const geometry = await rail.evaluate(node => {
      const rail = node.getBoundingClientRect();
      const card = node.firstElementChild.getBoundingClientRect();
      return {width:rail.width,cardWidth:card.width,gap:parseFloat(getComputedStyle(node).gap)};
    });
    const expected = width >= 1100 ? 4 : width >= 761 ? 2 : 1;
    if (expected === 1) check(geometry.cardWidth < geometry.width && geometry.cardWidth > geometry.width*.8, 'Mobile next-card cue is missing');
    else check(Math.abs(geometry.cardWidth*expected+geometry.gap*(expected-1)-geometry.width)<2, 'Wrong video column count at '+width);
    check(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth+1), 'Document overflows at '+width);
    layouts.push({width,visible:expected});
  }
  check(requestedVideos.length === 0, 'Video bytes downloaded before a play action');
  await page.setViewportSize({width:1440,height:1000});
  await rail.press('End');
  check(await section.locator('[data-video-next]').isDisabled(), 'Last arrow is not disabled');
  await rail.press('Home');
  await page.waitForFunction(() => document.querySelector('[data-video-prev]').disabled);
  await section.locator('[data-video-next]').click();
  check(await rail.evaluate(node => node.scrollLeft)>0, 'Video arrow does not scroll');
  await rail.press('Home');
  await section.screenshot({path:'.playwright-cli/project-videos-1440.png'});
  const files = await links.evaluateAll(nodes => nodes.map(node => node.href));
  for (let index=0; index<files.length; index++) {
    const range = await page.request.get(files[index],{headers:{Range:'bytes=0-1023'}});
    check(range.status()===206, 'Video server does not support byte ranges: '+index);
    check((await range.body()).length===1024, 'Incorrect range length: '+index);
    const before = requestedVideos.length;
    await links.nth(index).click();
    await page.waitForFunction(() => {
      const video = document.querySelector('[data-video-dialog] video');
      return video.readyState>=3 && !video.paused && video.currentTime>0;
    });
    check(await dialog.isVisible(), 'Dialog did not open: '+index);
    check(await player.evaluate(node => node.videoHeight>node.videoWidth), 'Portrait video dimensions changed');
    check(requestedVideos.slice(before).every(url=>url===files[index]), 'Opening one video fetched another video');
    const duration = await player.evaluate(node => node.duration);
    await player.evaluate(node => { node.currentTime=node.duration/2; });
    await page.waitForFunction(() => !document.querySelector('[data-video-dialog] video').seeking);
    check(await player.evaluate(node=>node.currentTime)>duration/3, 'Seeking failed: '+index);
    if (index === 0) {
      await dialog.locator('[data-video-fullscreen]').click();
      await page.waitForFunction(() => !!document.fullscreenElement);
      await page.evaluate(() => document.exitFullscreen());
      await dialog.screenshot({path:'.playwright-cli/project-video-player-1440.png'});
    }
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => !document.querySelector('[data-video-dialog]').open);
    check(await player.getAttribute('src') === null && await player.evaluate(node=>node.paused), 'Closed video still has a source or is playing');
    check(await links.nth(index).evaluate(node=>document.activeElement===node), 'Focus did not return to opener');
  }
  await page.setViewportSize({width:390,height:844});
  await rail.press('Home');
  await section.scrollIntoViewIfNeeded();
  await section.screenshot({path:'.playwright-cli/project-videos-390.png'});
  await links.first().click();
  await page.waitForFunction(() => document.querySelector('[data-video-dialog] video').readyState>=3);
  check(await page.locator('[data-home-sticky-cta]').isHidden(), 'Mobile CTA covers the player');
  await dialog.screenshot({path:'.playwright-cli/project-video-player-390.png'});
  await dialog.locator('[data-video-close]').click();
  await page.route('**/project-videos/*.mp4',route=>route.abort());
  await links.first().click();
  await dialog.locator('[data-video-retry]').waitFor({state:'visible'});
  check(await dialog.locator('[data-video-fallback]').isVisible(), 'Failed video has no direct-file fallback');
  await page.unroute('**/project-videos/*.mp4');
  await dialog.locator('[data-video-retry]').click();
  await page.waitForFunction(() => document.querySelector('[data-video-dialog] video').readyState>=3 && !document.querySelector('[data-video-dialog] video').paused);
  await dialog.locator('[data-video-close]').click();
  check(!errors.length,errors.join('; '));
  return {videos:files.length,initialVideoRequests:0,layouts,playback:'all seven',rangeRequests:'206 / 1024 bytes for all files',fullscreen:'Chromium passed',close:'source released and focus restored',retry:'passed',errors};
}
