(() => {
  // Eva renders the floating launcher and a separate shadow root for the mobile chat.
  const launcherHostId = 'chat-widget-container';
  const mobileHostId = 'eva-chat-widget-mobile-host';
  const hosts = new WeakSet();
  const privacy = document.querySelector('[data-privacy-panel]');
  const stickyAction = document.querySelector('[data-home-sticky-cta]');
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
      --vlico-chat-size: 64px;
      --vlico-chat-gap: max(24px, calc(env(safe-area-inset-bottom, 0px) + 12px));
    }
    @media (max-width: 760px) {
      :host {
        --vlico-chat-size: 58px;
        --vlico-chat-gap: max(16px, calc(env(safe-area-inset-bottom, 0px) + 12px));
      }
    }
    #chat-widget.chat-widget--popup .chat-bar {
      inset: auto max(16px, env(safe-area-inset-right)) var(--vlico-chat-bottom, var(--vlico-chat-gap)) auto !important;
      width: var(--vlico-chat-size) !important;
      height: var(--vlico-chat-size) !important;
      padding: 0 !important;
      justify-content: flex-start;
      padding-inline-start: calc((var(--vlico-chat-size) - 26px) / 2) !important;
      gap: 0;
      cursor: pointer;
      touch-action: manipulation;
      color: #fff;
      border-radius: calc(var(--vlico-chat-size) / 2);
      transition: none;
      transform: none;
    }
    #chat-widget.chat-widget--popup .chat-bar::before {
      background: #07543b;
      border-radius: calc(var(--vlico-chat-size) / 2) !important;
      box-shadow: inset 0 0 0 1px #87c4a480, 0 5px 18px #19191a38;
      animation: none;
      transform: none;
    }
    @media (hover: hover) {
      #chat-widget.chat-widget--popup .chat-bar:hover::before { background: #064f36; }
    }
    #chat-widget .chat-bar .text, #chat-widget .chat-bar__close { display: none; }
    #chat-widget .chat-bar .icon { width: 26px; height: 26px; flex: 0 0 26px; }
    #chat-widget .vlico-chat-label {
      position: absolute;
      inset-inline-start: 57px;
      white-space: nowrap;
      font: 600 14px/1 system-ui, sans-serif;
      opacity: 0;
      visibility: hidden;
      pointer-events: none;
    }
    @media (min-width: 761px) {
      #chat-widget.chat-widget--popup .chat-bar {
        transition: width 200ms ease-in-out;
      }
      #chat-widget.chat-widget--popup .chat-bar:focus-visible {
        width: 164px !important;
        transition: none;
      }
      #chat-widget .chat-bar:focus-visible .vlico-chat-label {
        opacity: 1;
        visibility: visible;
      }
      @media (hover: hover) and (pointer: fine) {
        #chat-widget.chat-widget--popup .chat-bar:hover {
          width: 164px !important;
        }
        #chat-widget .chat-bar:hover .vlico-chat-label {
          visibility: visible;
          animation: vlico-chat-label-in 160ms ease-out both;
        }
      }
      #chat-widget.chat-widget--chat-open .chat-window.popup {
        animation: vlico-chat-open 220ms ease-out both;
      }
    }
    @keyframes vlico-chat-label-in {
      from { opacity: 0; transform: translateX(4px); }
      to { opacity: 1; transform: none; }
    }
    @keyframes vlico-chat-open {
      from { opacity: .65; clip-path: inset(88% 0 0 0 round 14px); }
      to { opacity: 1; clip-path: inset(0 round 14px); }
    }
    #chat-widget .chat-bar .badge { position: absolute; top: -3px; right: -3px; border-color: #075f40; }
    #chat-widget.chat-widget--chat-open .chat-bar { visibility: hidden; }
    #chat-widget:not(.chat-widget--chat-open) .chat-window.popup { visibility: hidden; }
    .chat-title .close-btn { width: 44px; height: 44px; }
    .chat-window .chat-title { background: #07543b; color: #f2f1e9; }
    .vlico-chat-invitation[hidden] { display: none !important; }
    .vlico-chat-invitation {
      position: fixed;
      z-index: 99999;
      box-sizing: border-box;
      right: max(16px, env(safe-area-inset-right));
      bottom: calc(var(--vlico-chat-bottom, var(--vlico-chat-gap)) + var(--vlico-chat-size) + 12px);
      width: min(316px, calc(100vw - 36px));
      padding: 18px 18px 12px;
      border: 1px solid #d5d3c8;
      border-top: 2px solid #07543b;
      border-radius: 10px;
      background: #f2f1e9;
      color: #19191a;
      box-shadow: 0 8px 26px #19191a26;
      font: 500 14px/1.48 Manrope, system-ui, sans-serif;
      transform-origin: bottom right;
      animation: vlico-invitation-in 220ms ease-out both;
    }
    .vlico-chat-invitation p { margin: 0 0 8px; }
    .vlico-chat-invitation .vlico-chat-heading { padding-right: 40px; font-size: 17px; font-weight: 700; }
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
      color: #07543b;
      text-align: left;
      font-weight: 750;
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
      #chat-widget .chat-bar .vlico-chat-label,
      #chat-widget.chat-widget--chat-open .chat-window.popup,
      .vlico-chat-invitation {
        transition: none !important;
        animation: none !important;
      }
      #chat-widget .chat-bar:hover .vlico-chat-label { opacity: 1; }
    }
  `;

  function positionLauncher() {
    if (!launcherHost) return;
    if (privacy && !privacy.hidden && narrow.matches) {
      const bottom = window.innerHeight - privacy.getBoundingClientRect().top + 12;
      launcherHost.style.setProperty('--vlico-chat-bottom', `${bottom}px`);
    } else {
      launcherHost.style.removeProperty('--vlico-chat-bottom');
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
      }, 6500);
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
    prepareHost(document.getElementById(launcherHostId));
    prepareHost(document.getElementById(mobileHostId));
  }

  new MutationObserver(connectHosts).observe(document.body, { childList: true });
  connectHosts();
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
