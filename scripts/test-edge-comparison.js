async page => {
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8000/#calculator');await page.reload();await page.setViewportSize({width:1440,height:1050});
 const root=page.locator('[data-configurator]');await root.locator('[data-config-reset]').click();
 await root.getByRole('radio',{name:'Гостиная',exact:true}).check();await root.locator('[data-config-next]').click();
 await root.locator('#config-ui-length').fill('5');await root.locator('#config-ui-width').fill('4');await root.locator('[data-config-next]').click();
 await root.getByRole('radio',{name:'Матовый ПВХ',exact:true}).check();await root.locator('[data-config-next]').click();
 if(await root.locator('[name=edge]:checked').count())throw Error('Example preselected an answer');
 const options=root.locator('.config-options-edge');if(await options.locator('img').count()!==3)throw Error('Expected three real edge images');
 if(await options.locator('svg').count())throw Error('Edge diagrams remain');
 const unknown=options.locator('label').filter({has:page.locator('input[value=unknown]')});
 if(await unknown.locator('img,svg').count())throw Error('Unknown answer has a misleading image');
 const variants=['Классическое примыкание','Теневое примыкание','Парящий потолок'];const previews=[];
 for(const title of variants){
   await root.getByRole('radio',{name:title,exact:true}).check();
   const image=root.locator('[data-config-visual]>img');await image.evaluate(img=>img.decode());previews.push(await image.getAttribute('src'));
   await root.getByRole('button',{name:'Рассмотреть крупнее'}).click();await root.getByRole('dialog').locator('img').evaluate(img=>img.decode());
   if(!await root.getByRole('dialog').getByRole('heading',{name:title,exact:true}).isVisible())throw Error('Wrong preview title');
   await page.keyboard.press('Escape');
   if(!await root.getByRole('button',{name:'Рассмотреть крупнее'}).evaluate(b=>b===document.activeElement))throw Error('Preview focus lost');
 }
 if(new Set(previews).size!==3)throw Error('Images do not differ');
 await page.locator('#calculator').screenshot({style:'.site-header,.skip-link{visibility:hidden!important}',path:'docs/calculator-redesign/screenshots/edges-desktop.png'});
 for(const width of [1440,1024,768,390,320]){
   await page.setViewportSize({width,height:900});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Edge overflow '+width);
   await root.getByRole('button',{name:'Рассмотреть крупнее'}).click();if(await root.getByRole('dialog').evaluate(d=>d.scrollWidth>d.clientWidth+1))throw Error('Dialog overflow '+width);await page.keyboard.press('Escape');
 }
 await page.setViewportSize({width:390,height:844});await page.locator('#calculator').screenshot({style:'.site-header,.skip-link{visibility:hidden!important}',path:'docs/calculator-redesign/screenshots/edges-mobile.png'});
 await root.getByRole('radio',{name:'Пока не знаю',exact:true}).check();
 if(await root.locator('[data-config-visual]>img,[data-config-visual]>svg').count())throw Error('Unknown edge still previews a specific profile');
 await root.locator('[data-config-back]').click();await root.locator('[data-config-next]').click();
 if(!await root.getByRole('radio',{name:'Пока не знаю',exact:true}).isChecked())throw Error('Unknown choice lost on navigation');
 if(errors.length)throw Error(errors.join(';'));
 return {variants,previews,errors};
}
