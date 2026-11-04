const dialog = document.querySelector('.gallery-dialog');
const links = [...document.querySelectorAll('[data-gallery]')];
const photos = [...new Map(links.map(link => [link.href, link])).values()];
if (dialog && typeof dialog.showModal === 'function') {
  let index = 0;
  let opener;
  const photo = dialog.querySelector('.gallery-stage img');
  const show = next => {
    index = (next + photos.length) % photos.length;
    photo.src = photos[index].href;
    photo.alt = photos[index].dataset.alt || '';
    dialog.querySelector('[data-caption]').textContent = photos[index].dataset.caption || '';
    dialog.querySelector('[data-counter]').textContent = `${index + 1} / ${photos.length}`;
  };
  links.forEach((link, i) => link.addEventListener('click', event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey) return;
    event.preventDefault(); opener = link; show(photos.findIndex(photo => photo.href === link.href)); dialog.showModal();
  }));
  dialog.querySelector('[data-close]').addEventListener('click', () => dialog.close());
  dialog.querySelector('[data-prev]').addEventListener('click', () => show(index - 1));
  dialog.querySelector('[data-next]').addEventListener('click', () => show(index + 1));
  dialog.addEventListener('keydown', event => {
    if (event.key === 'ArrowRight') { event.preventDefault(); show(index + 1); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); show(index - 1); }
  });
  dialog.addEventListener('close', () => opener?.focus());
  let startX;
  photo.addEventListener('touchstart', event => { startX = event.changedTouches[0].clientX; }, { passive: true });
  photo.addEventListener('touchend', event => {
    const delta = event.changedTouches[0].clientX - startX;
    if (Math.abs(delta) > 60) show(index + (delta < 0 ? 1 : -1));
  }, { passive: true });
  photo.addEventListener('error', () => { dialog.querySelector('[data-caption]').textContent = 'Не удалось загрузить фотографию. Попробуйте открыть её позже.'; });
}
