async page => {
 const check=(ok,msg)=>{if(!ok)throw Error(msg)}; const origin='http://localhost:8000';const results=[];const errors=[];
 page.on('pageerror',e=>errors.push(e.message));await page.emulateMedia({reducedMotion:'reduce'});
 for(const [width,height] of [[320,568],[360,640],[390,844],[768,1024],[1024,768],[1280,720],[1440,900]]) {
  await page.setViewportSize({width,height});await page.goto(origin,{waitUntil:'domcontentloaded'});
  await page.evaluate(()=>{localStorage.removeItem('vlicoPrivacy');document.documentElement.style.scrollBehavior='auto'});await page.reload({waitUntil:'domcontentloaded'});
  const panel=page.locator('[data-privacy-panel]');await panel.waitFor({state:'visible'});
  const geometry=await panel.evaluate(el=>({position:getComputedStyle(el).position,rect:el.getBoundingClientRect().toJSON()}));
  check(geometry.position==='fixed','Cookie panel is not floating '+width);check(geometry.rect.bottom<=height+1&&geometry.rect.bottom>=height-22,'Cookie bottom '+width);check(geometry.rect.left<=22,'Cookie left '+width);check(geometry.rect.width<=Math.min(480,width-24)+1,'Cookie width '+width);
  if(width===390||width===1280)await page.screenshot({path:'.playwright-cli/refined-cookie-'+width+'.png'});
  await panel.getByRole('button',{name:'Отклонить',exact:true}).click();
  const rail=page.locator('.new-solutions-rail');check(await page.locator('.home-hero .new-solutions').count()===1,'Solutions not attached to hero');
  await page.evaluate(()=>document.fonts.ready);
  const next=page.locator('[data-solutions-next]'),prev=page.locator('[data-solutions-prev]');
  if(width<=1100){
   await next.scrollIntoViewIfNeeded();check(await prev.isDisabled(),'Initial previous should be disabled');const y=await page.evaluate(()=>scrollY);
   await next.click();await page.waitForFunction(()=>document.querySelector('.new-solutions-rail').scrollLeft>20&&!document.querySelector('[data-solutions-prev]').disabled);
   check(Math.abs(await page.evaluate(()=>scrollY)-y)<3,'Carousel moved the page');check(await prev.isEnabled(),'Previous did not enable');
   if(await next.isEnabled())await next.click();await page.waitForFunction(()=>document.querySelector('[data-solutions-next]').disabled);
   check(await page.locator('[data-solutions-count]').innerText()==='3 / 3','Incorrect end counter');await prev.click();await page.waitForFunction(()=>document.querySelector('[data-solutions-prev]').disabled===(document.querySelector('.new-solutions-rail').scrollLeft<=2));if(await prev.isEnabled())await prev.click();
   await page.waitForFunction(()=>document.querySelector('[data-solutions-prev]').disabled);
   check(await page.locator('[data-solutions-count]').innerText()==='1 / 3','Incorrect start counter');
  } else check(await page.locator('[data-solutions-controls]').isHidden(),'Desktop has unnecessary arrows');
  if(width===390||width===1280)await page.locator('.new-solutions').screenshot({path:'.playwright-cli/refined-solutions-'+width+'.png'});
  check(await page.locator('.approach-step').count()===5,'Five process steps missing');
  check((await page.locator('#approach-title').innerText()).replace(/\s+/g,' ').trim()==='СОВЕРШЕНСТВО НАЧИНАЕТСЯ С ДЕТАЛЕЙ.','Process heading mismatch');
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Homepage overflow '+width);
  if(width===390||width===1280)await page.locator('#approach').screenshot({path:'.playwright-cli/refined-process-'+width+'.png'});
  const partner=page.locator('.partners-home-entry');await partner.scrollIntoViewIfNeeded();
  check(await partner.locator('img').count()===1,'Partnership photo missing');check((await partner.locator('img').getAttribute('src')).includes('partnership-studio'),'Wrong partnership illustration');check((await partner.innerText()).includes('ремонтных компаний'),'Audience missing');
  if(width===390||width===1280)await partner.screenshot({path:'.playwright-cli/refined-partner-'+width+'.png'});
  await partner.getByRole('link',{name:'Стать партнёром',exact:false}).click();await page.waitForURL('**/partners/#partner-form');
  check(await page.locator('#partner-form [name=company]').count()===1,'Company field missing');check(await page.locator('#partner-form [name=contact_method]').count()===1,'Contact choice missing');
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Partner overflow '+width);
  await page.goto(origin+'/services/smart-home/',{waitUntil:'domcontentloaded'});
  check((await page.locator('.service-hero img').getAttribute('src')).includes('alice-smart-home'),'Wrong Alice image');
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Service overflow '+width);
  results.push({width,height,status:'pass'});
 }
 const browser=page.context().browser(), touch=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,reducedMotion:'reduce'});
 try {
  const mobile=await touch.newPage();await mobile.goto(origin,{waitUntil:'domcontentloaded'});await mobile.locator('[data-privacy-essential]').tap();
  await mobile.locator('.new-solutions img').first().scrollIntoViewIfNeeded();
  await mobile.evaluate(()=>document.fonts.ready);
  const bounds=await mobile.locator('.new-solution img').first().boundingBox();const cdp=await touch.newCDPSession(mobile);
  const x=bounds.x+bounds.width-20,y=bounds.y+bounds.height/2;
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
  for(let step=1;step<=8;step++)await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x-step*25,y}]});
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await mobile.waitForFunction(()=>document.querySelector('.new-solutions-rail').scrollLeft>50);
  check(await mobile.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Touch swipe causes page overflow');
 }finally{await touch.close()}
 check(errors.length===0,errors.join('; '));return {results,touchSwipe:true,errors};
}
