async page => {
  const errors=[]; page.on('pageerror', e => errors.push(e.message));
  await page.setViewportSize({width:1440,height:1000});
  await page.goto('http://127.0.0.1:8000/#calculator'); await page.reload();
  const root=page.locator('[data-configurator]');
  await root.locator('[data-config-reset]').click();
  await page.locator('#calculator').screenshot({style:'.site-header,.skip-link{visibility:hidden!important}',path:'docs/calculator-redesign/screenshots/after-desktop-start.png'});
  await root.getByRole('radio',{name:'Гостиная',exact:true}).check();
  await root.locator('[data-config-next]').click();
  await root.locator('#config-ui-length').fill('5');await root.locator('#config-ui-width').fill('4');
  await root.locator('[data-config-next]').click();
  await root.getByRole('radio',{name:'Матовый ПВХ',exact:true}).check();
  await page.locator('#calculator').screenshot({style:'.site-header,.skip-link{visibility:hidden!important}',path:'docs/calculator-redesign/screenshots/after-desktop-material.png'});
  await root.locator('[data-config-next]').click();
  await root.getByRole('radio',{name:'Теневое примыкание',exact:true}).check();await root.locator('[data-config-next]').click();
  await root.getByRole('checkbox',{name:'Точечные светильники',exact:true}).check();await root.locator('#config-ui-spots').fill('6');
  await root.getByRole('checkbox',{name:'Световые линии',exact:true}).check();await root.locator('#config-ui-light_lines').fill('3');
  await root.getByRole('checkbox',{name:'Магнитные треки',exact:true}).check();await root.locator('#config-ui-tracks').fill('2');
  await root.locator('[data-config-next]').click();await root.getByRole('radio',{name:'Скрытый карниз / ниша',exact:true}).check();await root.locator('#config-ui-cornices').fill('3');
  await root.locator('[data-config-next]').click();await root.getByRole('checkbox',{name:'Ничего из перечисленного',exact:true}).check();
  await root.locator('[data-config-next]').click();await root.getByRole('radio',{name:'Калининград',exact:true}).check();
  await root.locator('[data-config-next]').click();await root.locator('[data-config-result]').waitFor({state:'visible'});
  const total=await root.locator('.quote-total').innerText();if(!/50\s*900/.test(total))throw Error('Wrong total '+total);
  await page.locator('#calculator').screenshot({style:'.site-header,.skip-link{visibility:hidden!important}',path:'docs/calculator-redesign/screenshots/after-desktop-result.png'});
  await root.locator('[data-config-contact]').click();
  const ids=await page.locator('[id]').evaluateAll(nodes=>nodes.map(n=>n.id).filter((v,i,a)=>a.indexOf(v)!==i));if(ids.length)throw Error('Duplicate IDs '+ids);
  await root.locator('[data-config-edit]').click();
  await root.locator('[data-config-next]').click();
  if(await root.locator('#config-ui-length').inputValue()!=='5')throw Error('Back lost dimensions');
  const widths=[];
  for(const width of [1440,1280,1024,768,390,320]){
    await page.setViewportSize({width,height:900});
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);widths.push({width,overflow});
    if(overflow)throw Error('Overflow at '+width);
  }
  await page.setViewportSize({width:390,height:844});
  await page.locator('#calculator').screenshot({style:'.site-header,.skip-link{visibility:hidden!important}',path:'docs/calculator-redesign/screenshots/after-mobile-dimensions.png'});
  if(errors.length)throw Error(errors.join('; '));
  return {total,widths,errors};
}
