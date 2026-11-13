(() => {
  'use strict';
  const launch = document.querySelector('[data-eva-open]');
  const dialog = document.querySelector('#vlico-eva-dialog');
  if (!launch || !dialog || typeof dialog.showModal !== 'function') { launch?.remove(); return; }
  const host = dialog.querySelector('.eva-chat-host');
  const status = dialog.querySelector('[data-eva-status]');
  const privacy = document.querySelector('[data-privacy-panel]');
  const placeLauncher = () => {
    const top = privacy && !privacy.hidden ? privacy.getBoundingClientRect().top : innerHeight;
    launch.style.bottom = `${Math.max(96, innerHeight - top + 16)}px`;
  };
  placeLauncher();
  window.addEventListener('resize', placeLauncher);
  if (privacy) {
    new MutationObserver(placeLauncher).observe(privacy, { attributes: true, attributeFilter: ['hidden'] });
    if (typeof ResizeObserver === 'function') new ResizeObserver(placeLauncher).observe(privacy);
  }
  let loaded = false;
  launch.addEventListener('click', () => {
    dialog.showModal();
    if (loaded) return;
    loaded = true;
    const script = document.createElement('script');
    // Official Eva embedded mode; only a public channel id goes to the browser.
    script.src = `https://eva.bz/widget/chat-widget.js?widgetId=${encodeURIComponent(host.id)}&containerId=${encodeURIComponent(host.id)}&language=ru`;
    script.async = true;
    script.onload = () => { status.hidden = true; };
    script.onerror = () => { status.textContent = 'Чат временно недоступен. Оставьте заявку через форму сайта.'; };
    document.body.append(script);
  });
  dialog.querySelector('[data-eva-close]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => launch.focus());
})();
