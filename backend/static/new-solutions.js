(() => {
  const rail = document.querySelector('.new-solutions-rail');
  const controls = document.querySelector('[data-solutions-controls]');
  if (!rail || !controls) return;
  const cards = [...rail.querySelectorAll('.new-solution')];
  const previous = controls.querySelector('[data-solutions-prev]');
  const next = controls.querySelector('[data-solutions-next]');
  const count = controls.querySelector('[data-solutions-count]');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let current = 0;
  function positions() {
    const origin = cards[0].getBoundingClientRect().left;
    return cards.map(card => card.getBoundingClientRect().left - origin);
  }
  function update() {
    const max = rail.scrollWidth - rail.clientWidth;
    controls.hidden = max <= 2;
    const offsets = positions();
    current = offsets.reduce((best, offset, i) => Math.abs(offset - rail.scrollLeft) < Math.abs(offsets[best] - rail.scrollLeft) ? i : best, 0);
    if (rail.scrollLeft >= max - 2 && max > 2) current = cards.length - 1;
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
  rail.addEventListener('scroll', update, {passive:true});
  new ResizeObserver(update).observe(rail);
  update();
})();
