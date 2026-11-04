async page => {
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8000/#calculator');await page.reload();await page.setViewportSize({width:1440,height:1050});
 const root=page.locator('[data-configurator]');await root.locator('[data-config-reset]').click();
 await root.getByRole('radio',{name:'Гостиная',exact:true}).check();await root.locator('[data-config-next]').click();
 await root.locator('#config-ui-length').fill('5');await root.locator('#config-ui-width').fill('4');await root.locator('[data-config-next]').click();
 await root.getByRole('radio',{name:'Матовый ПВХ',exact:true}).check();await root.locator('[data-config-next]').click();
 await root.getByRole('radio',{name:'Классическое примыкание',exact:true}).check();await root.locator('[data-config-next]').click();
 await root.getByRole('checkbox',{name:'Без нового освещения',exact:true}).check();await root.locator('[data-config-next]').click();
 const options=root.locator('.config-options-cornice');
 if(await options.locator('img').count()!==4 || await options.locator('svg').count())throw Error('Expected four room images without diagrams');
 const sources=await options.locator('img').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('src')));
 if(!sources.every(src=>src.includes('/assets/calculator/curtain-')))throw Error('Old client image remains');
 if(await options.locator('input:checked').count())throw Error('Default preview silently selected an answer');
 const variants=['Потолочный карниз','Скрытый карниз / ниша','Карниз уже на стене','Карниз не нужен'];
 for(const title of variants){
   await root.getByRole('radio',{name:title,exact:true}).check();
   await root.locator('[data-config-visual]>img').evaluate(img=>img.decode());
   const length=root.locator('#config-ui-cornices');
   if(['Потолочный карниз','Скрытый карниз / ниша'].includes(title)){if(await length.count()!==1)throw Error('Length field absent');await length.fill('3');}
   else if(await length.count())throw Error('Irrelevant length field shown');
   await root.getByRole('button',{name:'Рассмотреть крупнее'}).click();const dialog=root.getByRole('dialog');await dialog.locator('img').evaluate(img=>img.decode());
   if(!await dialog.getByRole('heading',{name:title,exact:true}).isVisible())throw Error('Wrong curtain preview');
   await page.keyboard.press('Escape');
   if(!await root.getByRole('button',{name:'Рассмотреть крупнее'}).evaluate(b=>b===document.activeElement))throw Error('Focus lost after preview');
 }
 await root.getByRole('radio',{name:'Скрытый карниз / ниша',exact:true}).check();
 if(await root.locator('#config-ui-cornices').inputValue()!=='3')throw Error('Length lost when revisiting hidden rail');
 await page.locator('#calculator').screenshot({style:'.site-header,.skip-link{visibility:hidden!important}',path:'docs/calculator-redesign/screenshots/curtains-desktop.png'});
 for(const width of [1440,1024,768,390,320]){
   await page.setViewportSize({width,height:900});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Curtain overflow '+width);
   await root.getByRole('button',{name:'Рассмотреть крупнее'}).click();if(await root.getByRole('dialog').evaluate(d=>d.scrollWidth>d.clientWidth+1))throw Error('Dialog overflow '+width);await page.keyboard.press('Escape');
 }
 await page.setViewportSize({width:390,height:844});await page.locator('#calculator').screenshot({style:'.site-header,.skip-link{visibility:hidden!important}',path:'docs/calculator-redesign/screenshots/curtains-mobile.png'});
 await root.locator('[data-config-next]').click();await root.locator('[data-config-back]').click();
 if(!await root.getByRole('radio',{name:'Скрытый карниз / ниша',exact:true}).isChecked() || await root.locator('#config-ui-cornices').inputValue()!=='3')throw Error('Navigation lost curtain data');
 await root.getByRole('radio',{name:'Пока не определился',exact:true}).check();
 if(await root.locator('[data-config-visual]>img,[data-config-visual]>svg').count())throw Error('Undecided still displays a chosen curtain system');
 if(await options.locator('label').filter({has:page.locator('input[value=unknown]')}).locator('img,svg').count())throw Error('Undecided answer has a misleading image');
 if(errors.length)throw Error(errors.join(';'));return {variants,sources,errors};
}
