async page => {
 const checks=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8000/calculator/');await page.reload();
 const root=page.locator('[data-configurator]');await root.locator('[data-config-reset]').click();
 await root.getByRole('radio',{name:'Гостиная',exact:true}).check();await root.locator('[data-config-next]').click();
 await root.locator('#config-ui-width').fill('4');await root.locator('#config-ui-length').fill('1e309');
 if(/NaN|Infinity/.test(await root.locator('[data-config-visual]').innerHTML()))throw Error('Nonfinite SVG');
 await root.locator('[data-config-next]').click();if(await root.locator('.config-field-error').count()===0)throw Error('Invalid dimension accepted');
 await root.locator('#config-ui-length').fill('0.1');await root.locator('#config-ui-width').fill('0.1');await root.locator('[data-config-next]').click();
 if(!(await root.locator('.config-field-error').innerText()).includes('Площадь'))throw Error('Tiny area accepted');checks.push('nonfinite geometry and minimum area');
 const base={schema:'v2',room:'living',size_mode:'dimensions',shape:'rectangle',length:'5',width:'4',material:'pvc',edge:'standard',lights:'none',cornice:'none',features:'none',location:'city',action:'quote'};
 async function serverPost(tag,values){
  const csrf=await root.locator('[name=csrfmiddlewaretoken]').inputValue(),url='http://127.0.0.1:8000/calculator/?audit='+tag;
  await page.route(url,route=>route.continue({method:'POST',postData:new URLSearchParams({...base,...values,csrfmiddlewaretoken:csrf}).toString(),headers:{...route.request().headers(),'content-type':'application/x-www-form-urlencoded'}}));
  await page.goto(url);await page.unroute(url);
 }
 await serverPost('quote',{});await root.locator('[data-config-result]').waitFor({state:'visible'});
 const quote=await page.locator('#config-bootstrap').evaluate(n=>JSON.parse(n.textContent).quote);
 if(!/16\s*240/.test(await root.locator('.quote-total').innerText()))throw Error('Bound quote hidden or wrong');
 await page.evaluate(()=>sessionStorage.setItem('vlico-calculator-v2',JSON.stringify({schema:'v2',length:'9',width:'9'})));
 await serverPost('invalid',{length:''});await root.locator('#config-ui-length').waitFor();
 if(await root.locator('#config-ui-length').inputValue()!=='')throw Error('Blank bound value replaced with draft');
 if(!await root.locator('.config-field-error').count())throw Error('Bound server error hidden');checks.push('server quote and invalid POST restoration');
 await serverPost('retry',{});await root.locator('[data-config-contact]').click();
 await root.locator('[name=name]').fill('Проверка интерфейса');await root.locator('[name=contact]').fill('audit@example.invalid');await root.locator('[name=consent]').check();
 let attempts=0;
 const updated={...quote,version:quote.version+100,total:String(Number(quote.total)+100)};
 await page.route('**/api/leads/',async route=>{
  attempts++;
  const response=attempts===1?{status:400,body:{ok:false,errors:{contact:['Проверьте контакт']}}}:attempts===2?{status:503,body:null}:attempts===3?{status:409,body:{ok:false,errors:{__all__:['Тарифы обновились']},quote:updated}}:{status:201,body:{ok:true,message:'Тест интерфейса подтверждён',reference:'mocked-audit',kind:'calculator'}};
  await route.fulfill({status:response.status,contentType:'application/json',body:JSON.stringify(response.body)});
 });
 await root.locator('[data-config-submit]').click();await root.locator('[name=contact][aria-invalid=true]').waitFor();
 await root.locator('[name=contact]').fill('corrected@example.invalid');if(await root.locator('[name=contact]').getAttribute('aria-invalid'))throw Error('Corrected contact remains invalid');
 await root.locator('[data-config-submit]').click();await root.locator('[data-config-submit]').waitFor({state:'visible'});
 await page.waitForFunction(()=>document.querySelector('[data-configurator]').getAttribute('aria-busy')==='false');
 await root.locator('[data-config-submit]').click();await page.waitForFunction(v=>document.querySelector('[data-configurator] [name=pricing_version]').value===String(v),updated.version);
 if(await root.locator('[name=contact]').inputValue()!=='corrected@example.invalid')throw Error('Stale-rate retry lost contact');
 await root.locator('[data-config-submit]').click();await page.waitForFunction(()=>document.querySelector('[data-configurator]').dataset.submitted==='true');
 if(attempts!==4)throw Error('Unexpected duplicate submission');
 if(await root.locator('[data-submit-field-error]').count())throw Error('Old contact errors remain after success');
 await page.unroute('**/api/leads/');checks.push('mocked validation, malformed response, rate update and idempotent retry UI');
 if(errors.length)throw Error(errors.join(';'));return {checks,errors};
}
