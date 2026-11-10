(() => {
  document.querySelectorAll('[data-quick-calculator]').forEach(form => {
    const quickFields = form.querySelector('[data-quick-fields]');
    const quoteButton = form.querySelector('[data-calculate]');
    const result = form.querySelector('[data-quick-result]');
    const contact = form.querySelector('[data-quick-contact]');
    const title = form.querySelector('[data-quick-result-title]');
    if (!quickFields || !quoteButton || !result || !contact) return;

    if (!result.hidden) quoteButton.hidden = true;

    function revealContact() {
      result.hidden = false;
      contact.hidden = false;
      contact.disabled = false;
      quoteButton.hidden = true;
      title?.focus({ preventScroll: true });
      title?.scrollIntoView({ block: 'nearest' });
    }

    function resetResult() {
      if (result.hidden && contact.hidden) return;
      result.hidden = true;
      contact.hidden = true;
      contact.disabled = true;
      quoteButton.hidden = false;
    }

    form.addEventListener('submit', event => {
      const isQuote = event.submitter?.matches('[data-calculate]') || (!event.submitter && contact.hidden);
      if (!isQuote) return;
      event.preventDefault();
      if (form.reportValidity()) revealContact();
    });

    quickFields.addEventListener('input', resetResult);
    quickFields.addEventListener('change', resetResult);
  });
})();
