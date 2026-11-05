import { el, money } from './view.js';

export function livePrice(form, shell, panel, payload, answers) {
  const box = form.querySelector('[data-config-price]');
  const fields = JSON.parse(document.getElementById('config-schema').textContent).fields;
  let timer, request, revision = 0, previous = null, options = {}, changed = '', state = 'empty';
  const label = el('p', 'config-price-label'), total = el('p', 'config-price-total');
  const note = el('p', 'config-price-note'), delta = el('p', 'config-price-delta');
  const retry = el('button', 'config-back', 'Повторить расчёт'); retry.type = 'button';
  const details = el('details', 'config-price-details'), summary = el('summary', '', 'Что ещё уточнить');
  const warnings = el('ul'); details.append(summary, warnings);
  const announcement = el('span', 'config-sr'); announcement.setAttribute('role', 'status');
  box.append(label, total, note, delta, retry, details, announcement); box.hidden = false;
  new ResizeObserver(() => form.style.setProperty('--config-price-height', `${box.getBoundingClientRect().height}px`)).observe(box);
  function placement() {
    const rect = shell.getBoundingClientRect();
    box.classList.toggle('is-visible', !shell.hidden && rect.top < innerHeight && rect.bottom > 120);
  }
  window.addEventListener('scroll', placement, {passive:true}); window.addEventListener('resize', placement);
  form.addEventListener('focusin', e => form.classList.toggle('config-keyboard', e.target.matches('input[type=text],textarea')));
  form.addEventListener('focusout', () => form.classList.remove('config-keyboard'));
  function annotate() {
    panel.querySelectorAll('.config-option-price').forEach(n => n.remove());
    for (const input of panel.querySelectorAll('.config-option input')) {
      if (!['material', 'edge', 'lights', 'cornice', 'features', 'location'].includes(input.name)) continue;
      if (['none', 'unknown', 'wall', 'city', 'height'].includes(input.value)) continue;
      const item = options[`${input.name}:${input.value}`];
      let text = state === 'pending' ? 'Обновляем стоимость…' : state === 'error' ? 'Стоимость временно недоступна' : 'Стоимость уточняется';
      if (item && state === 'ready') text = `${money(item.unit_price)} / ${item.unit}${item.total !== null ? ` · Полная позиция: ${money(item.total)}` : ' · Укажите количество'}`;
      input.closest('label').append(el('small', 'config-option-price', text));
    }
  }
  function pending() {
    state = 'pending'; box.setAttribute('aria-busy', 'true');
    label.textContent = 'Пересчитываем стоимость'; total.textContent = '…'; note.textContent = 'Учитываем текущие ответы';
    delta.textContent = ''; retry.hidden = true; details.hidden = true; annotate();
    announcement.textContent = 'Пересчитываем стоимость';
  }
  async function fetchPrice(token) {
    request = new AbortController(); const active = request;
    const timeout = setTimeout(() => active.abort(), 20000);
    try {
      const data = payload(); data.set('preview', '1');
      const response = await fetch(form.dataset.estimateApi, {method:'POST', body:data, signal:active.signal, headers:{Accept:'application/json'}});
      const body = await response.json();
      if (token !== revision) return;
      if (!response.ok || !body?.quote) throw new Error(response.status === 400 ? 'input' : 'network');
      const q = body.quote; state = 'ready'; options = body.options || {};
      label.textContent = q.total === null ? 'Предварительная стоимость' : 'Учтено в расчёте:';
      total.textContent = q.total === null ? 'Стоимость уточняется' : money(q.total);
      note.textContent = q.total === null ? (!answers().material || !Number(q.inputs.area) ? 'Укажите размеры и выберите материал — покажем стоимость' : 'Для выбранного материала стоимость уточняется') : q.complete ? 'Все ответы получены · предварительная стоимость' : `Неполный расчёт. ${q.warnings[0]}`;
      delta.textContent = '';
      if (previous && previous.version !== q.version) delta.textContent = 'Тарифы обновились. Стоимость пересчитана.';
      else if (previous?.total !== null && previous && q.total !== null && changed) {
        const difference = Number(q.total) - Number(previous.total);
        delta.textContent = difference ? `${changed}: ${difference > 0 ? '+' : '−'}${money(Math.abs(difference))}` : 'Стоимость учтённых позиций не изменилась';
      }
      previous = q;
      warnings.replaceChildren(...q.warnings.map(w => el('li', '', w)));
      details.hidden = !q.warnings.length; retry.hidden = true; box.setAttribute('aria-busy','false');
      announcement.textContent = `${label.textContent} ${total.textContent}. ${note.textContent}`; annotate();
    } catch (err) {
      if (token !== revision) return;
      state = 'error'; box.setAttribute('aria-busy','false');
      label.textContent = 'Расчёт не обновлён'; total.textContent = 'Стоимость недоступна';
      note.textContent = err.message === 'input' ? 'Проверьте введённые размеры и количества.' : 'Проверьте соединение и повторите. Ответы сохранены.';
      retry.hidden = false; annotate();
      announcement.textContent = `${label.textContent}. ${note.textContent}`;
    } finally { clearTimeout(timeout); }
  }
  function schedule(name = '', delay = 350) {
    const spec = fields[name];
    changed = spec ? spec.label : '';
    if (name === 'spots' && answers().spots) changed = `${answers().spots} световых точек`;
    const token = ++revision; clearTimeout(timer); request?.abort(); pending();
    timer = setTimeout(() => fetchPrice(token), delay); placement();
  }
  retry.addEventListener('click', () => schedule('', 0));
  window.addEventListener('focus', () => { if (!shell.hidden) schedule('', 0); });
  return {schedule, refresh: () => {annotate(); placement();}, cancel: () => {++revision; clearTimeout(timer); request?.abort(); placement();}};
}
