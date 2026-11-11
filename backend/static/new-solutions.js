(() => {
  const rail = document.querySelector('.new-solutions-rail');
  const controls = document.querySelector('[data-solutions-controls]');
  if (!rail || !controls) return;
  const cards = [...rail.querySelectorAll('.new-solution')];
  const previous = controls.querySelector('[data-solutions-prev]');
  const next = controls.querySelector('[data-solutions-next]');
  const count = controls.querySelector('[data-solutions-count]');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const mobile = matchMedia('(max-width: 760px)');
  let scheduled = false;
  let current = 0;
  function positions() {
    const origin = cards[0].getBoundingClientRect().left;
    return cards.map(card => card.getBoundingClientRect().left - origin);
  }
  function update() {
    const max = rail.scrollWidth - rail.clientWidth;
    const offsets = positions();
    current = offsets.reduce((best, offset, i) => Math.abs(offset - rail.scrollLeft) < Math.abs(offsets[best] - rail.scrollLeft) ? i : best, 0);
    if (rail.scrollLeft >= max - 2 && max > 2) current = cards.length - 1;
    // Off-screen long descriptions must not reserve blank space below the active card.
    let height = null;
    if (mobile.matches && max > 2) {
      const style = getComputedStyle(rail);
      const scrollbar = rail.offsetHeight - rail.clientHeight;
      height = Math.ceil(cards[current].getBoundingClientRect().height + parseFloat(style.paddingTop) + parseFloat(style.paddingBottom) + scrollbar);
    }
    controls.hidden = max <= 2;
    if (height === null) rail.style.removeProperty('height');
    else if (rail.style.height !== `${height}px`) rail.style.height = `${height}px`;
    previous.disabled = rail.scrollLeft <= 2;
    next.disabled = rail.scrollLeft >= max - 2;
    const label = `${current + 1} / ${cards.length}`;
    if (count.textContent !== label) count.textContent = label;
  }
  function move(direction) {
    const max = rail.scrollWidth - rail.clientWidth;
    const stops = [...new Set(positions().map(offset => Math.min(offset, max)))];
    const target = direction > 0 ? stops.find(offset => offset > rail.scrollLeft + 2) : stops.reverse().find(offset => offset < rail.scrollLeft - 2);
    if (target !== undefined) rail.scrollTo({left: target, behavior: reduced.matches ? 'instant' : 'smooth'});
  }
  previous.addEventListener('click', () => move(-1));
  next.addEventListener('click', () => move(1));
  function scheduleUpdate() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => { scheduled = false; update(); });
  }
  rail.addEventListener('scroll', scheduleUpdate, {passive:true});
  const resize = new ResizeObserver(scheduleUpdate);
  resize.observe(rail);
  cards.forEach(card => resize.observe(card));
  mobile.addEventListener('change', scheduleUpdate);
  document.fonts?.ready.then(scheduleUpdate);
  update();
})();
