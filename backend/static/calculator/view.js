import { visible, numeric } from './model.js';
export function el(tag, className, text) {
  const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = text; return node;
}
const images = { 'edge:standard': 'calculator/edge-classic.webp', 'edge:shadow': 'calculator/edge-shadow.webp', 'edge:floating': 'calculator/edge-floating.webp', 'lights:spots': 'calculator/light-spots.webp', 'material:pvc': 'calculator/room-matte.webp', 'material:pvc_satin': 'calculator/room-satin.webp', 'material:pvc_gloss': 'calculator/room-gloss.webp', 'material:fabric': 'calculator/room-fabric.webp', 'lights:light_lines': 'calculator/light-lines.webp', 'lights:tracks': 'calculator/light-tracks.webp', 'lights:chandeliers': 'calculator/light-pendant.webp', 'lights:led': 'calculator/light-contour.webp', 'cornice:standard': 'calculator/curtain-ceiling.webp', 'cornice:hidden': 'calculator/curtain-hidden.webp', 'cornice:wall': 'calculator/curtain-wall.webp', 'cornice:none': 'calculator/curtain-none.webp' };
const descriptions = { 'material:pvc': 'Спокойная ровная поверхность. Не отражает интерьер.', 'material:pvc_satin': 'Мягкий перламутровый отсвет. Без зеркальных отражений.', 'material:pvc_gloss': 'Зеркальный блеск. Отражает окна и обстановку комнаты.', 'material:fabric': 'Матовая текстильная поверхность с тонкой фактурой.', 'edge:standard': 'Аккуратный закрытый стык. Белая вставка соединяет потолок со стеной.', 'edge:shadow': 'Тонкий тёмный зазор по периметру. Без подсветки.', 'edge:floating': 'Мягкая подсветка вдоль стены создаёт ощущение парящего потолка.' };
Object.assign(descriptions, { 'lights:spots': 'Небольшие светильники, равномерно распределённые по потолку.', 'lights:light_lines': 'Непрерывные линии света, встроенные в плоскость потолка.', 'lights:tracks': 'Тонкие треки с направленными световыми модулями.', 'lights:chandeliers': 'Подвесной светильник как акцент над зоной отдыха.', 'lights:led': 'Мягкий свет по периметру потолка.' });
Object.assign(descriptions, { 'cornice:standard': 'Видимый карниз закреплён на потолке. Шторы подвешены под ним.', 'cornice:hidden': 'Крепление спрятано в нише. Шторы словно выходят из потолка.', 'cornice:wall': 'Карниз закреплён над окном на стене, отдельно от потолка.', 'cornice:none': 'Окно без карниза и штор. Дополнительное крепление не требуется.' });
const NS = 'http://www.w3.org/2000/svg';
function svgNode(tag, attrs) { const node = document.createElementNS(NS, tag); for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value); return node; }
export function diagram(type, label, a = {}) {
  const svg = svgNode('svg', { viewBox: '0 0 360 240', role: 'img', 'aria-label': label });
  const line = (tag, attrs) => svg.append(svgNode(tag, { fill: 'none', stroke: 'currentColor', 'stroke-width': 2, ...attrs }));
  const text = (x, y, value) => { const t = svgNode('text', { x, y, 'text-anchor': 'middle', fill: 'currentColor', 'font-size': 13 }); t.textContent = value; svg.append(t); };
  const shape = a.shape || type;
  const l = numeric(a.length), w = numeric(a.width), known = a.size_mode === 'dimensions' && shape === 'rectangle' && l > 0 && w > 0;
  const scale = known ? Math.min(240 / l, 145 / w) : 1;
  const rw = known ? Math.max(35, l * scale) : 230;
  const rh = known ? Math.max(25, w * scale) : 140;
  if (shape === 'l') line('path', { d: 'M65 45H205V115H295V195H65Z' });
  else if (shape === 'complex') line('path', { d: 'M70 50H220L290 100V190H135L70 140Z' });
  else line('rect', { x: (360-rw)/2, y: (220-rh)/2, width: rw, height: rh });
  text(180, 22, known ? `${l.toLocaleString('ru-RU')} м` : 'Схема помещения');
  text(180, 230, known ? `${w.toLocaleString('ru-RU')} м · ${(l*w).toLocaleString('ru-RU', {maximumFractionDigits:2})} м²` : 'Размеры уточним на замере');
  return svg;
}
export function media(key, assets, a) {
  const comparison = ['material:', 'edge:', 'lights:', 'cornice:'].some(prefix => key.startsWith(prefix));
  if (images[key]) { const img = el('img'); img.src = assets + images[key]; img.alt = descriptions[key] || 'Пример потолочного решения'; img.width = 480; img.height = comparison ? 360 : 320; img.loading = 'lazy'; if (comparison) { img.srcset = `${assets + images[key].replace('.webp', '-small.webp')} 480w, ${img.src} 1440w`; img.sizes = '(max-width: 767px) 90vw, 40vw'; } return img; }
  return null;
}
export function fieldView(name, spec, a, assets) {
  const group = el('fieldset', 'config-field'); group.dataset.field = name;
  const legend = el('legend', '', spec.label); group.append(legend);
  if (['choice', 'multi'].includes(spec.kind)) {
    const options = el('div', `config-options config-options-${name}`);
    for (const [value, title] of spec.choices) {
      const label = el('label', 'config-option');
      const input = el('input'); input.type = spec.kind === 'multi' ? 'checkbox' : 'radio'; input.name = name; input.value = value;
      input.setAttribute('aria-label', title);
      input.checked = spec.kind === 'multi' ? (a[name] || []).includes(value) : a[name] === value;
      const m = media(`${name}:${value}`, assets, a); if (m) { if (['material', 'edge', 'lights', 'cornice'].includes(name)) m.sizes = '(max-width: 767px) 42vw, 24vw'; label.classList.add('config-option-visual'); label.append(m); }
      if (name === 'shape' && value !== 'unknown') label.append(diagram(value, title, { shape: value }));
      const caption = el('span', 'config-option-caption'); caption.append(input, el('span', '', title)); label.append(caption);
      const description = descriptions[`${name}:${value}`]; if (description) label.append(el('small', '', description));
      if (name === 'material' && ['pvc_satin', 'pvc_gloss'].includes(value)) label.append(el('small', 'config-material-note', 'Доступность и стоимость уточним'));
      options.append(label);
    }
    group.append(options);
  } else {
    const input = el('input', 'config-input'); input.type = 'text'; input.id = `config-ui-${name}`; input.name = name; input.value = a[name] || '';
    input.autocomplete = 'off'; input.maxLength = spec.kind === 'number' ? 12 : 120;
    if (spec.kind === 'number') { input.inputMode = spec.integer ? 'numeric' : 'decimal'; input.placeholder = 'Пока не знаю'; }
    const label = el('label', 'config-sr', spec.label); label.htmlFor = input.id; group.append(label);
    if (spec.integer) {
      const counter = el('div', 'config-counter');
      for (const [title, delta] of [['Уменьшить', -1], ['Увеличить', 1]]) {
        const button = el('button', '', delta === 1 ? '+' : '−'); button.type = 'button'; button.setAttribute('aria-label', `${title}: ${spec.label}`);
        button.addEventListener('click', () => { const value = Math.max(0, Math.min(Number(spec.max), (numeric(input.value) || 0) + delta)); input.value = value || ''; input.dispatchEvent(new Event('input', { bubbles: true })); });
        counter.append(button);
      }
      counter.insertBefore(input, counter.lastChild); group.append(counter);
    } else group.append(input);
  }
  return group;
}
export function summaryView(a, schema) {
  const dl = el('dl', 'config-summary');
  const labels = { room: 'Помещение', material: 'Поверхность', edge: 'Примыкание', lights: 'Освещение', cornice: 'Шторы', features: 'Монтаж', location: 'Расположение' };
  for (const name of ['room', 'material', 'edge', 'lights', 'cornice', 'features', 'location']) {
    const value = a[name], spec = schema.fields[name]; if (!value || !value.length) continue;
    const selected = Array.isArray(value) ? value : [value];
    const row = el('div'); row.append(el('dt', '', labels[name]), el('dd', '', spec.choices.filter(([code]) => selected.includes(code)).map(([, title]) => title).join(', '))); dl.append(row);
  }
  let area = a.size_mode === 'unknown' ? null : numeric(a.area), perimeter = numeric(a.perimeter);
  if (a.size_mode === 'dimensions' && a.shape === 'rectangle') { area = numeric(a.length) * numeric(a.width); perimeter = 2 * (numeric(a.length) + numeric(a.width)); }
  if (area > 0 && Number.isFinite(area)) { const row = el('div'); row.append(el('dt', '', 'Размеры'), el('dd', '', `${area.toLocaleString('ru-RU', { maximumFractionDigits: 2 })} м²${perimeter > 0 && Number.isFinite(perimeter) ? ' · ' + perimeter.toLocaleString('ru-RU', { maximumFractionDigits: 2 }) + ' м по периметру' : ' · периметр уточним'}`)); dl.append(row); }
  return dl;
}
export const money = value => new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(Number(value)) + ' ₽';
export function quoteView(q) {
  const box = el('div');
  box.append(el('p', 'quote-label', q.total === null ? 'Стоимость уточнит специалист' : q.complete ? 'Предварительная стоимость' : 'Известная часть стоимости'), el('p', 'quote-total', q.total === null ? 'Индивидуальный расчёт' : money(q.total)));
  if (q.warnings?.length) { const ul = el('ul', 'config-warnings'); q.warnings.forEach(w => ul.append(el('li', '', w))); box.append(ul); }
  const dl = el('dl', 'quote-lines');
  for (const item of q.items) { const row = el('div'), dt = el('dt', '', item.title); dt.append(el('small', '', `${item.quantity} ${item.unit} × ${money(item.unit_price)}`)); row.append(dt, el('dd', '', money(item.total))); dl.append(row); }
  box.append(dl, el('p', 'lead-help', q.exclusions));
  const details = el('details', 'config-details'); details.append(el('summary', '', 'Все выбранные параметры'));
  const selections = el('dl', 'config-summary');
  for (const item of q.configuration || []) { const row = el('div'); row.append(el('dt', '', item.label), el('dd', '', item.value)); selections.append(row); }
  details.append(selections); box.append(details); return box;
}
