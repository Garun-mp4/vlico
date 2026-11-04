async page => {
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8000/#calculator');await page.reload();await page.setViewportSize({width:1440,height:1050});
 const root=page.locator('[data-configurator]');await root.locator('[data-config-reset]').click();
 await root.getByRole('radio',{name:'Гостиная',exact:true}).check();await root.locator('[data-config-next]').click();
 await root.locator('#config-ui-length').fill('5');await root.locator('#config-ui-width').fill('4');await root.locator('[data-config-next]').click();
 await root.getByRole('radio',{name:'Матовый ПВХ',exact:true}).check();await root.locator('[data-config-next]').click();
 await root.getByRole('radio',{name:'Классическое примыкание',exact:true}).check();await root.locator('[data-config-next]').click();
 const options=root.locator('.config-options-lights');
 if(await options.locator('img').count()!==5 || await options.locator('svg').count())throw Error('Lighting options must contain five photos and no diagrams');
 const sources=await options.locator('img').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('src')));
 if(!sources.every(src=>src.includes('/assets/calculator/light-')))throw Error('Client photo remains in lighting choices');
 const variants=['Точечные светильники','Световые линии','Магнитные треки','Люстра / подвес','Контурная подсветка'];
 for(const title of variants){
   await root.getByRole('checkbox',{name:title,exact:true}).check();
   await root.locator('[data-config-visual]>img').evaluate(img=>img.decode());
   await root.getByRole('button',{name:'Рассмотреть крупнее'}).click();const dialog=root.getByRole('dialog');await dialog.locator('img').evaluate(img=>img.decode());
   if(!await dialog.getByRole('heading',{name:title,exact:true}).isVisible())throw Error('Latest selection not previewed: '+title);
   await page.keyboard.press('Escape');
 }
 if(await options.locator('input:checked').count()!==5)throw Error('Multi-select lost');
 await root.locator('#config-ui-spots').fill('6');
 await root.getByRole('group',{name:'Рассмотреть выбранное освещение'}).getByRole('button',{name:'Точечные светильники',exact:true}).click();
 if(await options.locator('input:checked').count()!==5 || await root.locator('#config-ui-spots').inputValue()!=='6')throw Error('Preview selector changed configuration');
 if(!(await root.locator('[data-config-visual]>img').getAttribute('src')).includes('light-spots.webp'))throw Error('Preview click was lost after leaving quantity field');
 await page.locator('#calculator').screenshot({style:'.site-header,.skip-link{visibility:hidden!important}',path:'docs/calculator-redesign/screenshots/lights-desktop.png'});
 for(const width of [1440,1024,768,390,320]){
   await page.setViewportSize({width,height:900});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Lighting overflow '+width);
   await root.getByRole('button',{name:'Рассмотреть крупнее'}).click();if(await root.getByRole('dialog').evaluate(d=>d.scrollWidth>d.clientWidth+1))throw Error('Preview overflow '+width);await page.keyboard.press('Escape');
 }
 await page.setViewportSize({width:390,height:844});await page.locator('#calculator').screenshot({style:'.site-header,.skip-link{visibility:hidden!important}',path:'docs/calculator-redesign/screenshots/lights-mobile.png'});
 await root.locator('[data-config-next]').click();await root.locator('[data-config-back]').click();
 if(await options.locator('input:checked').count()!==5 || await root.locator('#config-ui-spots').inputValue()!=='6')throw Error('Back lost lighting data');
 await root.getByRole('checkbox',{name:'Без нового освещения',exact:true}).check();
 if(await options.locator('input:checked').count()!==1 || await root.locator('#config-ui-spots').count())throw Error('No new lighting did not exclude dependent values');
 if(await root.locator('[data-config-visual]>img').count())throw Error('No lighting still shows a selected system');
 if(errors.length)throw Error(errors.join(';'));
 return {variants,sources,errors};
}
