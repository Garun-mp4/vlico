(() => {
  // Eva renders the floating launcher and a separate shadow root for the mobile chat.
  const launcherHostId = 'chat-widget-container';
  const mobileHostId = 'eva-chat-widget-mobile-host';
  const hosts = new WeakSet();
  const privacy = document.querySelector('[data-privacy-panel]');
  const stickyAction = document.querySelector('[data-home-sticky-cta]');
  const fallback = document.querySelector('[data-vlico-chat-fallback]');
  const invitationTemplate = document.getElementById('vlico-chat-invitation');
  const invitationKey = 'vlico-chat-invitation-v2-dismissed';
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  let openingBounds;
  let closing = false;
  let launcherHost;
  let mobileHost;
  let widget;
  let invitation;
  let launcher;
  let invitationReady = false;
  let invitationFinished = false;
  try {
    invitationFinished = sessionStorage.getItem(invitationKey) === '1';
  } catch {
    // The invitation can still be dismissed on this page if storage is blocked.
  }

  const styles = `
    :host {
      --vlico-chat-size: 56px;
      --vlico-chat-gap: max(24px, calc(env(safe-area-inset-bottom, 0px) + 12px));
      --vlico-chat-ink: #19191a;
      --vlico-chat-paper: #f2f1e9;
      --vlico-chat-sand: #eae8dd;
      --vlico-chat-rule: #d5d3c8;
      --vlico-chat-green: #27be82;
      --vlico-chat-focus: #075f40;
      --vlico-chat-mono: "IBM Plex Mono", "Cascadia Mono", monospace;
      --vlico-chat-title: Manrope, Arial, sans-serif;
      --vlico-chat-ease: var(--ease-out, cubic-bezier(.2, .7, .2, 1));
    }
    @media (max-width: 760px) {
      :host {
        --vlico-chat-gap: max(16px, calc(env(safe-area-inset-bottom, 0px) + 12px));
      }
    }
    #chat-widget.chat-widget--popup .chat-bar {
      inset: auto max(16px, env(safe-area-inset-right)) var(--vlico-chat-bottom, var(--vlico-chat-gap)) auto !important;
      width: var(--vlico-chat-size) !important;
      max-width: none !important;
      height: var(--vlico-chat-size) !important;
      padding: 0 !important;
      justify-content: flex-start;
      padding-inline-start: calc((var(--vlico-chat-size) - 26px) / 2) !important;
      gap: 0;
      cursor: pointer;
      touch-action: manipulation;
      color: var(--vlico-chat-paper);
      border-radius: 4px;
      overflow: visible;
      isolation: isolate;
      transition: none;
      transform: none;
    }
    #chat-widget.chat-widget--popup .chat-bar::before {
      background: var(--vlico-chat-ink);
      border-radius: 4px !important;
      box-shadow: none;
      animation: none;
      transform: none;
    }
    #chat-widget .chat-bar .text, #chat-widget .chat-bar__close { display: none; }
    #chat-widget.chat-widget--popup .chat-bar::after {
      content: "";
      position: absolute;
      z-index: -2;
      inset: 0;
      border-radius: inherit;
      box-shadow: 0 0 9px 2px #f2be8d, 0 0 22px 4px #d8945066;
      pointer-events: none;
      opacity: .55;
      animation: vlico-chat-glow 10s ease-in-out infinite;
    }
    @keyframes vlico-chat-glow {
      0%, 35%, 100% { opacity: .2; }
      25%, 60% { opacity: 1; }
    }
    #chat-widget .chat-bar .icon { width: 26px; height: 26px; flex: 0 0 26px; }
    #chat-widget .vlico-chat-label {
      position: absolute;
      inset-inline-start: 50px;
      inset-inline-end: 0;
      overflow: hidden;
      white-space: nowrap;
      font: 500 13px/1 var(--vlico-chat-mono);
      opacity: 0;
      pointer-events: none;
    }
    @media (min-width: 761px) {
      #chat-widget.chat-widget--popup .chat-bar {
        transition: width 240ms var(--vlico-chat-ease) !important;
      }
      #chat-widget.chat-widget--popup .chat-bar:focus-visible {
        width: 164px !important;
        transition: none !important;
      }
      #chat-widget .chat-bar:focus-visible .vlico-chat-label {
        opacity: 1;
      }
      @media (hover: hover) and (pointer: fine) {
        #chat-widget.chat-widget--popup .chat-bar:hover::after { opacity: 1 !important; }
        #chat-widget .vlico-chat-label { transition: opacity 170ms ease-out; }
        #chat-widget.chat-widget--popup .chat-bar:hover {
          width: 164px !important;
        }
        #chat-widget .chat-bar:hover .vlico-chat-label {
          opacity: 1;
        }
      }
    }
    #chat-widget .chat-bar .badge { position: absolute; top: -3px; right: -3px; border-color: #075f40; }
    #chat-widget.chat-widget--chat-open .chat-bar { visibility: hidden; }
    #chat-widget:not(.chat-widget--chat-open) .chat-window.popup { visibility: hidden; }
    .chat-window.popup {
      --widget-font: var(--vlico-chat-mono);
      --widget-font-size-message: 14px;
      --widget-line-height-message: 1.55;
      --widget-letter-spacing-message: 0;
      color: var(--vlico-chat-ink);
      font-family: var(--vlico-chat-mono);
      border-radius: 4px;
      box-shadow: 0 8px 28px #19191a24;
      transition: none !important;
    }
    .chat-window.popup .chat-card, .chat-window.popup .chat-body,
    .chat-window.popup .chat-footer, .chat-window.popup .chat-compose {
      background: var(--vlico-chat-paper);
    }
    .chat-window.popup .chat-title {
      background: var(--vlico-chat-ink);
      color: var(--vlico-chat-paper);
      border-radius: 0;
      padding-block: max(10px, env(safe-area-inset-top, 0px)) 10px;
    }
    .chat-window .chat-title h3, .vlico-chat-empty strong {
      font: 700 19px/1.2 var(--vlico-chat-title);
      letter-spacing: -.02em;
    }
    .chat-window .chat-title .subtitle {
      font: 400 0/1.4 var(--vlico-chat-mono);
      color: var(--vlico-chat-paper);
      opacity: 1;
    }
    .chat-window .vlico-consultant { font-size: 11px; }
    .chat-window .chat-title .status-dot { background: var(--vlico-chat-green); }
    .chat-window .chat-title .close-btn {
      width: 44px;
      height: 44px;
      border-radius: 3px;
      background: transparent;
    }
    .chat-window .chat-title .close-btn:hover { background: #ffffff19; }
    .chat-window.popup .message-bubble {
      padding: 9px 12px;
      border: 0;
      border-radius: 3px;
      box-shadow: none;
      overflow-wrap: anywhere;
    }
    .chat-window .message.user .message-bubble {
      background: var(--vlico-chat-ink);
      color: var(--vlico-chat-paper);
    }
    .chat-window .message:not(.user) .message-bubble {
      background: #e9dfcc;
      color: var(--vlico-chat-ink);
      border: 1px solid #d7c7ad;
    }
    .chat-window .message-text, .chat-window .message-input {
      font-family: var(--vlico-chat-mono);
    }
    .chat-window .chat-body { scrollbar-color: #a6a498 transparent; }
    .chat-window.popup .chat-footer { border-top: 1px solid var(--vlico-chat-rule); }
    .chat-window.popup .chat-footer .message-input {
      min-height: 44px;
      padding-inline: 0;
      border: 0;
      border-bottom: 1px solid #a6a498;
      border-radius: 0;
      background: transparent;
      color: var(--vlico-chat-ink);
      caret-color: var(--vlico-chat-focus);
    }
    .chat-window .message-input::placeholder { color: #68675f; opacity: 1; }
    .chat-window.popup .message-input:focus {
      border-color: var(--vlico-chat-focus);
      box-shadow: none;
    }
    .chat-window.popup .chat-footer :is(.attach-btn, .send-btn) {
      width: 44px;
      height: 44px;
      min-width: 44px;
      border-radius: 3px;
      transition: background-color 120ms ease, color 120ms ease;
    }
    .chat-window.popup .chat-footer .attach-btn {
      background: transparent;
      border: 1px solid var(--vlico-chat-rule);
      color: var(--vlico-chat-ink);
    }
    .chat-window.popup .chat-footer .send-btn {
      background: var(--vlico-chat-ink);
      color: var(--vlico-chat-paper);
    }
    .chat-window.popup .chat-footer .send-btn:hover:not(:disabled) {
      background: var(--vlico-chat-focus);
      transform: none;
    }
    .chat-window .chat-footer button:focus-visible {
      outline: 2px solid var(--vlico-chat-focus);
      outline-offset: 2px;
    }
    .chat-window .messages:has(.vlico-chat-empty) > div { padding-top: 0 !important; min-height: 180px; }
    .chat-window .messages .icon:has(~ .vlico-chat-empty) { display: none; }
    .vlico-chat-empty { color: var(--vlico-chat-ink); padding: 0 6px; }
    .vlico-chat-empty span { display: block; margin-top: 6px; font-size: 13px; color: #4d4c47; }
    #chat-widget .chat-bar:focus-visible, .chat-title .close-btn:focus-visible {
      outline: 2px solid #fff;
      outline-offset: -4px;
    }
    @media (prefers-reduced-motion: reduce) {
      #chat-widget.chat-widget--popup .chat-bar,
      #chat-widget.chat-widget--popup .chat-bar::after,
      #chat-widget .chat-bar .vlico-chat-label,
      #chat-widget.chat-widget--chat-open .chat-window.popup,
      .chat-window.popup .chat-footer button {
        transition: none !important;
        animation: none !important;
      }
      #chat-widget .chat-bar:hover .vlico-chat-label { opacity: 1; }
    }
  `;

  function positionLauncher() {
    const targets = [launcherHost, fallback, invitation];
    if (privacy && !privacy.hidden) {
      const bottom = window.innerHeight - privacy.getBoundingClientRect().top + 12;
      for (const target of targets) target?.style.setProperty('--vlico-chat-bottom', `${bottom}px`);
    } else {
      for (const target of targets) target?.style.removeProperty('--vlico-chat-bottom');
    }
  }

  function chatIsOpen() {
    return widget?.classList.contains('chat-widget--chat-open');
  }

  function rememberInvitation() {
    try { sessionStorage.setItem(invitationKey, '1'); }
    catch { /* Storage can be unavailable in private or embedded contexts. */ }
  }

  function finishInvitation() {
    invitationFinished = true;
    if (invitation) invitation.hidden = true;
    rememberInvitation();
  }

  function updateInvitation() {
    if (!invitation || invitationFinished || !invitationReady) return;
    const field = document.activeElement?.matches('input, textarea, select, [contenteditable="true"]');
    const keyboard = window.visualViewport?.height < window.innerHeight * .72;
    const busy = stickyAction && !stickyAction.hidden
      || document.querySelector('dialog[open], [data-header-mobile][open]');
    if (field || keyboard || busy || document.hidden || window.innerHeight <= 440) {
      invitation.hidden = true;
      return;
    }
    invitation.hidden = Boolean(chatIsOpen());
  }

  function labelChat(root) {
    const close = root.querySelector('.close-btn');
    close?.setAttribute('aria-label', 'Закрыть чат');
    return close;
  }

  function prepareChatCopy(root) {
    const status = root.querySelector('.chat-title .subtitle');
    if (status && !status.querySelector('.vlico-consultant')) {
      const label = document.createElement('span');
      label.className = 'vlico-consultant';
      label.textContent = 'ИИ-консультант VLICO';
      status.append(label);
      for (const child of status.childNodes) {
        if (child.nodeType === Node.TEXT_NODE) child.textContent = '';
      }
    }
    const emptyIcon = root.querySelector('.messages svg.icon[width="64"]');
    if (emptyIcon && !emptyIcon.parentElement.querySelector('.vlico-chat-empty')) {
      const hint = document.createElement('div');
      hint.className = 'vlico-chat-empty';
      const title = document.createElement('strong');
      title.textContent = 'Потолки и освещение';
      const description = document.createElement('span');
      description.textContent = 'Напишите, что хотите обсудить.';
      hint.append(title, description);
      emptyIcon.after(hint);
    }
  }

  function focusOpenChat(root) {
    const close = labelChat(root);
    if (chatIsOpen() && close?.getClientRects().length && getComputedStyle(close).visibility === 'visible') {
      close.focus({ preventScroll: true });
    }
  }

  function animateChat(panel, close = false) {
    if (!panel || !openingBounds || reducedMotion.matches) return null;
    const rect = panel.getBoundingClientRect();
    if (!rect.width || !rect.height || getComputedStyle(panel).visibility === 'hidden') return null;
    const clamp = (value, size) => Math.min(Math.max(value, 0), size);
    const width = Math.min(openingBounds.width, rect.width);
    const height = Math.min(openingBounds.height, rect.height);
    const left = clamp(openingBounds.left - rect.left, rect.width - width);
    const top = clamp(openingBounds.top - rect.top, rect.height - height);
    // Translate the clipped area back to the trigger, including when it is outside the window.
    const start = {
      clipPath: `inset(${top}px ${rect.width - left - width}px ${rect.height - top - height}px ${left}px round 4px)`,
      translate: `${openingBounds.left - rect.left - left}px ${openingBounds.top - rect.top - top}px`,
    };
    const end = {clipPath: 'inset(0 round 4px)', translate: '0px 0px'};
    return panel.animate(close ? [end, start] : [start, end], {
      duration: close ? 210 : 240,
      easing: 'cubic-bezier(.2,.7,.2,1)',
      fill: close ? 'forwards' : 'none',
    });
  }

  function revealChat(root) {
    let framesLeft = 4;
    function revealWhenVisible() {
      if (!chatIsOpen() || closing) return;
      const panel = root.querySelector('.chat-window.popup.visible');
      if (!panel || getComputedStyle(panel).visibility !== 'visible'
          || !panel.offsetWidth || !panel.offsetHeight) {
        if (--framesLeft) requestAnimationFrame(revealWhenVisible);
        return;
      }
      animateChat(panel);
      focusOpenChat(root);
    }
    requestAnimationFrame(revealWhenVisible);
  }

  function bindChatClose(root) {
    root.addEventListener('click', event => {
      const close = event.target.closest('.close-btn');
      if (!close || close.dataset.vlicoClosing || !chatIsOpen()) return;
      if (closing) {
        event.stopImmediatePropagation();
        return;
      }
      const animation = animateChat(close.closest('.chat-window'), true);
      if (!animation) return;
      event.stopImmediatePropagation();
      closing = true;
      const finish = () => {
        closing = false;
        animation.cancel();
        // Let Eva handle the replayed click without running the transition again.
        close.dataset.vlicoClosing = 'true';
        close.click();
        delete close.dataset.vlicoClosing;
      };
      animation.finished.then(finish, finish);
    }, true);
  }

  function prepareHost(host) {
    const root = host?.shadowRoot;
    if (!root || hosts.has(host)) return;
    hosts.add(host);
    const sheet = document.createElement('style');
    sheet.textContent = styles;
    root.append(sheet);
    bindChatClose(root);
    new MutationObserver(() => prepareChatCopy(root)).observe(root, {childList: true, subtree: true});
    prepareChatCopy(root);

    if (host.id === mobileHostId) {
      mobileHost = host;
      // The vendor adds the mobile window after creating its host.
      if (labelChat(root)) revealChat(root);
      else {
        const init = new MutationObserver(() => {
          if (!labelChat(root)) return;
          init.disconnect();
          revealChat(root);
        });
        init.observe(root, { childList: true, subtree: true });
      }
      return;
    }

    launcherHost = host;
    positionLauncher();
    // Eva currently opens the launcher on pointer release, so bridge native
    // keyboard and assistive-technology clicks to that same vendor action.
    root.addEventListener('pointerdown', event => {
      if (event.target.closest('.chat-bar')) openingBounds = launcher.getBoundingClientRect();
    }, true);
    root.addEventListener('click', event => {
      const launcher = event.target.closest('.chat-bar');
      if (!launcher || event.detail !== 0) return;
      openingBounds = launcher.getBoundingClientRect();
      for (const type of ['pointerdown', 'pointerup']) {
        launcher.dispatchEvent(new PointerEvent(type, { bubbles: true, composed: true, button: 0 }));
      }
    });
    let wasOpen = false;
    function updateLauncher() {
      widget = root.querySelector('#chat-widget');
      launcher = widget?.querySelector('.chat-bar');
      if (fallback) {
        const nativeReady = launcher && getComputedStyle(launcher).visibility === 'visible'
          && launcher.getClientRects().length > 0;
        const transferFocus = nativeReady && document.activeElement === fallback;
        fallback.hidden = Boolean(nativeReady || chatIsOpen());
        if (transferFocus) launcher.focus({preventScroll: true});
      }
      if (!launcher) return;
      if (!launcher.querySelector('.vlico-chat-label')) {
        const label = document.createElement('span');
        label.className = 'vlico-chat-label';
        label.textContent = 'Открыть чат';
        label.setAttribute('aria-hidden', 'true');
        launcher.append(label);
      }
      launcher.setAttribute('aria-label', 'Открыть чат');
      const open = chatIsOpen();
      launcher.setAttribute('aria-expanded', String(open));
      labelChat(root);
      updateInvitation();
      if (open === wasOpen) return;
      wasOpen = open;
      if (open) {
        finishInvitation();
        revealChat(root);
      }
      else launcher.focus({ preventScroll: true });
    }
    new MutationObserver(updateLauncher).observe(root, {
      childList: true, subtree: true, attributes: true, attributeFilter: ['class'],
    });
    updateLauncher();
  }

  function connectHosts() {
    if (fallback && !document.getElementById(launcherHostId)) fallback.hidden = false;
    prepareHost(document.getElementById(launcherHostId));
    prepareHost(document.getElementById(mobileHostId));
  }

  if (invitationTemplate && !invitationFinished) {
    invitation = invitationTemplate.content.firstElementChild.cloneNode(true);
    document.body.append(invitation);
    invitation.querySelector('.vlico-chat-dismiss').addEventListener('click', () => {
      finishInvitation();
      (fallback?.hidden ? launcher : fallback)?.focus({preventScroll: true});
    });
    invitation.querySelector('.vlico-chat-start').addEventListener('click', event => {
      finishInvitation();
      if (!fallback?.hidden || !launcher) return;
      event.preventDefault();
      launcher.click();
    });
    window.setTimeout(() => {
      invitationReady = true;
      updateInvitation();
    }, 6000);
    const observer = new MutationObserver(() => {
      positionLauncher();
      updateInvitation();
    });
    observer.observe(document.body, {subtree: true, attributes: true, attributeFilter: ['open']});
    for (const element of [privacy, stickyAction]) {
      if (element) observer.observe(element, {attributes: true, attributeFilter: ['hidden']});
    }
    document.addEventListener('focusin', updateInvitation);
    document.addEventListener('focusout', () => requestAnimationFrame(updateInvitation));
    document.addEventListener('visibilitychange', updateInvitation);
    window.visualViewport?.addEventListener('resize', updateInvitation);
  }

  new MutationObserver(connectHosts).observe(document.body, { childList: true });
  connectHosts();
  positionLauncher();
  if (privacy) new ResizeObserver(positionLauncher).observe(privacy);
  window.addEventListener('resize', () => { positionLauncher(); updateInvitation(); });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    if (invitation && !invitation.hidden && invitation.contains(document.activeElement)) {
      event.preventDefault();
      finishInvitation();
      (fallback?.hidden ? launcher : fallback)?.focus({preventScroll: true});
      return;
    }
    if (!chatIsOpen()) return;
    const host = document.activeElement;
    if (host !== launcherHost && host !== mobileHost) return;
    const close = host?.shadowRoot?.querySelector('.close-btn');
    if (!close) return;
    event.preventDefault();
    close.click();
  }, true);
})();
