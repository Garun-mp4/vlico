(() => {
  const section = document.getElementById('project-videos');
  const dialog = document.querySelector('[data-video-dialog]');
  if (!section || !dialog || typeof dialog.showModal !== 'function') return;
  const rail = section.querySelector('.project-videos-rail');
  const cards = [...rail.children];
  const controls = section.querySelector('[data-video-controls]');
  const previous = controls.querySelector('[data-video-prev]');
  const next = controls.querySelector('[data-video-next]');
  const count = controls.querySelector('[data-video-count]');
  const video = dialog.querySelector('video');
  const title = dialog.querySelector('#project-video-title');
  const status = dialog.querySelector('[data-video-status]');
  const retry = dialog.querySelector('[data-video-retry]');
  const fallback = dialog.querySelector('[data-video-fallback]');
  const fullscreen = dialog.querySelector('[data-video-fullscreen]');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let active = null;
  let savedOverflow = '';
  let generation = 0;
  let scheduled = false;

  function stops() {
    const origin = cards[0].getBoundingClientRect().left;
    const max = Math.max(0, rail.scrollWidth - rail.clientWidth);
    return [...new Set(cards.map(card => Math.min(max, card.getBoundingClientRect().left - origin)))];
  }
  function updateRail() {
    const max = rail.scrollWidth - rail.clientWidth;
    const positions = stops();
    const index = positions.reduce((best, position, i) => Math.abs(position - rail.scrollLeft) < Math.abs(positions[best] - rail.scrollLeft) ? i : best, 0);
    controls.hidden = max <= 2;
    previous.disabled = rail.scrollLeft <= 2;
    next.disabled = rail.scrollLeft >= max - 2;
    const visible = Math.max(1, cards.filter(card => {
      const box = card.getBoundingClientRect();
      const bounds = rail.getBoundingClientRect();
      return box.left >= bounds.left - 2 && box.right <= bounds.right + 2;
    }).length);
    const label = `${index + 1}${visible > 1 ? `–${Math.min(cards.length, index + visible)}` : ''} / ${cards.length}`;
    if (count.textContent !== label) count.textContent = label;
  }
  function move(direction, keyboard = false) {
    const positions = stops();
    const destination = direction > 0 ? positions.find(x => x > rail.scrollLeft + 2) : positions.reverse().find(x => x < rail.scrollLeft - 2);
    if (destination !== undefined) rail.scrollTo({left:destination, behavior:keyboard || reduced.matches ? 'instant' : 'smooth'});
  }
  previous.addEventListener('click', () => move(-1));
  next.addEventListener('click', () => move(1));
  rail.addEventListener('keydown', event => {
    if (event.altKey || event.ctrlKey || event.metaKey || !['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
    event.preventDefault();
    if (event.key === 'Home' || event.key === 'End') rail.scrollTo({left:event.key === 'Home' ? 0 : rail.scrollWidth, behavior:'instant'});
    else move(event.key === 'ArrowRight' ? 1 : -1, true);
  });
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => { scheduled = false; updateRail(); });
  }
  rail.addEventListener('scroll', schedule, {passive:true});
  new ResizeObserver(schedule).observe(rail);
  document.fonts?.ready.then(schedule);

  function showError() {
    if (!active) return;
    status.textContent = 'Не удалось загрузить видео. Попробуйте снова или откройте его отдельно.';
    retry.hidden = false;
    fallback.hidden = false;
    fullscreen.disabled = true;
  }
  function play() {
    const attempt = ++generation;
    retry.hidden = true;
    fallback.hidden = true;
    fullscreen.disabled = true;
    status.textContent = 'Загружаем видео…';
    video.src = active.href;
    video.play().catch(error => {
      if (attempt !== generation || !active || error.name === 'AbortError') return;
      if (error.name === 'NotAllowedError') status.textContent = 'Нажмите воспроизведение в плеере.';
      else showError();
    });
  }
  section.querySelectorAll('[data-project-video]').forEach(link => {
    link.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
      event.preventDefault();
      active = link;
      title.textContent = link.dataset.title;
      video.poster = link.querySelector('img').src;
      fallback.href = link.href;
      savedOverflow = document.body.style.overflow;
      dialog.showModal();
      document.body.style.overflow = 'hidden';
      play();
    });
  });
  dialog.querySelector('[data-video-close]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const box = dialog.getBoundingClientRect();
    if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close();
  });
  dialog.addEventListener('close', () => {
    const opener = active;
    active = null;
    generation++;
    video.pause();
    video.removeAttribute('src');
    video.removeAttribute('poster');
    video.load();
    document.body.style.overflow = savedOverflow;
    opener?.focus({preventScroll:true});
  });
  retry.addEventListener('click', play);
  video.addEventListener('error', showError);
  video.addEventListener('waiting', () => { if (active) status.textContent = 'Загружаем видео…'; });
  video.addEventListener('playing', () => { if (active) status.textContent = ''; });
  video.addEventListener('canplay', () => {
    if (!active) return;
    status.textContent = '';
    fullscreen.disabled = !(video.requestFullscreen || video.webkitEnterFullscreen);
  });
  fullscreen.addEventListener('click', () => {
    try {
      if (video.webkitEnterFullscreen) video.webkitEnterFullscreen();
      else video.requestFullscreen().catch(() => { status.textContent = 'Полный экран недоступен. Продолжайте просмотр в плеере.'; });
    } catch {
      status.textContent = 'Полный экран недоступен. Продолжайте просмотр в плеере.';
    }
  });
  updateRail();
})();
