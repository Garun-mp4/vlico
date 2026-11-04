document.querySelectorAll('[data-upload]').forEach(form => {
  form.addEventListener('submit', event => {
    const files = [...form.querySelector('input[type=file]').files];
    const status = form.querySelector('[data-upload-status]');
    if (files.length > 8 || files.some(file => file.size > 12 * 1024 * 1024)) {
      event.preventDefault(); status.textContent = 'Выберите до 8 файлов, не больше 12 МБ каждый.'; return;
    }
    status.textContent = 'Фотографии загружаются и подготавливаются. Дождитесь обновления страницы.';
    form.querySelector('button[type=submit]').disabled = true;
  });
});
let changed = false;
document.querySelectorAll('[data-unsaved]').forEach(form => {
  form.addEventListener('input', () => { changed = true; });
  form.addEventListener('submit', () => { changed = false; });
});
window.addEventListener('beforeunload', event => {
  if (changed) { event.preventDefault(); event.returnValue = ''; }
});
