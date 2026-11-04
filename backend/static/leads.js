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
    const progress = form.querySelector('[data-upload-progress]');
    const submit = form.querySelector('button[type="submit"]:not([data-calculate])');
    const files = form.querySelector('[name=attachments]');
    let busy = false;

    function showErrors(items) {
      errors.replaceChildren();
      form.querySelectorAll('[data-field-error]').forEach(line => line.remove());
      for (const [field, messages] of Object.entries(items)) {
        const input = form.elements.namedItem(field);
        if (input instanceof HTMLElement) {
          input.setAttribute('aria-invalid', 'true');
          const field = input.closest('.lead-field');
          if (field) {
            const message = document.createElement('p'); message.className = 'lead-errors'; message.dataset.fieldError = '';
            message.id = input.id + '-server-error'; message.textContent = messages.join(' '); field.append(message);
            input.setAttribute('aria-describedby', message.id);
          }
        }
        for (const message of messages) {
          const line = document.createElement('p'); line.textContent = message; errors.append(line);
        }
      }
      errors.hidden = false;
      form.querySelector('[aria-invalid=true]')?.focus();
    }

    files?.addEventListener('change', () => { form.querySelector('[data-selected-files]').textContent = [...files.files].map(file => file.name).join(', '); });
    const setFileRequired = () => { if (files) files.required = form.elements.namedItem('kind').value === 'project'; };
    form.querySelector('[name=kind]')?.addEventListener('change', setFileRequired); setFileRequired();
    document.querySelectorAll('[data-interest]').forEach(link => link.addEventListener('click', () => { form.elements.namedItem('interest').value = link.dataset.interest || ''; }));
    form.addEventListener('input', event => { event.target.removeAttribute('aria-invalid'); });
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (busy || form.dataset.submitted === 'true') return;
      const selected = [...(files?.files || [])];
      if (selected.length > 3 || selected.some(file => file.size > 8 * 1024 * 1024)) { showErrors({ attachments: ['Можно выбрать до 3 файлов, каждый не больше 8 МБ.'] }); return; }
      const data = new FormData(form); data.set('source_page', location.pathname); data.set('attribution', JSON.stringify(attribution));
      busy = true; submit.disabled = true; errors.hidden = true; status.hidden = false; status.textContent = 'Сохраняем заявку…'; progress.hidden = !selected.length;
      const xhr = new XMLHttpRequest(); xhr.open('POST', form.dataset.api); xhr.setRequestHeader('Accept', 'application/json'); xhr.timeout = 90000;
      xhr.upload.onprogress = event => { if (event.lengthComputable) progress.value = Math.round(event.loaded / event.total * 100); };
      const finish = () => { busy = false; progress.hidden = true; if (form.dataset.submitted !== 'true') submit.disabled = false; };
      xhr.onload = () => {
        let result; try { result = JSON.parse(xhr.responseText); } catch { result = {}; }
        if (xhr.status >= 200 && xhr.status < 300 && result.ok) {
          status.textContent = `${result.message} Номер: ${result.reference}`; form.dataset.submitted = 'true';
          form.querySelectorAll('input,select,textarea,button').forEach(input => { input.disabled = true; });
          document.dispatchEvent(new CustomEvent('vlico:lead-saved', { detail: { kind: result.kind } }));
        } else {
          status.hidden = true;
          showErrors(result.errors || { __all__: [xhr.status === 403 ? 'Сессия формы устарела. Сохраните введённое и обновите страницу.' : 'Сервис временно недоступен. Данные остались в форме; попробуйте отправить снова.'] });
        }
        finish();
      };
      xhr.onerror = xhr.ontimeout = xhr.onabort = () => { status.hidden = true; showErrors({ __all__: ['Связь прервалась. Данные остались в форме. Повторная отправка не создаст вторую заявку.'] }); finish(); };
      xhr.send(data);
    });
  });
})();
