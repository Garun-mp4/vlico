(() => {
  function initialize(list, navigation = false) {
    const section = navigation ? list : list.closest('#solutions');
    const rows = [...list.querySelectorAll('[data-service-preview]')];
    if (!rows.length) return;
    const capable = matchMedia(`(hover: hover) and (pointer: fine) and (min-width: ${navigation ? 961 : 900}px)`);
    const reduce = matchMedia('(prefers-reduced-motion: reduce)');
    const card = document.createElement('div');
    card.className = navigation ? 'service-preview service-preview--navigation' : 'service-preview';
    card.setAttribute('aria-hidden', 'true');
    const label = document.createElement('span');
    label.className = 'service-preview-label';
    label.textContent = 'Иллюстрация решения';
    card.append(label);
    document.body.append(card);
    const images = new Map();
    let active = null, generation = 0, frame = 0, near = false, keyboard = false;
    let width = 0, height = 0, targetX = 0, targetY = 0, x = 0, y = 0, tilt = 0, previous = 0;
    let anchor = null, menuBounds = null, releaseTimer;
    const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

    function load(row) {
      if (images.has(row)) return images.get(row);
      const image = new Image();
      image.className = 'service-preview-image';
      image.alt = ''; image.decoding = 'async'; image.draggable = false;
      const entry = { image, ready: false };
      images.set(row, entry);
      image.src = row.dataset.servicePreview;
      entry.promise = image.decode().then(() => {
        entry.ready = true;
        card.insertBefore(image, label);
        return true;
      }).catch(() => false); // A failed decorative image never blocks its service link.
      return entry;
    }
    function warm() {
      if (near && capable.matches && (!navigation || list.getAttribute('aria-hidden') === 'false') && !navigator.connection?.saveData) rows.forEach(load);
    }
    const observer = new IntersectionObserver(entries => {
      near = entries[0].isIntersecting;
      if (near) warm(); else hide();
    }, { rootMargin: '250px' });
    observer.observe(section);

    function paint() {
      card.style.transform = `translate3d(${x}px,${y}px,0) rotate(${tilt}deg)`;
    }
    function animate(now) {
      frame = 0;
      if (!active || !capable.matches || document.hidden) return;
      const dt = Math.min(now - previous, 48); previous = now;
      const dx = targetX - x, dy = targetY - y;
      x += dx * (1 - Math.exp(-dt / 90));
      y += dy * (1 - Math.exp(-dt / 90));
      const maxTilt = navigation ? 6 : 12;
      tilt += (clamp(dx * 0.065, -maxTilt, maxTilt) - tilt) * (1 - Math.exp(-dt / 140));
      paint();
      if (Math.hypot(targetX-x,targetY-y) > 0.1 || Math.abs(tilt) > 0.05) frame = requestAnimationFrame(animate);
      else { x=targetX; y=targetY; tilt=0; paint(); }
    }
    function schedule() {
      if (!frame) { previous=performance.now(); frame=requestAnimationFrame(animate); }
    }
    function aim(event) {
      if (navigation) {
        const left = menuBounds.left-width-32;
        const baseX = left >= 24 ? left : menuBounds.right+32;
        const drift = keyboard || reduce.matches ? 0 : clamp((event.clientX-anchor.left-anchor.width/2)*.12,-12,12);
        targetX=clamp(baseX+drift,24,innerWidth-width-24);
        targetY=clamp((keyboard || reduce.matches ? anchor.top+anchor.height/2 : event.clientY)-height/2,Math.max(24,menuBounds.top),Math.max(24,innerHeight-height-24));
      } else if (keyboard || reduce.matches) {
        targetX=clamp(anchor.right-width-20,32,innerWidth-width-32);
        targetY=clamp(anchor.top+(anchor.height-height)/2,32,innerHeight-height-32);
      } else {
        const preferred=event.clientX+36;
        targetX=clamp(preferred+width+32>innerWidth ? event.clientX-width-36 : preferred,32,innerWidth-width-32);
        targetY=clamp(event.clientY-height*.55,32,innerHeight-height-32);
      }
    }
    function show(row, event, fromKeyboard=false) {
      if (!capable.matches || document.hidden || (navigation && list.getAttribute('aria-hidden') !== 'false')) return;
      const token=++generation;
      active=row; keyboard=fromKeyboard;
      width=Math.min(navigation ? 280 : 360,Math.max(240,innerWidth*.22),Math.max(120,(innerHeight-80)*4/3));
      height=width*.75;card.style.width=`${width}px`;
      anchor=row.getBoundingClientRect();
      if (navigation) menuBounds=list.getBoundingClientRect();
      aim(event);
      clearTimeout(releaseTimer);
      card.style.willChange='transform, opacity';
      const entry=load(row);
      const reveal=() => {
        if (active!==row || token!==generation || !capable.matches || document.hidden) return;
        images.forEach(item=>item.image.classList.toggle('is-current',item===entry));
        label.hidden=row.dataset.previewIllustration!=='true';
        const visible=card.classList.contains('is-visible');
        if (!visible || keyboard || reduce.matches) { x=targetX;y=targetY;tilt=0;paint(); }
        card.classList.add('is-visible');
        if (!keyboard && !reduce.matches) schedule();
      };
      if (entry.ready) reveal();
      else {
        card.classList.remove('is-visible');
        entry.promise.then(ok=>{ if (ok) reveal(); });
      }
    }
    function hide() {
      active=null;generation++;
      cancelAnimationFrame(frame);frame=0;
      card.classList.remove('is-visible');
      clearTimeout(releaseTimer);
      releaseTimer=setTimeout(()=>card.style.removeProperty('will-change'),180);
    }
    list.addEventListener('pointermove',event=>{
      if (event.pointerType==='touch' || !capable.matches) return;
      const row=event.target.closest('[data-service-preview]');
      if (!row) { hide();return; }
      if (row!==active || keyboard) { show(row,event);return; }
      if (!reduce.matches) {
        aim(event);
        if (card.classList.contains('is-visible')) schedule();
      }
    },{passive:true});
    list.addEventListener('pointerleave',hide);
    list.addEventListener('pointercancel',hide);
    list.addEventListener('focusin',event=>{
      const row=event.target.closest('[data-service-preview]');
      // Focus can scroll the document; place the stationary preview afterward.
      if (row) requestAnimationFrame(()=>{
        if(document.activeElement===row && row.matches(':focus-visible')) show(row,null,true);
      });
    });
    list.addEventListener('focusout',event=>{if(!list.contains(event.relatedTarget))hide();});
    window.addEventListener('scroll',hide,{passive:true});
    window.addEventListener('resize',hide,{passive:true});
    window.addEventListener('blur',hide);
    document.addEventListener('visibilitychange',()=>{if(document.hidden)hide();});
    capable.addEventListener('change',()=>{hide();warm();});
    reduce.addEventListener('change',hide);
    if (navigation) new MutationObserver(() => {
      if (list.getAttribute('aria-hidden') === 'false') warm(); else hide();
    }).observe(list, {attributes:true,attributeFilter:['aria-hidden']});
  }
  const list = document.querySelector('#solutions .solution-list');
  if (list) initialize(list);
  document.querySelectorAll('[data-navigation-preview]').forEach(panel => initialize(panel, true));
})();
