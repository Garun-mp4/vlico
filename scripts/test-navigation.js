async page => {
  const check = (value, message) => { if (!value) throw Error(message); };
  const origin = 'http://127.0.0.1:8000';
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.setViewportSize({width:1440,height:960});
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.goto(origin + '/projects/');
  if (await page.getByRole('button',{name:'Отклонить',exact:true}).isVisible()) await page.getByRole('button',{name:'Отклонить',exact:true}).click();
  const root = page.locator('.desktop-nav [data-project-nav]');
  const toggle = root.getByRole('button',{name:'Направления проектов'});
  const panel = page.locator('#desktop-projects');
  const preview = page.locator('.service-preview--navigation');
  const expanded = value => page.waitForFunction(expected => document.querySelector('.desktop-nav [data-project-nav] button').getAttribute('aria-expanded') === expected, String(value));
  await root.hover(); await expanded(true);
  await page.keyboard.press('Escape'); await expanded(false);
  await page.mouse.move(0,500); await root.hover(); await expanded(true);
  await page.waitForFunction(() => getComputedStyle(document.querySelector('#desktop-projects')).opacity === '1');
  const directions = panel.locator('[data-service-preview]');
  check(await directions.count() >= 6, 'Direction previews missing');
  for (let index=0; index<await directions.count(); index++) {
    const link = directions.nth(index), src = await link.getAttribute('data-service-preview');
    await link.hover();
    await page.waitForFunction(expected => {
      const card = document.querySelector('.service-preview--navigation');
      return card.classList.contains('is-visible') && card.querySelector('.is-current')?.getAttribute('src') === expected;
    }, src);
    check(await preview.locator('.is-current').evaluate(image => image.naturalWidth > 0), 'Broken direction image');
  }
  await directions.first().hover();
  const inertia = await directions.first().evaluate(async link => {
    const box=link.getBoundingClientRect(), card=document.querySelector('.service-preview--navigation');
    const before=card.style.transform;
    link.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,pointerType:'mouse',clientX:box.right-5,clientY:box.top+box.height/2}));
    const deferred=card.style.transform===before;
    await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    return {deferred,moved:card.style.transform!==before};
  });
  check(inertia.deferred && inertia.moved, 'No inertial movement');
  await page.waitForTimeout(1000);
  const still=await preview.getAttribute('style'); await page.waitForTimeout(150);
  check(await preview.getAttribute('style')===still,'Animation runs while idle');
  const imageBox=await preview.boundingBox(), menuBox=await panel.boundingBox();
  check(imageBox.x+imageBox.width < menuBox.x || imageBox.x > menuBox.x+menuBox.width,'Preview covers menu links');
  check(imageBox.x>=0 && imageBox.y>=0 && imageBox.x+imageBox.width<=1440 && imageBox.y+imageBox.height<=960,'Preview exceeds viewport');
  await page.screenshot({path:'.playwright-cli/navigation-desktop-final.png'});
  const title=await directions.first().innerText();
  await directions.first().click(); await page.waitForURL('**/projects/?category=*');
  check((await page.locator('h1').innerText()).toLowerCase()===title.toLowerCase(),'Category page heading mismatch');
  await page.mouse.move(0,500); await toggle.focus(); await page.keyboard.press('Enter'); await expanded(true);
  await page.keyboard.press('ArrowDown');
  check(await panel.getByRole('link',{name:'Все проекты'}).evaluate(link => link===document.activeElement),'Keyboard cannot enter dropdown');
  await page.keyboard.press('Tab');
  await page.waitForFunction(() => document.querySelector('.service-preview--navigation').classList.contains('is-visible'));
  await page.keyboard.press('Escape'); await expanded(false);
  check(await toggle.evaluate(button => button===document.activeElement),'Escape loses focus');
  check(!await preview.evaluate(card=>card.classList.contains('is-visible')),'Escape leaves preview behind');
  await page.keyboard.press('ArrowDown'); await panel.locator('a').last().focus(); await page.keyboard.press('Tab'); await expanded(false);
  await root.hover(); await expanded(true); await page.locator('h1').click(); await expanded(false);
  await page.emulateMedia({reducedMotion:'reduce'}); await root.hover(); await directions.first().hover();
  await page.waitForFunction(()=>document.querySelector('.service-preview--navigation').classList.contains('is-visible'));
  const reduced=await preview.getAttribute('style'), box=await directions.first().boundingBox();
  await page.mouse.move(box.x+box.width*.8,box.y+box.height/2);
  check(await preview.getAttribute('style')===reduced,'Reduced motion still tracks pointer');
  for (const width of [1920,1280,1024,961,960,768,640,390,320]) {
    await page.setViewportSize({width,height:900});
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Horizontal overflow at '+width);
    check(await page.locator('.desktop-nav').isVisible()===(width>960),'Wrong navigation breakpoint at '+width);
  }
  const context=await page.context().browser().newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const mobile=await context.newPage(); let downloads=0;
  mobile.on('request',request=>{if(request.url().includes('/service-previews/'))downloads++;});
  await mobile.goto(origin+'/projects/');
  if (await mobile.getByRole('button',{name:'Отклонить',exact:true}).isVisible()) await mobile.getByRole('button',{name:'Отклонить',exact:true}).click();
  await mobile.getByLabel('Открыть меню',{exact:true}).tap();
  const mobileMenu=mobile.locator('[data-header-mobile]');
  await mobileMenu.getByRole('button',{name:'Направления проектов'}).tap();
  await mobile.screenshot({path:'.playwright-cli/navigation-mobile-final.png'});
  const mobileLink=mobileMenu.locator('a[href*="?category="]').first(), mobileTitle=await mobileLink.innerText();
  await mobileLink.tap(); await mobile.waitForURL('**/projects/?category=*');
  check((await mobile.locator('h1').innerText()).toLowerCase()===mobileTitle.toLowerCase(),'Touch category failed');
  check(!await mobileMenu.evaluate(menu=>menu.open),'Mobile menu did not close');
  check(downloads===0,'Touch downloads decorative service images');
  check(await mobile.locator('.service-preview.is-visible').count()===0,'Touch preview active');
  await mobile.getByLabel('Открыть меню',{exact:true}).tap();
  await mobile.touchscreen.tap(5,500); check(!await mobileMenu.evaluate(menu=>menu.open),'Outside tap did not close navigation');
  await context.close();
  const noJSContext=await page.context().browser().newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
  const noJS=await noJSContext.newPage(); await noJS.goto(origin+'/contacts/');
  await noJS.getByLabel('Открыть меню',{exact:true}).click();
  await noJS.locator('[data-header-mobile]').getByRole('link',{name:'Проекты',exact:true}).click(); await noJS.waitForURL('**/projects/');
  await noJSContext.close();
  await page.setViewportSize({width:1440,height:960});
  for (const path of ['/projects/','/calculator/','/services/','/services/shadow/']) {
    await page.goto(origin+path);
    const active=page.locator('.desktop-nav a[aria-current]').first(); await active.hover();
    check(await active.evaluate(link => getComputedStyle(link).textDecorationLine==='none' && getComputedStyle(link,'::after').height==='1px'),'Duplicate active-link underline at '+path);
  }
  check(!errors.length,errors.join(';'));
  return {directions:await directions.count(),inertia,categoryNavigation:true,keyboard:true,reducedMotion:true,responsiveWidths:9,touch:true,touchDecorativeDownloads:downloads,noJavaScript:true,singleActiveUnderline:true,pageErrors:errors};
}
