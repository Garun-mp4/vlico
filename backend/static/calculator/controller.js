import { STORAGE_KEY, initial, restore, visible, change, validate } from './model.js';
import { el, fieldView, diagram, media, summaryView, quoteView } from './view.js';

document.querySelectorAll('[data-configurator]').forEach(form => {
  const schema = JSON.parse(document.getElementById('config-schema').textContent);
  const bootstrap = JSON.parse(document.getElementById('config-bootstrap').textContent);
  const find = name => form.querySelector(`[data-config-${name}]`);
  const shell = find('shell'), panel = find('question'), visual = find('visual'), result = find('result'), contact = find('contact-form');
  const next = find('next'), back = find('back'), error = find('error'), status = find('status'), submitErrors = find('submit-errors');
  const fallback = find('fallback'), fields = schema.fields;
  let answers = restore(schema), step = 0, quote = null, busy = false;
  let lightPreview = null;
  const lightTypes = ['spots', 'light_lines', 'tracks', 'chandeliers', 'led'];
  const imageDialog = el('dialog', 'config-preview-dialog');
  const dialogHeading = el('h3'); dialogHeading.id = 'config-preview-dialog-title';
  imageDialog.setAttribute('aria-labelledby', dialogHeading.id);
  const closePreview = el('button', 'config-back', 'Закрыть ×'); closePreview.type = 'button';
  closePreview.addEventListener('click', () => imageDialog.close());
  const dialogHeader = el('div', 'config-preview-dialog-header'); dialogHeader.append(dialogHeading, closePreview);
  const dialogImage = el('div');
  imageDialog.append(dialogHeader, dialogImage, el('p', 'lead-help', 'Визуализация решения, созданная с помощью ИИ. Фактуру и конструкцию подберём после замера.'));
  form.append(imageDialog);
  function previewSurface() { return ['pvc', 'pvc_satin', 'pvc_gloss', 'fabric'].includes(answers.material) ? answers.material : 'pvc'; }
  function previewChoice() {
    if (step === 2) return { field: 'material', value: previewSurface() };
    if (step === 3 && answers.edge !== 'unknown') return { field: 'edge', value: answers.edge || 'standard' };
    if (step === 5 && answers.cornice !== 'unknown') return { field: 'cornice', value: answers.cornice || 'standard' };
    if (step === 4) {
      const value = answers.lights.includes(lightPreview) ? lightPreview : answers.lights.find(code => lightTypes.includes(code)) || (answers.lights.length ? null : 'spots');
      if (value) return { field: 'lights', value };
    }
    return null;
  }
  function openSolutionPreview() {
    const choice = previewChoice();
    if (!choice) return;
    dialogHeading.textContent = fields[choice.field].choices.find(([code]) => code === choice.value)[1];
    const img = media(`${choice.field}:${choice.value}`, form.dataset.assets, answers); img.sizes = '90vw'; img.loading = 'eager'; dialogImage.replaceChildren(img);
    imageDialog.showModal();
  }
  // Bound server answers take precedence over the optional session draft.
  if (bootstrap.bound) {
    const data = new FormData(form);
    for (const [name, spec] of Object.entries(fields)) answers[name] = spec.kind === 'multi' ? data.getAll(name) : data.get(name) ?? '';
  }
  fallback.hidden = true; fallback.querySelectorAll('input, select, button').forEach(input => { input.disabled = true; });
  function showContact(open) {
    contact.hidden = !open;
    contact.querySelectorAll('input,select,textarea,button').forEach(input => { input.disabled = !open; });
  }
  showContact(false); shell.hidden = false; result.hidden = true;
  const save = () => { try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(answers)); } catch { /* No persistence needed for navigation. */ } };
  function focusHeading() { panel.querySelector('h3')?.focus({ preventScroll: true }); shell.scrollIntoView({ block: 'start', behavior: 'instant' }); }
  function updateVisual() {
    visual.replaceChildren(el('p', 'eyebrow', 'VLICO / ВАШЕ РЕШЕНИЕ'));
    if (step === 1) {
      visual.append(diagram(answers.shape, 'Схема выбранной формы помещения', answers));
      visual.append(el('p', 'lead-help', answers.size_mode === 'dimensions' && answers.shape === 'rectangle' ? 'Площадь = длина × ширина. Периметр = 2 × (длина + ширина).' : 'Из площади нельзя вывести точный периметр. Непрямоугольную геометрию уточним на замере.'));
    } else {
      const choice = previewChoice();
      const key = choice ? `${choice.field}:${choice.value}` : { 4: `lights:${answers.lights.find(v => !['none', 'unknown'].includes(v))}`, 5: `cornice:${answers.cornice}` }[step];
      const m = key && media(key, form.dataset.assets, answers);
      if (choice) visual.append(el('p', 'config-preview-name', `Предпросмотр: ${fields[choice.field].choices.find(([code]) => code === choice.value)[1]}`));
      if (m) { visual.append(m); visual.append(el('p', 'lead-help', 'Иллюстрация решения · создано с помощью ИИ')); }
      if (choice && m) { const zoom = el('button', 'config-back config-preview-zoom', 'Рассмотреть крупнее ↗'); zoom.type = 'button'; zoom.addEventListener('click', openSolutionPreview); visual.append(zoom); }
      if (step === 4 && choice) {
        visual.append(el('p', 'lead-help', 'В предпросмотре один вид освещения. Выбранные решения можно сочетать; общую схему разработаем отдельно.'));
        const selected = answers.lights.filter(code => lightTypes.includes(code));
        if (selected.length > 1) {
          const choices = el('div', 'config-light-preview-choices'); choices.setAttribute('role', 'group'); choices.setAttribute('aria-label', 'Рассмотреть выбранное освещение');
          for (const code of selected) {
            const button = el('button', '', fields.lights.choices.find(([value]) => value === code)[1]); button.type = 'button'; button.dataset.lightPreview = code; button.setAttribute('aria-pressed', String(choice.value === code));
            button.addEventListener('click', () => { lightPreview = code; updateVisual(); visual.querySelector(`[data-light-preview="${code}"]`)?.focus({ preventScroll: true }); });
            choices.append(button);
          }
          visual.append(choices);
        }
      }
      if (step === 3 && answers.edge === 'unknown') visual.append(el('p', 'config-visual-title', 'Подберём примыкание вместе.'), el('p', 'lead-help', 'Покажем образцы профилей и предложим решение под ваш интерьер.'));
      if (step === 5 && answers.cornice === 'unknown') visual.append(el('p', 'config-visual-title', 'Подберём оформление штор.'), el('p', 'lead-help', 'Обсудим внешний вид, крепление и размеры окна на замере.'));
      if (step === 0 && !answers.room) { visual.append(el('p', 'config-visual-title', 'Начнём с вашей комнаты.'), el('p', 'lead-help', 'Сначала пространство, затем детали. Контакты понадобятся только если вы захотите обсудить результат.')); }
      else visual.append(summaryView(answers, schema));
    }
    visual.append(el('p', 'config-visual-note', 'Один потолок · предварительный расчёт'));
  }
  function render(focus = false) {
    result.hidden = true; showContact(false); shell.hidden = false; error.hidden = true;
    const current = schema.steps[step]; panel.replaceChildren();
    const h = el('h3', '', current.title); h.tabIndex = -1; panel.append(h, el('p', 'config-step-help', current.help));
    for (const name of current.fields.filter(name => visible(name, answers))) panel.append(fieldView(name, fields[name], answers, form.dataset.assets));
    if (fields[current.fields[0]].label === current.title) panel.querySelector('legend').classList.add('config-sr');
    find('step').textContent = `${String(step + 1).padStart(2, '0')} / 08 · ${current.name}`;
    form.querySelector('.config-progress').value = step + 1;
    back.hidden = step === 0; next.textContent = step === 7 ? 'Рассчитать стоимость →' : 'Продолжить →';
    updateVisual(); if (focus) focusHeading();
  }
  function fieldErrors(errors) {
    panel.querySelectorAll('.config-field-error').forEach(n => n.remove());
    panel.querySelectorAll('[aria-invalid]').forEach(input => { input.removeAttribute('aria-invalid'); input.removeAttribute('aria-describedby'); });
    for (const [name, message] of Object.entries(errors)) {
      const group = panel.querySelector(`[data-field="${name}"]`); if (!group) continue;
      const p = el('p', 'config-error config-field-error', Array.isArray(message) ? message.join(' ') : message); p.id = `config-error-${name}`; group.append(p);
      group.querySelectorAll('input').forEach(input => { input.setAttribute('aria-invalid', 'true'); input.setAttribute('aria-describedby', p.id); });
    }
    panel.querySelector('[aria-invalid=true]')?.focus();
  }
  function payload() {
    const data = new FormData(form);
    // UI only contains the current step; send the normalized draft explicitly.
    for (const name of Object.keys(fields)) {
      data.delete(name);
      if (name === 'schema') { data.set(name, 'v2'); continue; }
      if (!visible(name, answers)) continue;
      const value = answers[name];
      if (Array.isArray(value)) value.forEach(v => data.append(name, v));
      else if (value !== undefined) data.set(name, value);
    }
    data.set('source_page', location.pathname);
    try { data.set('attribution', JSON.stringify(JSON.parse(localStorage.getItem('vlico-attribution'))?.data || {})); } catch { /* Server session attribution remains. */ }
    return data;
  }
  function showQuote(q) {
    quote = q; form.elements.namedItem('pricing_version').value = q.version;
    find('quote').replaceChildren(quoteView(q)); shell.hidden = true; result.hidden = false; showContact(false); result.focus(); result.scrollIntoView({ block: 'start', behavior: 'instant' });
  }
  function setBusy(value) {
    busy = value;
    shell.querySelectorAll('input, button').forEach(input => { input.disabled = value; });
    find('submit').disabled = value;
    form.setAttribute('aria-busy', String(value));
  }
  async function estimate() {
    if (busy) return;
    setBusy(true); error.hidden = true; next.textContent = 'Считаем…';
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(form.dataset.estimateApi, { method: 'POST', body: payload(), signal: controller.signal, headers: { Accept: 'application/json' } });
      const body = await response.json();
      if (!response.ok) {
        const key = Object.keys(body.errors || {})[0], target = schema.steps.findIndex(s => s.fields.includes(key));
        if (target >= 0) { step = target; render(true); fieldErrors(body.errors); }
        else throw new Error('response');
        return;
      }
      showQuote(body.quote);
    } catch { error.textContent = 'Не удалось получить расчёт. Проверьте соединение и попробуйте снова. Ответы сохранены.'; error.hidden = false; }
    finally { clearTimeout(timer); setBusy(false); next.textContent = step === 7 ? 'Рассчитать стоимость →' : 'Продолжить →'; }
  }
  panel.addEventListener('change', event => {
    const input = event.target; if (!input.name || busy || !['radio', 'checkbox'].includes(input.type)) return;
    answers = change(answers, input.name, input.value, fields[input.name].kind === 'multi'); quote = null; save();
    if (input.name === 'lights' && lightTypes.includes(input.value) && input.checked) lightPreview = input.value;
    const name = input.name, value = input.value; render();
    [...panel.querySelectorAll('input')].find(i => i.name === name && i.value === value)?.focus({ preventScroll: true });
  });
  panel.addEventListener('input', event => {
    const input = event.target; if (['radio', 'checkbox'].includes(input.type) || !input.name || busy) return;
    answers = change(answers, input.name, input.value); quote = null; input.removeAttribute('aria-invalid'); save(); updateVisual();
  });
  next.addEventListener('click', () => { if (busy) return; const errors = validate(answers, schema.steps[step], fields); if (Object.keys(errors).length) { fieldErrors(errors); return; } if (step === 7) estimate(); else { step++; render(true); } });
  back.addEventListener('click', () => { if (!busy && step > 0) { step--; render(true); } });
  find('reset').addEventListener('click', () => { if (busy) return; answers = initial(); lightPreview = null; quote = null; step = 0; save(); render(true); });
  find('edit').addEventListener('click', () => { if (!busy) { step = 0; quote = null; render(true); } });
  find('contact').addEventListener('click', () => { if (!quote || busy) return; showContact(true); contact.querySelector('input[name=name]')?.focus(); contact.scrollIntoView({ block: 'start', behavior: 'instant' }); });
  form.querySelector('[name=attachments]').addEventListener('change', event => { form.querySelector('[data-selected-files]').textContent = [...event.target.files].map(file => file.name).join(', '); });
  const contactDescriptions = new Map([...contact.querySelectorAll('[aria-describedby]')].map(input => [input, input.getAttribute('aria-describedby')]));
  function resetContactError(input) {
    input.removeAttribute('aria-invalid');
    if (contactDescriptions.has(input)) input.setAttribute('aria-describedby', contactDescriptions.get(input));
    else input.removeAttribute('aria-describedby');
  }
  function clearContactErrors() {
    contact.querySelectorAll('[data-submit-field-error]').forEach(node => node.remove());
    contact.querySelectorAll('[aria-invalid]').forEach(resetContactError);
  }
  contact.addEventListener('input', event => {
    const input = event.target;
    if (!input.hasAttribute('aria-invalid')) return;
    input.closest('.lead-field,.lead-consent')?.querySelector('[data-submit-field-error]')?.remove();
    resetContactError(input);
  });
  form.addEventListener('submit', event => {
    event.preventDefault(); if (busy || form.dataset.submitted) return;
    if (!quote) { next.click(); return; }
    if (!form.reportValidity()) return;
    const files = [...form.querySelector('[name=attachments]').files];
    submitErrors.hidden = true;
    clearContactErrors();
    const showSubmitErrors = errors => {
      contact.querySelectorAll('[data-submit-field-error]').forEach(node => node.remove());
      submitErrors.replaceChildren(...Object.values(errors).flat().map(message => el('p', '', message))); submitErrors.hidden = false;
      for (const [name, messages] of Object.entries(errors)) {
        const input = form.elements.namedItem(name);
        if (!(input instanceof HTMLElement)) continue;
        const group = input.closest('.lead-field') || input.closest('.lead-consent');
        if (!group) continue;
        const line = el('p', 'config-error', messages.join(' ')); line.id = `config-contact-error-${name}`; line.dataset.submitFieldError = '';
        group.append(line); input.setAttribute('aria-invalid', 'true'); input.setAttribute('aria-describedby', [contactDescriptions.get(input), line.id].filter(Boolean).join(' '));
      }
    };
    if (files.length > 3 || files.some(file => file.size > 8 * 1024 * 1024)) { showSubmitErrors({ attachments: ['Можно приложить до 3 файлов по 8 МБ.'] }); return; }
    const data = payload(); setBusy(true); status.hidden = false; status.textContent = 'Сохраняем заявку…';
    contact.querySelectorAll('input,select,textarea,button').forEach(input => { input.disabled = true; });
    const xhr = new XMLHttpRequest(), progress = find('upload'); xhr.open('POST', form.dataset.api); xhr.timeout = 90000; progress.hidden = !files.length;
    xhr.upload.onprogress = event => { if (event.lengthComputable) progress.value = 100 * event.loaded / event.total; };
    const finish = () => { progress.hidden = true; setBusy(false); if (!form.dataset.submitted) contact.querySelectorAll('input,select,textarea,button').forEach(input => { input.disabled = false; }); };
    xhr.onload = () => {
      let body; try { body = JSON.parse(xhr.responseText); } catch { body = {}; }
      if (!body || typeof body !== 'object' || Array.isArray(body)) body = {};
      if (xhr.status >= 200 && xhr.status < 300 && body.ok) {
        status.textContent = `${body.message} Номер: ${body.reference}`; form.dataset.submitted = 'true';
        try { sessionStorage.removeItem(STORAGE_KEY); } catch { /* Storage optional. */ }
        finish(); form.querySelectorAll('input,select,textarea,button').forEach(input => { input.disabled = true; });
        document.dispatchEvent(new CustomEvent('vlico:lead-saved', { detail: { kind: 'calculator' } }));
      } else {
        status.hidden = true;
        if (body.quote) { showQuote(body.quote); showContact(true); }
        showSubmitErrors(body.errors || { __all__: ['Не удалось сохранить заявку. Ответы и контакты остались в форме. Попробуйте снова.'] }); finish();
      }
    };
    xhr.onerror = xhr.ontimeout = () => { status.hidden = true; showSubmitErrors({ __all__: ['Связь прервалась. Повторите отправку: повторная попытка не создаст вторую заявку.'] }); finish(); };
    xhr.send(data);
  });
  if (bootstrap.quote) {
    showQuote(bootstrap.quote);
    if (Object.keys(bootstrap.errors).length) showContact(true);
  } else {
    const target = schema.steps.findIndex(s => s.fields.some(name => bootstrap.errors[name]));
    if (target >= 0) step = target;
    render();
    if (target >= 0) fieldErrors(bootstrap.errors);
  }
});
