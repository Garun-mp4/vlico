async page => {
 const errors=[]; page.on('pageerror', e=>errors.push(e.message));
 const check=(ok,msg)=>{if(!ok)throw Error(msg)};
 const origin='http://localhost:8000';
 await page.goto(origin,{waitUntil:'domcontentloaded'});
 if(await page.locator('[data-privacy-panel]').isVisible()) await page.locator('[data-privacy-essential]').click();
 const report=[];
 for(const width of [1440,1024,768,390,320]) {
  await page.setViewportSize({width,height:900});
  await page.goto(origin,{waitUntil:'domcontentloaded'});
  await page.locator('.new-solutions img').first().scrollIntoViewIfNeeded();
  await page.locator('.new-solutions img').first().evaluate(im=>im.decode());
  check(await page.locator('.new-solution').count()===3,'Three new cards missing');
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Home overflow '+width);
  check(await page.locator('#about-title').innerText()==='ПОТОЛОК — ОСНОВА КРАСИВОГО ИНТЕРЬЕРА','About copy');
  await page.locator('.new-solutions').screenshot({path:'.playwright-cli/new-cards-'+width+'.png'});
  if(width===390) {
   const rail=page.locator('.new-solutions-rail');
   await rail.press('End');
   await page.locator('.new-solution').last().scrollIntoViewIfNeeded();
   check(await rail.evaluate(el=>el.scrollLeft>0),'Mobile rail does not scroll');
  }
  await page.goto(origin+'/partners/',{waitUntil:'domcontentloaded'});
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Partner overflow '+width);
  await page.getByRole('link',{name:/Обсудить сотрудничество/}).first().click();
  check(await page.locator('#partner-form').isVisible(),'Embedded partner form');
  check(await page.locator('#partner-form select[name=contact_method]').count()===1,'Contact preference missing');
  if(width===390||width===1440) await page.locator('#partner-form').screenshot({path:'.playwright-cli/partner-'+width+'.png'});
  await page.goto(origin+'/projects/ceiling-installation-detail/',{waitUntil:'domcontentloaded'});
  check(await page.locator('.installation-pair figure').count()===2,'Before after missing');
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Case overflow '+width);
  if(width===390||width===1440) await page.locator('.installation-comparison').screenshot({path:'.playwright-cli/before-after-'+width+'.png'});
  report.push({width,status:'ok'});
 }
 await page.setViewportSize({width:1440,height:1000});
 await page.goto(origin+'/contacts/',{waitUntil:'domcontentloaded'});
 await page.locator('.review-offer').screenshot({path:'.playwright-cli/review-offer.png'});
 check((await page.locator('.review-offer a').getAttribute('href')).includes('164382623295'),'Wrong reviews target');
 for(const slug of ['karniz-dlya-natyazhnogo-potolka-vybor','natiazhnoi-potolok-kak-sozdat-stilnyj-i-praktichnyi-interer']) {
  await page.goto(origin+'/blog/'+slug+'/',{waitUntil:'domcontentloaded'});
  await page.locator('.blog-cover').evaluate(im=>im.decode());
  check((await page.locator('.blog-photo-caption').first().innerText()).includes('ИИ'),'Illustration provenance missing');
 }
 check(errors.length===0,JSON.stringify(errors));
 return {report,errors};
}
