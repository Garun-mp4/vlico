async page => {
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8000/#calculator');await page.reload();
 await page.setViewportSize({width:1440,height:1050});
 const root=page.locator('[data-configurator]');await root.locator('[data-config-reset]').click();
 await root.getByRole('radio',{name:'Гостиная',exact:true}).check();await root.locator('[data-config-next]').click();
 await root.locator('#config-ui-length').fill('5');await root.locator('#config-ui-width').fill('4');await root.locator('[data-config-next]').click();
 if(await root.locator('[name=material]:checked').count())throw Error('Preview must not silently select material');
 await root.locator('[data-config-visual]>img').waitFor();
 const choices=['Матовый ПВХ','Сатиновый ПВХ','Глянцевый ПВХ','Тканевый потолок'];
 const previews=[];
 for(const title of choices){
   await root.getByRole('radio',{name:title,exact:true}).check();
   const image=root.locator('[data-config-visual]>img');
   await image.evaluate(img=>img.decode());previews.push(await image.getAttribute('src'));
   await root.getByRole('button',{name:'Рассмотреть крупнее'}).click();
   await root.getByRole('dialog').waitFor({state:'visible'});await root.getByRole('dialog').locator('img').evaluate(img=>img.decode());
   await page.keyboard.press('Escape');if(await root.getByRole('dialog').isVisible())throw Error('Escape did not close preview');
   if(!await root.getByRole('button',{name:'Рассмотреть крупнее'}).evaluate(button=>button===document.activeElement))throw Error('Focus did not return after preview');
 }
 if(new Set(previews).size!==4)throw Error('Surface previews do not differ');
 await root.getByRole('radio',{name:'Глянцевый ПВХ',exact:true}).check();
 await page.locator('#calculator').screenshot({style:'.site-header,.skip-link{visibility:hidden!important}',path:'docs/calculator-redesign/screenshots/materials-desktop.png'});
 const sizes=[];
 for(const width of [1440,1024,768,390,320]){
   await page.setViewportSize({width,height:900});
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Material overflow '+width);
   await root.getByRole('button',{name:'Рассмотреть крупнее'}).click();
   if(await root.getByRole('dialog').evaluate(d=>d.scrollWidth>d.clientWidth+1))throw Error('Dialog overflow '+width);
   await root.getByRole('dialog').getByRole('button',{name:'Закрыть'}).click();sizes.push(width);
 }
 await page.setViewportSize({width:390,height:844});
 await page.locator('#calculator').screenshot({style:'.site-header,.skip-link{visibility:hidden!important}',path:'docs/calculator-redesign/screenshots/materials-mobile.png'});
 await root.locator('[data-config-back]').click();await root.locator('[data-config-next]').click();
 if(!await root.getByRole('radio',{name:'Глянцевый ПВХ',exact:true}).isChecked())throw Error('Finish lost after back');
 await page.reload();
 await root.locator('[data-config-next]').click();await root.locator('[data-config-next]').click();
 if(!await root.getByRole('radio',{name:'Глянцевый ПВХ',exact:true}).isChecked())throw Error('Finish lost after reload');
 if(errors.length)throw Error(errors.join(';'));
 return {choices,previews,sizes,errors};
}
