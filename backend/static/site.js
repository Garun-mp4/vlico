(() => {
  const configNode = document.getElementById('site-config');
  if (!configNode) return;
  const config = JSON.parse(configNode.textContent);
  const panel = document.querySelector('[data-privacy-panel]');
  const ttl = 180 * 86400000;
  let choice = { analytics: false }, accepted = false, counterReady = false, tag = null;
  let returnFocus = null;
  const pendingLeads = new Map(), pendingGoals = [], pendingChatAcceptances = new Set();
  try {
    const saved = JSON.parse(localStorage.getItem('vlicoPrivacy'));
    if (saved?.version === config.consent_version && saved.expires > Date.now()) {
      choice = { analytics: saved.analytics === true }; accepted = true;
    }
  } catch { /* Optional services remain disabled when storage is unavailable. */ }
  const mayTrack = () => choice.analytics && config.analytics_enabled && Boolean(config.counter);
  const goals = new Set(['phone_click', 'telegram_click', 'whatsapp_click', 'instagram_click', 'map_click', 'reviews_click', 'review_write_click', 'service_request_click', 'lead_success', 'lead_consultation', 'lead_measurement', 'lead_project', 'lead_partner', 'lead_calculator']);
  goals.add('eva_chat_open');
  goals.add('eva_chat_first_message');
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
  function trackChatAcceptance(reference) {
    if (!mayTrack() || !reference) return;
    // Only the goal name goes to Metrika. The reference stays in this tab.
    const key = `vlicoChatGoal:${reference}`;
    try { if (sessionStorage.getItem(key)) return; } catch { /* No persistent deduplication. */ }
    if (!counterReady) { pendingChatAcceptances.add(reference); return; }
    goal('eva_chat_first_message');
    try { sessionStorage.setItem(key, '1'); } catch { /* This page still deduplicates. */ }
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
      pendingChatAcceptances.forEach(trackChatAcceptance); pendingChatAcceptances.clear();
      if (success) trackLead(success.dataset.kind, success.dataset.reference);
    };
    script.onerror = () => { script.remove(); if (tag === script) tag = null; };
    document.head.append(script);
  }
  function apply() {
    if (mayTrack()) startAnalytics();
    else {
      if (counterReady && window.ym) window.ym(Number(config.counter), 'destruct');
      counterReady = false; tag?.remove(); tag = null;
      pendingLeads.clear(); pendingChatAcceptances.clear(); pendingGoals.length = 0;
    }
  }
  function show(trigger) {
    returnFocus = trigger || null;
    panel.hidden = false;
    if (trigger) panel.querySelector('[data-privacy-accept]').focus();
  }
  function save(analytics) {
    choice = { analytics };
    try { localStorage.setItem('vlicoPrivacy', JSON.stringify({ ...choice, version: config.consent_version, expires: Date.now() + ttl })); } catch { /* Choice lasts only for this page. */ }
    panel.hidden = true; apply(); returnFocus?.focus();
  }
  panel.querySelector('[data-privacy-accept]').addEventListener('click', () => save(true));
  panel.querySelector('[data-privacy-essential]').addEventListener('click', () => save(false));
  document.addEventListener('click', event => {
    const trigger = event.target.closest('[data-privacy-open]');
    if (trigger) show(trigger);
    const link = event.target.closest('[data-goal]');
    if (link) goal(link.dataset.goal);
  });
  document.addEventListener('vlico:lead-saved', event => trackLead(event.detail?.kind, event.detail?.reference));
  document.addEventListener('vlico:chat-opened', () => goal('eva_chat_open'));
  document.addEventListener('vlico:chat-first-accepted', event => trackChatAcceptance(event.detail?.reference));
  if (!accepted) show();
  apply();
})();
