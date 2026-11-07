export const STORAGE_KEY = 'vlico-calculator-v2';
export const initial = () => ({ schema: 'v2', object_type: 'room', room: '', size_mode: 'dimensions', shape: 'rectangle', material: '', edge: '', lights: [], cornice: '', features: [], location: '', zones_enabled: 'no' });
export function visible(name, a) {
  const multi = ['apartment', 'house'].includes(a.object_type);
  const zones = multi && a.zones_enabled === 'yes';
  if (name === 'object_type' || name === 'zones_enabled') return name === 'object_type' || multi;
  if (name === 'object_area') return multi;
  if (name === 'room' || name === 'room_other') return !multi && (name === 'room' || a.room === 'other');
  if (/^zone_[1-3]_(name|area|material|edge)$/.test(name)) return zones;
  if (name === 'size_mode') return !multi;
  if (name === 'shape') return !multi && a.size_mode === 'dimensions';
  if (name === 'length' || name === 'width') return !multi && a.size_mode === 'dimensions' && a.shape === 'rectangle';
  if (name === 'area' || name === 'perimeter') return !multi && a.size_mode !== 'unknown' && !(a.size_mode === 'dimensions' && a.shape === 'rectangle');
  if (name === 'area_range') return !multi && a.size_mode === 'unknown';
  if (zones && ['material', 'edge'].includes(name)) return false;
  const rules = {
    length: () => a.size_mode === 'dimensions' && a.shape === 'rectangle',
    width: () => a.size_mode === 'dimensions' && a.shape === 'rectangle',
    area: () => a.size_mode !== 'unknown' && !(a.size_mode === 'dimensions' && a.shape === 'rectangle'),
    perimeter: () => a.size_mode !== 'unknown' && !(a.size_mode === 'dimensions' && a.shape === 'rectangle'),
    area_range: () => a.size_mode === 'unknown',
    cornices: () => ['standard', 'hidden'].includes(a.cornice),
    locality: () => ['region', 'other'].includes(a.location),
    pipes: () => a.features.includes('pipes'), vents: () => a.features.includes('vents'),
  };
  if (['spots', 'light_lines', 'tracks', 'chandeliers', 'led'].includes(name)) return a.lights.includes(name);
  return rules[name] ? rules[name]() : true;
}
export function change(a, name, value, multi = false) {
  if (!multi) return { ...a, [name]: value };
  const exclusive = ['none', 'unknown'];
  const values = a[name] || [];
  return { ...a, [name]: values.includes(value) ? values.filter(v => v !== value) : exclusive.includes(value) ? [value] : [...values.filter(v => !exclusive.includes(v)), value] };
}
export const numeric = value => Number(String(value ?? '').replace(',', '.'));
export function validNumber(value, field) {
  const n = numeric(value);
  return Number.isFinite(n) && n >= (field.integer ? 1 : 0.1) && n <= Number(field.max)
    && (field.integer ? /^\d+$/.test(String(value)) && Number.isInteger(n) : /^\d+(?:[.,]\d{1,2})?$/.test(String(value)));
}
export function validate(a, step, fields) {
  const errors = {};
  for (const name of step.fields.filter(name => visible(name, a))) {
    const field = fields[name], value = a[name];
    if ((field.kind === 'choice' || field.kind === 'multi') && name !== 'area_range' && (!value || !value.length)) errors[name] = 'Выберите ответ, чтобы продолжить.';
    const mandatory = ['length', 'width', 'area', 'object_area', 'locality'].includes(name);
    if (mandatory && !String(value || '').trim()) errors[name] = 'Заполните поле или выберите «Не знаю».';
    if (field.kind === 'number' && value !== undefined && value !== '') {
      if (!validNumber(value, field)) errors[name] = `Укажите ${field.integer ? 'целое число' : 'число'} от ${field.integer ? 1 : '0,1'} до ${field.max}.`;
    }
  }
  if (step.fields.includes('length') && step.fields.includes('width') && visible('length', a) && !errors.length && !errors.width) {
    // Lengths have at most two decimal places; integer centimetres avoid rounding drift.
    const area = Math.round(Math.round(numeric(a.length) * 100) * Math.round(numeric(a.width) * 100) / 100) / 100;
    if (area < 0.1) errors.length = 'Площадь должна быть не меньше 0,1 м².';
  }
  if (step.fields.some(name => name.startsWith('zone_') && name.endsWith('_area')) && visible('zone_1_area', a)) {
    const sum = [1, 2, 3].reduce((total, i) => total + (numeric(a[`zone_${i}_area`]) || 0), 0);
    const whole = numeric(a.object_area);
    if (whole > 0 && sum > whole) errors.object_area = 'Сумма площадей зон не может превышать площадь объекта.';
    for (let i = 1; i <= 3; i++) {
      const keys = [`zone_${i}_name`, `zone_${i}_area`, `zone_${i}_material`, `zone_${i}_edge`];
      const any = keys.some(key => String(a[key] || '').trim());
      if (any) for (const key of keys) if (!String(a[key] || '').trim()) errors[key] = 'Заполните зону целиком или очистите её.';
    }
    if (![1, 2, 3].some(i => a[`zone_${i}_area`] && a[`zone_${i}_material`])) errors.zones_enabled = 'Добавьте хотя бы одну заполненную зону.';
  }
  return errors;
}
export function restore(schema) {
  const a = initial();
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY));
    if (saved?.schema !== 'v2') return a;
    for (const [key, field] of Object.entries(schema.fields)) {
      const value = saved[key];
      if (field.kind === 'multi' && Array.isArray(value)) {
        const values = [...new Set(value.filter(v => field.choices.some(([code]) => code === v)))];
        a[key] = values.length > 1 && values.some(v => ['none', 'unknown'].includes(v)) ? [] : values;
      }
      else if (field.kind === 'choice' && field.choices.some(([code]) => code === value)) a[key] = value;
      else if (field.kind === 'number' && typeof value === 'string' && (value === '' || validNumber(value, field))) a[key] = value;
      else if (field.kind === 'text' && typeof value === 'string' && value.length <= (field.max_length || 120)) a[key] = value;
    }
  } catch { /* Storage is optional; the current form remains usable. */ }
  return a;
}
