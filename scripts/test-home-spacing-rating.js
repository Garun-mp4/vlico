async page => {
 const check=(ok,message)=>{if(!ok)throw Error(message)};const results=[],errors=[];
 page.on('pageerror',e=>errors.push(e.message));await page.emulateMedia({reducedMotion:'reduce'});
 for(const width of [320,390,768,1280,1440]){
  await page.setViewportSize({width,height:900});await page.goto('http://localhost:8000/',{waitUntil:'domcontentloaded'});await page.evaluate(()=>document.fonts.ready);
  if(await page.locator('[data-privacy-panel]').isVisible())await page.locator('[data-privacy-essential]').click();
  check(await page.locator('.grid-overlay').count()===0,'Grid guides remain');
  const badge=page.locator('.home-rating .rating-badge iframe');await badge.scrollIntoViewIfNeeded();check(await badge.isVisible(),'Rating hidden '+width);
  check((await badge.getAttribute('src')).includes('164382623295'),'Wrong organization');
  if(width===1280){
   const frame=await(await badge.elementHandle()).contentFrame();
   const live=frame.locator('.RatingBadgeWidget');await live.waitFor({state:'visible'});
   const background=await live.evaluate(el=>getComputedStyle(el).backgroundImage);
   check(background.startsWith('url("data:image/svg+xml;'),'Official live rating graphic missing');
   await live.evaluate(async el=>{const image=new Image();image.src=getComputedStyle(el).backgroundImage.slice(5,-2);await image.decode()});
   await page.locator('.home-rating').screenshot({path:'.playwright-cli/rating-desktop-visible.png'});
  }
  const rail=page.locator('.new-solutions-rail');await rail.scrollIntoViewIfNeeded();
  if(width<=760){
   const heights=[];
   for(let index=0;index<3;index++){
    await page.waitForFunction(i=>{const rail=document.querySelector('.new-solutions-rail'),card=rail.children[i],style=getComputedStyle(rail);return Math.abs(rail.clientHeight-card.getBoundingClientRect().height-parseFloat(style.paddingTop)-parseFloat(style.paddingBottom))<2},index);
    const dimensions=await page.evaluate(i=>{const rail=document.querySelector('.new-solutions-rail'),a=rail.children[i].querySelector('.text-link').getBoundingClientRect(),r=rail.getBoundingClientRect(),about=document.querySelector('#about').getBoundingClientRect();return {height:r.height,gap:about.top-a.bottom,clipped:a.bottom>r.bottom+1}},index);
    check(dimensions.gap<=50&&dimensions.gap>=8,'Large gap '+width+' card '+index+': '+dimensions.gap);check(!dimensions.clipped,'Active action clipped');heights.push(dimensions);
    if(width===390)await page.locator('.new-solutions').screenshot({path:'.playwright-cli/compact-solutions-'+index+'.png'});
    if(index<2){await page.locator('[data-solutions-next]').click();await page.waitForFunction(i=>document.querySelector('[data-solutions-count]').textContent===`${i+1} / 3`,index+1)}
   }
   check(heights[2].height>heights[0].height+50,'Rail never adapts to long copy');
   await page.locator('[data-solutions-prev]').click();await page.waitForFunction(()=>document.querySelector('[data-solutions-count]').textContent==='2 / 3');await page.locator('[data-solutions-prev]').click();await page.waitForFunction(()=>document.querySelector('[data-solutions-prev]').disabled);
   results.push({width,cards:heights});
  }else{check(await rail.evaluate(el=>!el.style.height),'Desktop retains mobile inline height');results.push({width,rating:true})}
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Page overflow');
 }
 for(const path of ['/partners/','/services/','/contacts/','/blog/']){await page.goto('http://localhost:8000'+path,{waitUntil:'domcontentloaded'});check(await page.locator('.grid-overlay').count()===0,'Guides remain on '+path)}
 check(!errors.length,errors.join('; '));return {results,errors};
}
