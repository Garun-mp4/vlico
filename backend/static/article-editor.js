(() => {
  const editor = document.querySelector('[data-article-editor]');
  const source = document.querySelector('[data-article-source]');
  const writing = editor.querySelector('[data-article-writing]');
  const format = editor.querySelector('.article-format');
  const selection = window.getSelection();
  const markdown = window.markdownit?.({html: false, breaks: true});
  const allowedTags = new Set('P BR DIV H1 H2 H3 H4 H5 H6 STRONG B EM I S DEL CODE PRE UL OL LI BLOCKQUOTE A HR DETAILS SUMMARY TABLE THEAD TBODY TR TH TD'.split(' '));
  const discardTags = new Set(['SCRIPT', 'STYLE', 'TEMPLATE', 'IFRAME', 'OBJECT']);
  const formatted = 'h2,h3,h4,h5,h6,strong,b,em,i,s,del,code,pre,ul,ol,blockquote,a,hr,table,details';
  if (markdown) markdown.renderer.rules.image = (tokens, index) => markdown.utils.escapeHtml(tokens[index].content);

  function safeClipboard(html) {
    const fragment = document.createElement('template');
    fragment.innerHTML = html;
    for (const node of fragment.content.querySelectorAll('*')) {
      if (!fragment.content.contains(node)) continue;
      if (node.namespaceURI !== 'http://www.w3.org/1999/xhtml' || discardTags.has(node.tagName)) {
        node.remove();
        continue;
      }
      if (!allowedTags.has(node.tagName)) {
        node.replaceWith(...node.childNodes);
        continue;
      }
      const href = node.tagName === 'A' ? node.getAttribute('href') : null;
      const start = node.tagName === 'OL' ? node.getAttribute('start') : null;
      for (const attribute of [...node.attributes]) node.removeAttribute(attribute.name);
      if (href && href === href.trim() && !/[\x00-\x1f\\]/.test(href)) {
        const url = URL.canParse?.(href) ? new URL(href) : null;
        if (/^(?:#|\/(?!\/))/.test(href) || (url?.hostname && ['http:', 'https:'].includes(url.protocol))) {
          node.setAttribute('href', href);
        }
      }
      if (start && /^-?\d{1,9}$/.test(start)) node.setAttribute('start', start);
      if (node.tagName === 'H1') {
        const heading = document.createElement('h2');
        heading.append(...node.childNodes);
        node.replaceWith(heading);
      }
    }
    return fragment;
  }
  let lastSelection;
  document.addEventListener('selectionchange', () => {
    if (selection.rangeCount && writing.contains(selection.getRangeAt(0).commonAncestorContainer)) {
      lastSelection = selection.getRangeAt(0).cloneRange();
    }
  });

  function syncArticle() {
    source.value = writing.innerHTML;
    source.dispatchEvent(new Event('input', {bubbles: true}));
  }

  source.hidden = true;
  editor.hidden = false;
  document.querySelector('#article-body-label').addEventListener('click', event => {
    event.preventDefault();
    writing.focus();
  });
  writing.addEventListener('input', syncArticle);
  writing.addEventListener('paste', event => {
    event.preventDefault();
    const plain = event.clipboardData.getData('text/plain');
    const rich = event.clipboardData.getData('text/html');
    const rendered = markdown && plain.length <= 180000 ? safeClipboard(markdown.render(plain)) : null;
    let content = rendered?.content.querySelector(formatted) ? rendered : null;
    const clipboard = !content && rich && rich.length <= 720000 ? safeClipboard(rich) : null;
    if (clipboard?.content.querySelector(formatted)) content = clipboard;
    if (content) document.execCommand('insertHTML', false, content.innerHTML);
    else document.execCommand('insertText', false, plain || clipboard?.content.textContent || '');
    syncArticle();
  });
  writing.addEventListener('drop', event => event.preventDefault());
  format.addEventListener('mousedown', event => {
    if (event.target.closest('[data-format]')) event.preventDefault();
  });
  format.addEventListener('click', event => {
    const button = event.target.closest('[data-format]');
    if (!button) return;
    writing.focus();
    if (lastSelection && writing.contains(lastSelection.commonAncestorContainer)) {
      selection.removeAllRanges();
      selection.addRange(lastSelection);
    }
    let value = button.dataset.value;
    if (button.dataset.format === 'createLink') {
      if (window.getSelection().isCollapsed) return;
      value = window.prompt('Введите адрес ссылки (https://)', 'https://')?.trim();
      if (!value || !/^https?:\/\/[^\s]+$/i.test(value)) return;
    }
    document.execCommand(button.dataset.format, false, value);
    syncArticle();
  });
})();
