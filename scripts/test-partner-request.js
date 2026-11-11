async page => {
 const check=(ok,message)=>{if(!ok)throw Error(message)};
 const origin='http://localhost:8000',errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.emulateMedia({reducedMotion:'reduce'});
 for(const width of [1440,820,390])for(const path of ['/partners/','/request/partner/']){
  await page.setViewportSize({width,height:900});await page.goto(origin+path,{waitUntil:'domcontentloaded'});
  if(await page.locator('[data-privacy-panel]').isVisible())await page.locator('[data-privacy-essential]').click();
  const form=page.locator('[data-lead-form]');
  check(await form.locator('input[type=file]').count()===0,'Upload control remains');
  check(await form.getAttribute('enctype')!=='multipart/form-data','Native form still multipart');
  for(const name of ['name','contact','company','contact_method'])check(await form.locator('[name='+name+']').count()===1,'Missing '+name);
  check(await form.locator('[name=name]').getAttribute('required')!==null,'Name is optional');
  check(await form.locator('[name=contact]').getAttribute('required')!==null,'Phone is optional');
  check(await form.locator('[name=company]').getAttribute('required')===null,'Company must be optional');
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Overflow '+width);
 }
 let requests=0,body='';
 await page.route('**/api/leads/',async route=>{
  requests++;body=route.request().postData()||'';check(!body.includes('filename=')&&!body.includes('name="attachment"'),'File included in submission');
  if(requests===1)return route.abort('failed');
  if(requests===2)return route.fulfill({status:400,contentType:'application/json',body:JSON.stringify({ok:false,errors:{contact:['Укажите телефон с кодом страны.']}})});
  return route.fulfill({status:201,contentType:'application/json',body:JSON.stringify({ok:true,kind:'partner',reference:'ui-only',new_request_url:'/request/partner/',message:'Спасибо! Ваша заявка успешно отправлена. Наш специалист свяжется с вами в ближайшее время.'})});
 });
 const form=page.locator('[data-lead-form]'),phone=form.locator('[name=contact]');
 await form.locator('[name=name]').fill('Тестовый дизайнер');await phone.fill('+79000000000');await form.locator('[name=company]').fill('Studio North');await form.locator('[name=contact_method]').selectOption('telegram');await form.locator('[name=consent]').check();
 await form.locator('[type=submit]').click();await page.waitForFunction(()=>document.querySelector('[data-lead-errors]').textContent.includes('Связь прервалась'));
 check(await phone.inputValue()==='+79000000000','Network failure discarded phone');
 await form.locator('[type=submit]').click();await form.locator('[data-field-error]').waitFor();
 check(await phone.getAttribute('aria-invalid')==='true','Validation is not associated with phone');
 check((await phone.getAttribute('aria-describedby')).includes('server-error'),'Validation description missing');
 await phone.fill('+79000000001');check(await form.locator('[data-field-error]').count()===0,'Error remains after editing');
 await form.locator('[type=submit]').click();await page.waitForFunction(()=>document.querySelector('[data-lead-form]').dataset.submitted==='true');
 check(requests===3,'Incorrect retry count');check(body.includes('Studio North')&&body.includes('telegram'),'Partner details not sent');check(await form.locator('[type=submit]').isEnabled(),'Successful button stayed disabled');
 check(await form.locator('.lead-new-request').getAttribute('href')==='/request/partner/','Fresh form link missing');await page.unroute('**/api/leads/');
 const context=await page.context().browser().newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
 try{
  const native=await context.newPage();let posted=false;
  await native.route('**/request/partner/',async route=>{
   if(route.request().method()!=='POST')return route.continue();posted=true;
   check((route.request().headers()['content-type']||'').includes('application/x-www-form-urlencoded'),'Native submission must be URL encoded');
   const data=new URLSearchParams(route.request().postData());check(data.get('company')==='Native Studio','Native submission lost company');check(!data.has('attachment'),'Native submission includes file');
   return route.fulfill({contentType:'text/html; charset=utf-8',body:'<!doctype html><html lang="ru"><h1>Заявка принята</h1></html>'});
  });
  await native.goto(origin+'/request/partner/',{waitUntil:'domcontentloaded'});
  await native.locator('[name=name]').fill('Тест без JavaScript');await native.locator('[name=contact]').fill('+79000000002');await native.locator('[name=company]').fill('Native Studio');await native.locator('[name=consent]').check();await native.locator('[type=submit]').click();await native.waitForFunction(()=>document.querySelector('h1').textContent==='Заявка принята');check(posted,'No native POST');
 }finally{await context.close()}
 check(!errors.length,errors.join('; '));return {widths:[1440,820,390],partnerEntries:2,uploads:false,networkAndValidationRetry:true,noJavaScript:true,errors};
}
