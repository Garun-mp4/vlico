(() => {
  const configNode = document.getElementById('site-config');
  if (!configNode) return;
  const config = JSON.parse(configNode.textContent);
  const panel = document.querySelector('[data-privacy-panel]');
  const form = document.querySelector('[data-privacy-form]');
  const ttl = 180 * 86400000;
  let choice = { analytics: false, external: false }, accepted = false, counterReady = false, tag = null;
  let returnFocus = null;
  const pendingLeads = new Map(), pendingGoals = [];
  try {
    const saved = JSON.parse(localStorage.getItem('vlicoPrivacy'));
    if (saved?.version === config.consent_version && saved.expires > Date.now()) {
      choice = { analytics: saved.analytics === true, external: saved.external === true }; accepted = true;
    }
  } catch { /* Optional services remain disabled when storage is unavailable. */ }
  const mayTrack = () => choice.analytics && config.analytics_enabled && Boolean(config.counter);
  const goals = new Set(['phone_click', 'telegram_click', 'whatsapp_click', 'instagram_click', 'map_click', 'reviews_click', 'review_write_click', 'service_request_click', 'lead_success', 'lead_consultation', 'lead_measurement', 'lead_project', 'lead_partner', 'lead_calculator']);
  function goal(name) {
    if (!mayTrack() || !goals.has(name)) return;
    if (counterReady) window.ym(Number(config.counter), 'reachGoal', name);
    else pendingGoals.push(name);
  }
  function trackLead(kind, reference) {
    if (!mayTrack() || !reference || !goals.has(`lead_${kind}`)) return;
    // References are used only for local deduplication and never sent to Metrika.
    const key = `vlicoGoal:${reference}`;
    try { if (sessionStorage.getItem(key)) return; } catch { /* No persistent deduplication. */ }
    if (!counterReady) { pendingLeads.set(reference, kind); return; }
    goal('lead_success');
    goal(`lead_${kind}`);
    try { sessionStorage.setItem(key, '1'); } catch { /* Event remains valid. */ }
  }
  const success = document.querySelector('[data-lead-success]');
  function startAnalytics() {
    if (!mayTrack() || counterReady || tag) return;
    const ym = window.ym = window.ym || function () { (ym.a = ym.a || []).push(arguments); };
    ym.l = Date.now();
    const script = document.createElement('script'); tag = script; script.async = true; script.src = 'https://mc.yandex.ru/metrika/tag.js';
    script.onload = () => {
      if (tag !== script || !mayTrack()) return;
      window.ym(Number(config.counter), 'init', { defer: true, webvisor: false, clickmap: false, trackLinks: false, accurateTrackBounce: false, disableYtm: true });
      // Send a canonical URL without query, hash, form contents or contact information.
      let referer = '';
      try { if (document.referrer) referer = new URL(document.referrer).origin + '/'; } catch { /* No referrer. */ }
      window.ym(Number(config.counter), 'hit', config.canonical, { title: document.title, referer });
      counterReady = true;
      pendingGoals.splice(0).forEach(goal);
      pendingLeads.forEach((kind, reference) => trackLead(kind, reference)); pendingLeads.clear();
      if (success) trackLead(success.dataset.kind, success.dataset.reference);
    };
    script.onerror = () => { script.remove(); if (tag === script) tag = null; };
    document.head.append(script);
  }
  const sources = {
    rating: ['https://yandex.ru/sprav/widget/rating-badge/164382623295?type=rating', 'Актуальный рейтинг VLICO на Яндекс Картах'],
    reviews: ['https://yandex.ru/maps-reviews-widget/164382623295?comments', 'Отзывы клиентов VLICO на Яндекс Картах'],
  };
  function updateWidgets() {
    document.querySelectorAll('[data-external-widget]').forEach(host => {
      const frame = host.querySelector('iframe');
      if (!choice.external) { frame?.remove(); host.querySelectorAll(':scope > :not(iframe)').forEach(node => { node.hidden = false; }); return; }
      if (frame) return;
      const source = sources[host.dataset.externalWidget];
      if (!source) return;
      const iframe = document.createElement('iframe'); iframe.src = source[0]; iframe.title = source[1];
      iframe.loading = 'lazy'; iframe.referrerPolicy = 'no-referrer'; iframe.setAttribute('frameborder', '0');
      iframe.width = host.dataset.externalWidget === 'rating' ? '150' : '760';
      iframe.height = host.dataset.externalWidget === 'rating' ? '50' : '960';
      // Keep a real link available even when a third-party frame fails to load.
      host.append(iframe);
      host.querySelectorAll(':scope > button').forEach(node => { node.hidden = true; });
      host.querySelector('.external-fallback')?.setAttribute('hidden', '');
    });
  }
  function apply() {
    if (mayTrack()) startAnalytics();
    else {
      if (counterReady && window.ym) window.ym(Number(config.counter), 'destruct');
      counterReady = false; tag?.remove(); tag = null;
      pendingLeads.clear(); pendingGoals.length = 0;
    }
    updateWidgets();
  }
  function show(trigger) {
    returnFocus = trigger || null;
    form.elements.analytics.checked = choice.analytics;
    form.elements.external.checked = choice.external;
    panel.hidden = false;
    if (trigger) form.elements.analytics.focus();
  }
  function save(essential = false) {
    choice = { analytics: !essential && form.elements.analytics.checked, external: !essential && form.elements.external.checked };
    try { localStorage.setItem('vlicoPrivacy', JSON.stringify({ ...choice, version: config.consent_version, expires: Date.now() + ttl })); } catch { /* Choice lasts only for this page. */ }
    panel.hidden = true; apply(); returnFocus?.focus();
  }
  form.addEventListener('submit', event => { event.preventDefault(); save(); });
  panel.querySelector('[data-privacy-essential]').addEventListener('click', () => save(true));
  document.addEventListener('click', event => {
    const external = event.target.closest('[data-external-enable]');
    if (external) {
      returnFocus = null;
      form.elements.analytics.checked = choice.analytics;
      form.elements.external.checked = true;
      save();
      external.closest('[data-external-widget]')?.querySelector('iframe')?.focus({ preventScroll: true });
    }
    const trigger = event.target.closest('[data-privacy-open]');
    if (trigger) show(trigger);
    const link = event.target.closest('[data-goal]');
    if (link) goal(link.dataset.goal);
  });
  document.addEventListener('vlico:lead-saved', event => trackLead(event.detail?.kind, event.detail?.reference));
  if (!accepted) show();
  apply();
})();
