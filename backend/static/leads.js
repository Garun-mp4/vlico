(() => {
  const ttl = 30 * 24 * 60 * 60 * 1000;
  let attribution = {};
  try {
    const stored = JSON.parse(localStorage.getItem('vlico-attribution') || 'null');
    if (stored && stored.expires > Date.now()) attribution = stored.data;
    else {
      const query = new URLSearchParams(location.search);
      for (const key of ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content']) {
        if (query.has(key)) attribution[key] = query.get(key).slice(0, 150);
      }
      attribution.landing_path = location.pathname;
      if (document.referrer) {
        const referrer = new URL(document.referrer);
        attribution.referrer = (referrer.origin + referrer.pathname).slice(0, 200);
      }
      localStorage.setItem('vlico-attribution', JSON.stringify({ data: attribution, expires: Date.now() + ttl }));
    }
  } catch { /* Server-side session attribution remains available when storage is blocked. */ }
  document.querySelectorAll('[data-lead-form]').forEach(form => {
    const errors = form.querySelector('[data-lead-errors]'), status = form.querySelector('[data-lead-status]');
    const submit = form.querySelector('button[type="submit"]:not([data-calculate])');
    const submitLabel = submit?.textContent;
    let busy = false;

    function clearFieldError(input) {
      if (!(input instanceof HTMLElement)) return;
      input.removeAttribute('aria-invalid');
      for (const line of form.querySelectorAll('[data-field-error]')) {
        if (line.dataset.fieldName !== input.name) continue;
        const describedBy = (input.getAttribute('aria-describedby') || '').split(/\s+/).filter(id => id && id !== line.id);
        if (describedBy.length) input.setAttribute('aria-describedby', describedBy.join(' '));
        else input.removeAttribute('aria-describedby');
        line.remove();
      }
      if (errors) {
        for (const line of errors.querySelectorAll('[data-error-field]')) {
          if (line.dataset.errorField === input.name) line.remove();
        }
        if (!errors.childElementCount) errors.hidden = true;
      }
    }

    function clearFieldErrors() {
      for (const line of form.querySelectorAll('[data-field-error]')) {
        const input = form.elements.namedItem(line.dataset.fieldName);
        if (input instanceof HTMLElement) clearFieldError(input);
        else line.remove();
      }
    }

    function showErrors(items) {
      errors.replaceChildren();
      clearFieldErrors();
      for (const [field, messages] of Object.entries(items)) {
        const input = form.elements.namedItem(field);
        if (input instanceof HTMLElement) {
          input.setAttribute('aria-invalid', 'true');
          const field = input.closest('.lead-field, .quick-calculator__field');
          if (field) {
            const message = document.createElement('p'); message.className = 'lead-errors'; message.dataset.fieldError = '';
            message.dataset.fieldName = input.name;
            message.id = input.id + '-server-error'; message.textContent = messages.join(' '); field.append(message);
            const describedBy = new Set((input.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean));
            describedBy.add(message.id); input.setAttribute('aria-describedby', [...describedBy].join(' '));
          }
        }
        for (const message of messages) {
          const line = document.createElement('p'); line.dataset.errorField = field; line.textContent = message; errors.append(line);
        }
      }
      errors.hidden = false;
      form.querySelector('[aria-invalid=true]')?.focus();
    }

    document.querySelectorAll('[data-interest]').forEach(link => link.addEventListener('click', () => { form.elements.namedItem('interest').value = link.dataset.interest || ''; }));
    for (const eventName of ['input', 'change']) form.addEventListener(eventName, event => clearFieldError(event.target));
    form.addEventListener('submit', async event => {
      const quoteSubmit = event.submitter?.hasAttribute('data-calculate') || (!event.submitter && form.querySelector('[data-quick-contact][hidden]'));
      if (quoteSubmit) return;
      event.preventDefault();
      if (busy) return;
      if (form.dataset.submitted === 'true') { status.focus(); return; }
      clearFieldErrors();
      errors.replaceChildren();
      const data = new FormData(form); data.set('source_page', form.elements.namedItem('source_page')?.value || location.pathname); data.set('attribution', JSON.stringify(attribution));
      busy = true; submit.disabled = true; submit.textContent = 'Отправляем заявку…'; form.setAttribute('aria-busy', 'true'); errors.hidden = true; status.hidden = false; status.dataset.state = 'sending'; status.textContent = 'Отправляем заявку…';
      const xhr = new XMLHttpRequest(); xhr.open('POST', form.dataset.api); xhr.setRequestHeader('Accept', 'application/json'); xhr.timeout = 90000;
      const finish = () => { busy = false; submit.disabled = false; form.removeAttribute('aria-busy'); submit.textContent = form.dataset.submitted === 'true' ? 'Заявка отправлена' : submitLabel; };
      xhr.onload = () => {
        let result; try { result = JSON.parse(xhr.responseText); } catch { result = {}; }
        if (xhr.status >= 200 && xhr.status < 300 && result.ok) {
          status.textContent = `${result.message}`; form.dataset.submitted = 'true';
          status.dataset.state = 'success';
          status.focus({ preventScroll: true });
          status.scrollIntoView({ block: 'nearest', behavior: 'instant' });
          document.dispatchEvent(new CustomEvent('vlico:lead-saved', { detail: { kind: result.kind, reference: result.reference } }));
        } else {
          status.hidden = true;
          showErrors(result.errors || { __all__: [xhr.status === 403 ? 'Страница с формой устарела. Сохраните введённое и обновите страницу.' : 'Не удалось отправить заявку. Данные остались в форме; попробуйте отправить снова.'] });
        }
        finish();
      };
      xhr.onerror = xhr.ontimeout = xhr.onabort = () => { status.hidden = true; showErrors({ __all__: ['Связь прервалась. Данные остались в форме. Повторная отправка не создаст вторую заявку.'] }); finish(); };
      xhr.send(data);
    });
  });
})();
