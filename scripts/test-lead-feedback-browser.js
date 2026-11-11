async page => {
 const message='Спасибо! Ваша заявка успешно отправлена. Наш специалист свяжется с вами в ближайшее время.';
 const check=(ok,msg)=>{if(!ok)throw Error(msg)};const report=[];
 for(const width of [1440,390]) for(const entry of [
  {path:'/',selector:'#contact-form'},
  {path:'/request/measurement/',selector:'[data-lead-form]'},
  {path:'/partners/',selector:'[data-lead-form]'},
  {path:'/calculator/',selector:'[data-lead-form]',quick:true}
 ]) {
  await page.setViewportSize({width,height:900});
  await page.goto('http://localhost:8000'+entry.path,{waitUntil:'domcontentloaded'});
  if(await page.locator('[data-privacy-panel]').isVisible())await page.locator('[data-privacy-essential]').click();
  const f=page.locator(entry.selector);
  if(entry.quick) {
   await f.locator('[name=object_type][value=apartment]').check();await f.locator('[name=area_m2]').fill('35');await f.locator('[name=solution]').first().check();await f.locator('[data-calculate]').click();
  }
  await f.locator('[name=name]').fill('Проверка интерфейса');await f.locator('[name=contact]').fill('+79000000000');await f.locator('[name=consent]').check();
  const submit=f.locator('button[type=submit]:not([data-calculate])');let release;const gate=new Promise(resolve=>release=resolve);let requests=0;
  await page.route('**/api/leads/',async r=>{requests++;await gate;await r.fulfill({status:201,contentType:'application/json',body:JSON.stringify({ok:true,kind:entry.quick?'calculator':'consultation',reference:'ui-only',message})});});
  await submit.click();await page.waitForFunction(selector=>document.querySelector(selector).getAttribute('aria-busy')==='true',entry.selector);
  check(await submit.isDisabled(),'Not protected during sending');check(await submit.innerText()==='Отправляем заявку…','Sending text missing');
  release();await page.waitForFunction(selector=>document.querySelector(selector).dataset.submitted==='true',entry.selector);
  check(await submit.isEnabled(),'Button stayed disabled');check(await submit.innerText()==='Заявка отправлена','Success label missing');
  const status=f.locator('[data-lead-status]');check(await status.innerText()===message,'Wrong success text');check(await status.getAttribute('data-state')==='success','Success styling missing');
  check(await f.locator('[name=name]').isEnabled(),'Form greyed out');check(await f.locator('.lead-measurement-note').count()===1,'Measurement information missing');
  await submit.click();check(requests===1,'Duplicate request');
  await status.screenshot({path:'.playwright-cli/success-'+width+'-'+(entry.quick?'calculator':entry.path.includes('partners')?'partner':entry.path==='/'?'home':'measurement')+'.png'});
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Page overflows');
  await page.unroute('**/api/leads/');report.push({width,path:entry.path,status:'pass'});
 }
 return report;
}
