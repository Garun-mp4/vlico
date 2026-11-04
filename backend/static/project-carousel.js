document.querySelectorAll('[data-project-carousel]').forEach((carousel) => {
  const track = carousel.querySelector('.project-carousel-track');
  const slides = [...track.querySelectorAll('.project-carousel-slide')];
  const previous = carousel.querySelector('.project-carousel-prev');
  const next = carousel.querySelector('.project-carousel-next');
  const number = carousel.querySelector('[data-photo-number]');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let index = 0;
  let destination = 0;
  let scrolling = false;
  let settleTimer;
  let pointer = null;
  let suppressClick = false;
  let clickTimer;

  function update(current) {
    index = Math.max(0, Math.min(slides.length - 1, current));
    previous.disabled = index === 0;
    next.disabled = index === slides.length - 1;
    number.textContent = String(index + 1);
    slides.forEach((slide, position) => {
      slide.tabIndex = position === index ? 0 : -1;
    });
  }

  function goTo(current, animate = true) {
    destination = Math.max(0, Math.min(slides.length - 1, current));
    scrolling = true;
    update(destination);
    track.scrollTo({
      left: destination * track.clientWidth,
      behavior: animate && !reducedMotion.matches ? 'smooth' : 'instant',
    });
  }

  previous.addEventListener('click', () => goTo(destination - 1));
  next.addEventListener('click', () => goTo(destination + 1));
  track.addEventListener('keydown', (event) => {
    const actions = { ArrowLeft: destination - 1, ArrowRight: destination + 1, Home: 0, End: slides.length - 1 };
    if (!(event.key in actions) || event.altKey || event.ctrlKey || event.metaKey) return;
    event.preventDefault();
    goTo(actions[event.key], false);
  });

  track.addEventListener('scroll', () => {
    if (!scrolling && !pointer?.dragging) {
      destination = Math.round(track.scrollLeft / track.clientWidth);
      update(destination);
    }
    clearTimeout(settleTimer);
    settleTimer = setTimeout(() => {
      if (pointer?.dragging) return;
      scrolling = false;
      destination = Math.round(track.scrollLeft / track.clientWidth);
      update(destination);
    }, 140);
  }, { passive: true });

  // Touch uses native scrolling; only mouse dragging needs an additional handler.
  track.addEventListener('pointerdown', (event) => {
    if (event.pointerType !== 'mouse' || event.button !== 0 || !event.isPrimary) return;
    pointer = { id: event.pointerId, x: event.clientX, y: event.clientY, left: track.scrollLeft, start: index, dragging: false };
  });
  track.addEventListener('pointermove', (event) => {
    if (!pointer || event.pointerId !== pointer.id) return;
    const dx = event.clientX - pointer.x;
    if (!pointer.dragging) {
      if (Math.abs(dx) < 6) return;
      if (Math.abs(event.clientY - pointer.y) > Math.abs(dx)) {
        pointer = null;
        return;
      }
      pointer.dragging = true;
      scrolling = false;
      track.classList.add('is-dragging');
      track.setPointerCapture(event.pointerId);
    }
    event.preventDefault();
    track.scrollLeft = pointer.left - dx;
  });

  function endDrag(event) {
    if (!pointer || event.pointerId !== pointer.id) return;
    const drag = pointer;
    pointer = null;
    if (!drag.dragging) return;
    const distance = track.scrollLeft - drag.left;
    let current = Math.round(track.scrollLeft / track.clientWidth);
    if (event.type !== 'pointercancel' && current === drag.start && Math.abs(distance) > Math.min(60, track.clientWidth * 0.15)) {
      current += Math.sign(distance);
    }
    suppressClick = true;
    clearTimeout(clickTimer);
    clickTimer = setTimeout(() => { suppressClick = false; }, 400);
    track.classList.remove('is-dragging');
    if (track.hasPointerCapture(event.pointerId)) track.releasePointerCapture(event.pointerId);
    goTo(current);
  }
  track.addEventListener('pointerup', endDrag);
  track.addEventListener('pointercancel', endDrag);
  track.addEventListener('lostpointercapture', endDrag);
  track.addEventListener('dragstart', (event) => event.preventDefault());
  track.addEventListener('click', (event) => {
    if (!suppressClick) return;
    event.preventDefault();
    event.stopPropagation();
    suppressClick = false;
  }, true);

  new ResizeObserver(() => {
    if (!pointer?.dragging) goTo(destination, false);
  }).observe(track);
  update(0);
  carousel.querySelector('.project-carousel-controls').hidden = false;
});
