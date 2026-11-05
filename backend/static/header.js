(() => {
  const header = document.querySelector('[data-site-header]');
  if (!header) return;
  const mobile = header.querySelector('[data-header-mobile]');
  const finePointer = matchMedia('(hover: hover) and (pointer: fine)');
  const desktop = matchMedia('(min-width: 961px)');
  const groups = [];
  header.querySelectorAll('[data-project-nav]').forEach(root => {
    const button = root.querySelector('button');
    const panel = root.querySelector('.project-nav-panel');
    let timer;
    const isOpen = () => button.getAttribute('aria-expanded') === 'true';
    const setOpen = open => {
      clearTimeout(timer);
      if (open) groups.forEach(group => { if (group.root !== root) group.close(); });
      button.setAttribute('aria-expanded', String(open));
      panel.inert = !open;
      panel.setAttribute('aria-hidden', String(!open));
      root.dataset.open = String(open);
    };
    groups.push({root, isOpen, close: () => setOpen(false), button});
    setOpen(false);
    panel.hidden = false;
    button.hidden = false;
    button.addEventListener('click', () => setOpen(!isOpen()));
    root.addEventListener('pointerenter', event => {
      if (!desktop.matches || !finePointer.matches || event.pointerType !== 'mouse') return;
      setOpen(true);
    });
    root.addEventListener('pointerleave', () => {
      timer = setTimeout(() => { if (!root.contains(document.activeElement)) setOpen(false); }, 140);
    });
    root.addEventListener('focusout', event => {
      if (!root.contains(event.relatedTarget)) setOpen(false);
    });
    root.addEventListener('keydown', event => {
      if (event.key === 'Escape' && isOpen()) {
        event.preventDefault(); event.stopPropagation(); setOpen(false); button.focus();
      } else if (event.key === 'ArrowDown' && event.target.closest('.project-nav-trigger')) {
        event.preventDefault(); setOpen(true); panel.querySelector('a')?.focus();
      }
    });
    panel.addEventListener('click', event => { if (event.target.closest('a')) setOpen(false); });
  });
  const closeAll = () => groups.forEach(group => group.close());
  document.addEventListener('pointerdown', event => {
    if (header.contains(event.target)) return;
    closeAll(); mobile.open = false;
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    if (groups.some(group => group.isOpen())) { event.preventDefault(); closeAll(); }
    if (mobile.open) {
      event.preventDefault(); mobile.open = false; mobile.querySelector('summary').focus();
    }
  });
  mobile.addEventListener('toggle', () => {
    mobile.querySelector('summary').setAttribute('aria-label', mobile.open ? 'Закрыть меню' : 'Открыть меню');
    if (!mobile.open) closeAll();
  });
  mobile.querySelectorAll('a').forEach(link => link.addEventListener('click', () => { mobile.open = false; }));
  desktop.addEventListener('change', () => { closeAll(); mobile.open = false; });
  window.addEventListener('pageshow', closeAll);
  if (header.hasAttribute('data-over-hero')) {
    let scheduled = false;
    const update = () => { header.classList.toggle('is-scrolled', scrollY > 34); scheduled = false; };
    window.addEventListener('scroll', () => {
      if (!scheduled) { scheduled = true; requestAnimationFrame(update); }
    }, {passive:true});
    update();
  }
})();
