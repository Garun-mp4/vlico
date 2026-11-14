(() => {
  // Eva renders the floating launcher and a separate shadow root for the mobile chat.
  const launcherHostId = 'chat-widget-container';
  const mobileHostId = 'eva-chat-widget-mobile-host';
  const hosts = new WeakSet();
  const privacy = document.querySelector('[data-privacy-panel]');
  const stickyAction = document.querySelector('[data-home-sticky-cta]');
  const fallback = document.querySelector('[data-vlico-chat-fallback]');
  const invitationTemplate = document.getElementById('vlico-chat-invitation');
  const invitationKey = 'vlico-chat-invitation-seen';
  const narrow = matchMedia('(max-width: 760px)');
  let launcherHost;
  let mobileHost;
  let widget;
  let invitation;
  let launcher;
  let invitationReady = false;
  let invitationShown = false;
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
      color: var(--vlico-chat-ink);
      border-radius: 4px;
      overflow: hidden;
      transition: none;
      transform: none;
    }
    #chat-widget.chat-widget--popup .chat-bar::before {
      background: var(--vlico-chat-green);
      border-radius: 4px !important;
      box-shadow: inset 0 0 0 1px var(--vlico-chat-focus), 0 3px 10px #19191a24;
      animation: none;
      transform: none;
    }
    #chat-widget .chat-bar .text, #chat-widget .chat-bar__close { display: none; }
    #chat-widget.chat-widget--popup .chat-bar::after {
      content: "";
      position: absolute;
      inset: 5px auto 5px 5px;
      width: 46px;
      box-sizing: border-box;
      border: 1px solid var(--vlico-chat-focus);
      border-radius: 3px;
      pointer-events: none;
      opacity: 0;
      animation: vlico-chat-attention 650ms var(--vlico-chat-ease) 2s;
    }
    @keyframes vlico-chat-attention {
      0% { opacity: .75; transform: scale(.74); }
      100% { opacity: 0; transform: scale(1.14); }
    }
    #chat-widget.chat-widget--popup .chat-bar:is(:hover, :focus-visible)::after { visibility: hidden; }
    #chat-widget .chat-bar .icon { width: 26px; height: 26px; flex: 0 0 26px; }
    #chat-widget .vlico-chat-label {
      position: absolute;
      inset-inline-start: 50px;
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
        #chat-widget .vlico-chat-label { transition: opacity 170ms ease-out; }
        #chat-widget.chat-widget--popup .chat-bar:hover {
          width: 164px !important;
        }
        #chat-widget .chat-bar:hover .vlico-chat-label {
          opacity: 1;
        }
      }
      #chat-widget.chat-widget--chat-open .chat-window.popup {
        animation: vlico-chat-open 160ms var(--vlico-chat-ease);
      }
    }
    @keyframes vlico-chat-open {
      from { opacity: .7; transform: translateY(6px); }
      to { opacity: 1; transform: none; }
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
      transition: none;
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
    .chat-window .message.bot .message-bubble {
      background: var(--vlico-chat-sand);
      color: var(--vlico-chat-ink);
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
    .vlico-chat-invitation[hidden] { display: none !important; }
    .vlico-chat-invitation {
      position: fixed;
      z-index: 99999;
      pointer-events: auto;
      box-sizing: border-box;
      right: max(16px, env(safe-area-inset-right));
      bottom: calc(var(--vlico-chat-bottom, var(--vlico-chat-gap)) + var(--vlico-chat-size) + 12px);
      width: min(316px, calc(100vw - 36px));
      padding: 18px 18px 12px;
      border: 1px solid #d5d3c8;
      border-top: 2px solid var(--vlico-chat-green);
      border-radius: 4px;
      background: var(--vlico-chat-paper);
      color: var(--vlico-chat-ink);
      font: 400 13px/1.55 var(--vlico-chat-mono);
      transform-origin: bottom right;
      animation: vlico-invitation-in 170ms var(--vlico-chat-ease) both;
    }
    .vlico-chat-invitation p { margin: 0 0 8px; }
    .vlico-chat-invitation .vlico-chat-heading { padding-right: 40px; font: 700 19px/1.2 var(--vlico-chat-title); }
    .vlico-chat-start, .vlico-chat-dismiss {
      cursor: pointer;
      min-height: 44px;
      border: 0;
      background: transparent;
      font: inherit;
    }
    .vlico-chat-start {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      padding: 0;
      border-top: 1px solid #d5d3c8;
      color: var(--vlico-chat-focus);
      text-align: left;
      text-decoration: underline;
      text-underline-offset: 4px;
      font-weight: 500;
    }
    .vlico-chat-dismiss {
      position: absolute;
      top: 4px;
      right: 4px;
      width: 44px;
      color: #4d4c47;
      font: 400 24px/1 system-ui, sans-serif;
    }
    .vlico-chat-invitation button:focus-visible { outline: 2px solid #07543b; outline-offset: 2px; }
    @keyframes vlico-invitation-in {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: none; }
    }
    @media (max-height: 440px) { .vlico-chat-invitation { display: none; } }
    #chat-widget .chat-bar:focus-visible, .chat-title .close-btn:focus-visible {
      outline: 2px solid #fff;
      outline-offset: -4px;
    }
    @media (prefers-reduced-motion: reduce) {
      #chat-widget.chat-widget--popup .chat-bar,
      #chat-widget.chat-widget--popup .chat-bar::after,
      #chat-widget .chat-bar .vlico-chat-label,
      #chat-widget.chat-widget--chat-open .chat-window.popup,
      .chat-window.popup .chat-footer button,
      .vlico-chat-invitation {
        transition: none !important;
        animation: none !important;
      }
      #chat-widget .chat-bar:hover .vlico-chat-label { opacity: 1; }
    }
  `;

  function positionLauncher() {
    const targets = [launcherHost, fallback];
    if (privacy && !privacy.hidden && narrow.matches) {
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
    const busy = privacy && !privacy.hidden || stickyAction && !stickyAction.hidden
      || document.querySelector('dialog[open], [data-header-mobile][open]');
    if (field || keyboard || busy || document.hidden || window.innerHeight <= 440) {
      if (invitationShown) finishInvitation();
      return;
    }
    if (!invitationShown && launcher?.getClientRects().length && !chatIsOpen()) {
      invitation.hidden = false;
      invitationShown = true;
      rememberInvitation();
    }
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

  function prepareHost(host) {
    const root = host?.shadowRoot;
    if (!root || hosts.has(host)) return;
    hosts.add(host);
    const sheet = document.createElement('style');
    sheet.textContent = styles;
    root.append(sheet);
    new MutationObserver(() => prepareChatCopy(root)).observe(root, {childList: true, subtree: true});
    prepareChatCopy(root);

    if (host.id === mobileHostId) {
      mobileHost = host;
      // The vendor adds the mobile window after creating its host.
      if (labelChat(root)) focusOpenChat(root);
      else {
        const init = new MutationObserver(() => {
          if (!labelChat(root)) return;
          init.disconnect();
          focusOpenChat(root);
        });
        init.observe(root, { childList: true, subtree: true });
      }
      return;
    }

    launcherHost = host;
    positionLauncher();
    if (invitationTemplate && !invitationFinished) {
      invitation = invitationTemplate.content.firstElementChild.cloneNode(true);
      root.append(invitation);
      invitation.querySelector('.vlico-chat-dismiss').addEventListener('click', () => {
        finishInvitation();
        launcher?.focus({preventScroll: true});
      });
      invitation.querySelector('.vlico-chat-start').addEventListener('click', () => launcher?.click());
      window.setTimeout(() => {
        invitationReady = true;
        updateInvitation();
      }, 6000);
      const observer = new MutationObserver(updateInvitation);
      observer.observe(document.body, {subtree: true, attributes: true, attributeFilter: ['open']});
      for (const element of [privacy, stickyAction]) {
        if (element) observer.observe(element, {attributes: true, attributeFilter: ['hidden']});
      }
      document.addEventListener('focusin', updateInvitation);
      document.addEventListener('focusout', () => requestAnimationFrame(updateInvitation));
      document.addEventListener('visibilitychange', updateInvitation);
      window.addEventListener('resize', updateInvitation);
      window.visualViewport?.addEventListener('resize', updateInvitation);
    }
    // Eva currently opens the launcher on pointer release, so bridge native
    // keyboard and assistive-technology clicks to that same vendor action.
    root.addEventListener('click', event => {
      const launcher = event.target.closest('.chat-bar');
      if (!launcher || event.detail !== 0) return;
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
      if (open === wasOpen) return;
      wasOpen = open;
      if (open) {
        finishInvitation();
        focusOpenChat(root);
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

  new MutationObserver(connectHosts).observe(document.body, { childList: true });
  connectHosts();
  positionLauncher();
  if (privacy) new ResizeObserver(positionLauncher).observe(privacy);
  narrow.addEventListener('change', positionLauncher);
  window.addEventListener('resize', positionLauncher);
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    if (invitation && !invitation.hidden && invitation.contains(launcherHost?.shadowRoot?.activeElement)) {
      event.preventDefault();
      finishInvitation();
      launcher?.focus({preventScroll: true});
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
