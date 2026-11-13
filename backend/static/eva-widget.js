(() => {
  // Eva renders the floating launcher and a separate shadow root for the mobile chat.
  const launcherHostId = 'chat-widget-container';
  const mobileHostId = 'eva-chat-widget-mobile-host';
  const hosts = new WeakSet();
  const privacy = document.querySelector('[data-privacy-panel]');
  const narrow = matchMedia('(max-width: 760px)');
  let launcherHost;
  let mobileHost;
  let widget;

  const styles = `
    #chat-widget.chat-widget--popup .chat-bar {
      inset: auto max(16px, env(safe-area-inset-right)) var(--vlico-chat-bottom, max(16px, env(safe-area-inset-bottom))) auto !important;
      width: 56px !important;
      height: 56px !important;
      padding: 0 !important;
      justify-content: flex-end;
      padding-inline-end: 16px !important;
      gap: 0;
      cursor: pointer;
      touch-action: manipulation;
      color: #fff;
      border-radius: 50%;
      transition: none;
      transform: none;
    }
    #chat-widget .chat-bar::before {
      background: #075f40;
      box-shadow: 0 3px 12px #19191a30;
      animation: none;
      transform: none;
    }
    @media (hover: hover) {
      #chat-widget .chat-bar:hover::before { background: #064f36; }
    }
    #chat-widget .chat-bar .text, #chat-widget .chat-bar__close { display: none; }
    #chat-widget .chat-bar .icon { width: 24px; height: 24px; flex: 0 0 24px; }
    #chat-widget .vlico-chat-label {
      position: absolute;
      inset-inline-end: 52px;
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
        width: 156px !important;
        transition: none;
      }
      #chat-widget .chat-bar:focus-visible .vlico-chat-label {
        opacity: 1;
        visibility: visible;
      }
      @media (hover: hover) and (pointer: fine) {
        #chat-widget.chat-widget--popup .chat-bar:hover {
          width: 156px !important;
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
    #chat-widget .chat-bar:focus-visible, .chat-title .close-btn:focus-visible {
      outline: 2px solid #fff;
      outline-offset: -4px;
    }
    @media (prefers-reduced-motion: reduce) {
      #chat-widget.chat-widget--popup .chat-bar,
      #chat-widget .chat-bar .vlico-chat-label,
      #chat-widget.chat-widget--chat-open .chat-window.popup {
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
      const launcher = widget?.querySelector('.chat-bar');
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
      if (open) focusOpenChat(root);
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
    if (event.key !== 'Escape' || !chatIsOpen()) return;
    const host = document.activeElement;
    if (host !== launcherHost && host !== mobileHost) return;
    const close = host?.shadowRoot?.querySelector('.close-btn');
    if (!close) return;
    event.preventDefault();
    close.click();
  }, true);
})();
