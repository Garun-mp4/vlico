async page => {
 const errors=[]; page.on('pageerror', e=>errors.push(e.message));
 await page.setViewportSize({width:1440,height:1000});
 await page.goto('http://127.0.0.1:8000/calculator/');
 const root=page.locator('[data-configurator]'), price=root.locator('[data-config-price]');
 const next=()=>root.locator('[data-config-next]').click();
 const radio=name=>root.getByRole('radio',{name,exact:true}).check();
 const check=name=>root.getByRole('checkbox',{name,exact:true}).check();
 async function amount(value) {
   await page.waitForFunction(v=>{
     const box=document.querySelector('[data-config-price]');
     return box.getAttribute('aria-busy')==='false' && box.querySelector('.config-price-total').textContent.replace(/\s/g,'')===v+'₽';
   },String(value));
 }
 async function capture(name) {
   await root.locator('[data-config-question]').scrollIntoViewIfNeeded();
   await page.screenshot({path:`docs/calculator-redesign/screenshots/live-${name}.png`});
 }
 await root.locator('[data-config-reset]').click();
 await price.getByText('Укажите размеры и выберите материал — покажем стоимость',{exact:true}).waitFor();
 if((await price.innerText()).includes('0 ₽'))throw Error('Zero placeholder');
 await radio('Гостиная');await next();
 await root.locator('#config-ui-length').fill('5');await root.locator('#config-ui-width').fill('4');await next();
 await radio('Матовый ПВХ');await amount(13000);await capture('13000');
 if(!(await root.locator('.config-options-material').innerText()).includes('650 ₽'))throw Error('Unit price missing');
 await next();await radio('Классическое примыкание');await amount(16240);await capture('16240');
 await radio('Теневое примыкание');await amount(28300);
 if(!(await price.locator('.config-price-delta').innerText()).replace(/\s/g,'').includes('+12060₽'))throw Error('Replacement delta wrong');
 await capture('28300');await next();await check('Точечные светильники');await root.locator('#config-ui-spots').fill('6');await amount(31000);
 await check('Световые линии');await root.locator('#config-ui-light_lines').fill('3');
 await check('Магнитные треки');await root.locator('#config-ui-tracks').fill('2');
 await next();await radio('Скрытый карниз / ниша');await root.locator('#config-ui-cornices').fill('3');await amount(50900);await capture('50900');
 await page.setViewportSize({width:390,height:844});await root.locator('#config-ui-cornices').focus();
 if(await price.isVisible())throw Error('Price overlaps keyboard input');
 await root.locator('[data-config-question] h3').focus();await amount(50900);
 const geometry=await price.boundingBox();if(!geometry || geometry.y+geometry.height>845)throw Error('Mobile price outside viewport');
 await capture('mobile-50900');
 await next();await check('Ничего из перечисленного');await next();await radio('Калининград');await amount(50900);
 await next();await root.locator('[data-config-result]').waitFor({state:'visible'});
 if(!(await root.locator('.quote-total').innerText()).replace(/\s/g,'').includes('50900'))throw Error('Final differs');
 if(await price.isVisible())throw Error('Live price overlaps final result');
 await root.locator('[data-config-edit]').click();await amount(50900);await next();
 await page.route('**/api/calculate/',route=>route.abort());
 await root.locator('#config-ui-width').fill('3');
 if((await price.locator('.config-price-total').innerText()).includes('900'))throw Error('Stale price displayed');
 await root.locator('[data-config-question] h3').focus();
 await price.getByText('Стоимость недоступна',{exact:true}).waitFor();await page.unroute('**/api/calculate/');
 await price.getByRole('button',{name:'Повторить расчёт'}).click();await amount(45950);
 await root.locator('#config-ui-width').fill('4');await root.locator('[data-config-question] h3').focus();await amount(50900);
 await next();await radio('Глянцевый ПВХ');await price.getByText('Для выбранного материала стоимость уточняется',{exact:true}).waitFor();
 await radio('Матовый ПВХ');await amount(50900);await next();await next();
 await check('Без нового освещения');await amount(32800);await next();await radio('Карниз не нужен');await amount(28300);
 // Dimensions and finish changes replace their rows, never accumulate them.
 for(let i=0;i<4;i++)await root.locator('[data-config-back]').click();
 await root.locator('#config-ui-width').fill('2');await root.locator('[data-config-question] h3').focus();await amount(18400);
 await page.reload();await amount(18400);
 for(const width of [320,390,768,1024,1440]){
   await page.setViewportSize({width,height:900});
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Overflow '+width);
 }
 await next();
 let held, resolveHeld;
 const captured=new Promise(resolve=>{resolveHeld=resolve;});
 await page.route('**/api/calculate/',route=>{
   if(!held){held=route;resolveHeld();}else return route.continue();
 });
 await root.locator('#config-ui-width').fill('3');await captured;
 await root.locator('#config-ui-width').fill('4');await amount(28300);
 await held.fulfill({status:200,contentType:'application/json',body:JSON.stringify({quote:{version:1,total:'999999',warnings:[],inputs:{area:'20'}},options:{}})});
 if(!(await price.locator('.config-price-total').innerText()).replace(/\s/g,'').includes('28300'))throw Error('Stale response replaced price');
 await page.unroute('**/api/calculate/');
 await page.route('**/api/calculate/',async route=>{
   const response=await route.fetch(),body=await response.json();body.quote.version+=1000;
   await route.fulfill({response,json:body});
 });
 await root.locator('#config-ui-width').fill('2');await amount(18400);
 if(!(await price.locator('.config-price-delta').innerText()).includes('Тарифы обновились'))throw Error('Version update not explained');
 await page.unroute('**/api/calculate/');
 if(errors.length)throw Error(errors.join('; '));
 return {sequence:[13000,16240,28300,31000,50900],removed:28300,restored:18400,errors};
}
