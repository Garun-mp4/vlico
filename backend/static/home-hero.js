(() => {
  const solutionList = document.querySelector('[data-home-solutions]');
  if (!solutionList) return;

  const cards = [...solutionList.querySelectorAll('[data-home-solution]')];
  const media = window.matchMedia('(max-width: 760px)');
  const wide = window.matchMedia('(min-width: 1100px)');
  const layout = solutionList.closest('[data-hero-layout]');
  const intro = layout.querySelector('[data-hero-intro]');
  const introToggle = intro.querySelector('.home-hero-overview');
  const introCopy = intro.querySelector('.home-hero-copy');
  const panels = [intro, ...cards];
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
  let activeCard = cards.find(card => card.open) || null;
  let pinnedCard = null;
  let hoveredCard = null;
  let stickyScheduled = false;
  let restoringFocus = false;
  let lastPointer = null;

  function selectWidePanel(panel, animate = false) {
    const index = panels.indexOf(panel);
    if (layout.dataset.heroActive === String(index)) return;
    const previous = panels[Number(layout.dataset.heroActive)];
    const focus = document.activeElement;
    if (previous && previous !== panel && previous.contains(focus) &&
        focus.closest('.home-hero-copy, .home-solution-detail')) {
      restoringFocus = true;
      previous.querySelector('summary, .home-hero-overview').focus({ preventScroll: true });
      restoringFocus = false;
    }
    layout.toggleAttribute('data-hero-motion', animate);
    layout.dataset.heroActive = String(index);
    intro.toggleAttribute('data-hero-current', panel === intro);
    introToggle.setAttribute('aria-expanded', String(panel === intro));
    introCopy.inert = panel !== intro;
    setActiveCard(panel === intro ? null : panel);
  }

  function syncLayout() {
    lastPointer = null;
    layout.removeAttribute('data-hero-motion');
    delete layout.dataset.heroActive;
    layout.toggleAttribute('data-hero-wide', wide.matches);
    if (wide.matches) {
      selectWidePanel(intro);
    } else {
      intro.removeAttribute('data-hero-current');
      introToggle.removeAttribute('aria-expanded');
      introCopy.inert = false;
      pinnedCard = hoveredCard = null;
      setActiveCard(null);
    }
  }

  // Boundary events can fire under a stationary cursor as the tracks move.
  // Only a new mouse position may choose a different panel.
  layout.addEventListener('pointermove', event => {
    if (!wide.matches || !finePointer.matches || event.pointerType !== 'mouse') return;
    if (lastPointer?.x === event.clientX && lastPointer?.y === event.clientY) return;
    lastPointer = { x: event.clientX, y: event.clientY };
    const panel = event.target.closest('[data-hero-intro], [data-home-solution]');
    if (panel) selectWidePanel(panel, true);
  });
  layout.addEventListener('pointerleave', () => { lastPointer = null; });

  introToggle.addEventListener('click', event => {
    if (wide.matches) selectWidePanel(intro, event.detail > 0);
  });
  introToggle.addEventListener('focus', () => {
    if (wide.matches && !restoringFocus && introToggle.matches(':focus-visible')) selectWidePanel(intro);
  });

  function setActiveCard(target) {
    activeCard = target;
    cards.forEach(card => {
      const open = card === target;
      card.open = open;
      card.querySelector('summary')?.setAttribute('aria-expanded', String(open));
    });
  }

  cards.forEach(card => {
    const summary = card.querySelector('summary');
    summary.setAttribute('aria-expanded', String(card.open));

    summary.addEventListener('click', event => {
      event.preventDefault();
      if (wide.matches) {
        selectWidePanel(card, event.detail > 0);
        return;
      }
      if (pinnedCard === card && activeCard === card) {
        pinnedCard = null;
        setActiveCard(null);
        return;
      }
      pinnedCard = card;
      setActiveCard(card);
    });

    card.addEventListener('pointerenter', event => {
      if (wide.matches || !finePointer.matches || event.pointerType !== 'mouse') return;
      hoveredCard = card;
      if (!pinnedCard) setActiveCard(card);
    });

    card.addEventListener('pointerleave', () => {
      if (wide.matches) return;
      if (hoveredCard === card) hoveredCard = null;
      if (activeCard === card && pinnedCard !== card && !card.contains(document.activeElement)) setActiveCard(null);
    });

    card.addEventListener('focusin', () => {
      if (restoringFocus) return;
      if (wide.matches) {
        if (document.activeElement.matches(':focus-visible')) selectWidePanel(card);
        return;
      }
      if (pinnedCard !== card) pinnedCard = null;
      setActiveCard(card);
    });

    card.addEventListener('focusout', event => {
      if (wide.matches || card.contains(event.relatedTarget)) return;
      requestAnimationFrame(() => {
        if (!wide.matches && activeCard === card && pinnedCard !== card && hoveredCard !== card && !card.contains(document.activeElement)) setActiveCard(null);
      });
    });
  });

  layout.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || !activeCard) return;
    event.preventDefault();
    event.stopPropagation();
    const card = activeCard;
    pinnedCard = null;
    hoveredCard = null;
    restoringFocus = true;
    card.querySelector('summary')?.focus();
    if (wide.matches) selectWidePanel(intro);
    else setActiveCard(null);
    restoringFocus = false;
  });

  wide.addEventListener('change', syncLayout);
  syncLayout();

  const ratingStrip = document.querySelector('.home-rating');
  const ratingSource = ratingStrip?.querySelector('[data-home-rating-slot]');
  const rating = ratingSource?.querySelector('[data-home-rating]');
  const ratingTarget = intro.querySelector('[data-hero-rating-slot]');
  const heroFooter = intro.querySelector('.home-hero-footer');

  if (rating && ratingTarget && heroFooter) {
    function syncRatingPlacement() {
      const target = wide.matches ? ratingTarget : ratingSource;
      if (rating.parentElement !== target) target.append(rating);
      ratingStrip.hidden = wide.matches;
      heroFooter.classList.toggle('has-home-rating', wide.matches);
    }
    wide.addEventListener('change', syncRatingPlacement);
    syncRatingPlacement();
  }

  const sticky = document.querySelector('[data-home-sticky-cta]');
  const primaryAction = document.querySelector('.home-hero-primary');
  const contact = document.getElementById('contact');
  const portfolioControls = document.querySelectorAll('#projects a, #projects button, #project-videos a, #project-videos button, .new-solutions a, .new-solutions button, .partners-home-entry a');
  const contactHeading = document.getElementById('contact-title');
  const privacyPanel = document.querySelector('[data-privacy-panel]');
  const mobileMenu = document.querySelector('[data-header-mobile]');

  if (!sticky || !primaryAction || !contact) return;
  contactHeading?.setAttribute('tabindex', '-1');

  sticky.addEventListener('click', () => {
    requestAnimationFrame(() => contactHeading?.focus({ preventScroll: true }));
  });

  function updateSticky() {
    stickyScheduled = false;
    const bounds = primaryAction.getBoundingClientRect();
    const primaryHasPassed = bounds.bottom <= 0;
    const contactBounds = contact.getBoundingClientRect();
    const contactInView = contactBounds.top < window.innerHeight && contactBounds.bottom > 0;
    const textFieldFocused = document.activeElement?.matches('input, textarea, select, [contenteditable="true"]');
    const keyboardOpen = window.visualViewport && window.visualViewport.height < window.innerHeight * .72;
    const consentOpen = privacyPanel && !privacyPanel.hidden;
    const overlayOpen = Boolean(mobileMenu?.open || document.querySelector('dialog[open]'));
    const overlapsPortfolioControl = media.matches && [...portfolioControls].some(control => {
      const rect = control.getBoundingClientRect();
      return rect.width && rect.height && rect.top < window.innerHeight - 12 && rect.bottom > window.innerHeight - 84;
    });
    const shouldShow = !overlapsPortfolioControl && media.matches && primaryHasPassed && !contactInView && contactBounds.bottom > 0 && !textFieldFocused && !keyboardOpen && !consentOpen && !overlayOpen;
    sticky.hidden = !shouldShow;
  }

  function scheduleStickyUpdate() {
    if (stickyScheduled) return;
    stickyScheduled = true;
    requestAnimationFrame(updateSticky);
  }

  window.addEventListener('scroll', scheduleStickyUpdate, { passive: true });
  window.addEventListener('resize', scheduleStickyUpdate, { passive: true });
  window.visualViewport?.addEventListener('resize', scheduleStickyUpdate, { passive: true });
  document.addEventListener('focusin', scheduleStickyUpdate);
  document.addEventListener('focusout', scheduleStickyUpdate);
  mobileMenu?.addEventListener('toggle', scheduleStickyUpdate);

  if (privacyPanel) {
    new MutationObserver(scheduleStickyUpdate).observe(privacyPanel, { attributes: true, attributeFilter: ['hidden'] });
  }
  new MutationObserver(scheduleStickyUpdate).observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['open'] });

  updateSticky();
})();
