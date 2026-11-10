(() => {
  const editor = document.querySelector('[data-article-editor]');
  const source = document.querySelector('[data-article-source]');
  const writing = editor.querySelector('[data-article-writing]');
  const format = editor.querySelector('.article-format');
  const selection = window.getSelection();
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
    document.execCommand('insertText', false, event.clipboardData.getData('text/plain'));
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
