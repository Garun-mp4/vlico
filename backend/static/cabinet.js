const logoutDialog = document.querySelector('#logout-dialog');
document.querySelector('[data-logout-open]')?.addEventListener('click', () => logoutDialog.showModal());

const loginPassword = document.querySelector('.login-panel input[type="password"]');
const passwordToggle = document.querySelector('[data-password-toggle]');
if (loginPassword && passwordToggle) {
  const showIcon = passwordToggle.querySelector('[data-password-show]');
  const hideIcon = passwordToggle.querySelector('[data-password-hide]');
  const updatePasswordToggle = () => {
    const visible = loginPassword.type === 'text';
    passwordToggle.setAttribute('aria-label', visible ? 'Скрыть пароль' : 'Показать пароль');
    passwordToggle.setAttribute('aria-pressed', String(visible));
    showIcon.hidden = visible;
    hideIcon.hidden = !visible;
  };
  passwordToggle.hidden = false;
  updatePasswordToggle();
  passwordToggle.addEventListener('click', () => {
    loginPassword.type = loginPassword.type === 'password' ? 'text' : 'password';
    updatePasswordToggle();
  });
}

const editor = document.querySelector('[data-image-editor]');
const uploadForm = document.querySelector('[data-upload]');
if (editor && typeof editor.showModal === 'function') {
  const prepareButton = uploadForm?.querySelector('[data-prepare-photos]');
  if (prepareButton) prepareButton.hidden = true;
  const form = editor.querySelector('[data-editor-form]');
  const field = name => form.elements.namedItem(name);
  const status = editor.querySelector('[data-editor-status]');
  const save = editor.querySelector('[data-editor-save]');
  const canvas = editor.querySelector('canvas');
  const context = canvas.getContext('2d');
  const skip = editor.querySelector('[data-editor-skip]');
  let baseline = null;
  let queue = [], index = 0, current, image, objectURL, rotation = 0, busy = false, saved = 0, opener, generation = 0;
  const message = (text, error = false) => {
    status.textContent = text;
    status.dataset.error = String(error);
    if (current?.file && error) { current.state = 'Ошибка — повторите сохранение или пропустите'; renderQueue(); }
  };
  function renderQueue() {
    const list = editor.querySelector('[data-upload-queue]');
    list.replaceChildren(); list.hidden = !queue.some(item => item.file);
    queue.forEach((item, i) => {
      if (!item.file) return;
      const row = document.createElement('li');
      row.textContent = `${item.file.name} · ${item.state || (i === index ? 'Подготовка' : 'В очереди')}`;
      if (i === index) row.setAttribute('aria-current','step');
      list.append(row);
    });
  }
  const settings = () => ({
    ratio: field('ratio').value, mode: field('mode').value, zoom: Number(field('zoom').value), x: Number(field('x').value), y: Number(field('y').value), rotation,
    alt: field('alt').value, caption: field('caption').value, section: field('section').value, cover: field('cover').checked
  });
  function draw() {
    if (!image) return;
    const data = settings();
    window.photoEditorDirty = Boolean(current?.file) || (baseline !== null && baseline !== JSON.stringify(data));
    const rotated = document.createElement('canvas');
    const swap = rotation === 90 || rotation === 270;
    rotated.width = swap ? image.naturalHeight : image.naturalWidth;
    rotated.height = swap ? image.naturalWidth : image.naturalHeight;
    const ctx = rotated.getContext('2d');
    ctx.translate(rotated.width / 2, rotated.height / 2);
    ctx.rotate(rotation * Math.PI / 180);
    ctx.drawImage(image, -image.naturalWidth / 2, -image.naturalHeight / 2);
    const w = rotated.width, h = rotated.height;
    const ratios = {'4:3':4/3, '3:4':3/4, '16:9':16/9, '9:16':9/16, '1:1':1};
    const ratio = data.ratio === 'original' ? w/h : (ratios[data.ratio] || 4/3);
    canvas.width = Math.max(1, Math.round(Math.min(800, 800*ratio)));
    canvas.height = Math.max(1, Math.round(canvas.width/ratio));
    canvas.style.setProperty('--editor-ratio', canvas.width/canvas.height);
    canvas.setAttribute('aria-label', `Предпросмотр: ${field('ratio').selectedOptions[0].textContent}`);
    context.fillStyle = '#f2f1e9'; context.fillRect(0, 0, canvas.width, canvas.height);
    if (data.mode === 'fit') {
      const scale = Math.min(canvas.width / w, canvas.height / h);
      context.drawImage(rotated, (canvas.width-w*scale)/2, (canvas.height-h*scale)/2, w*scale, h*scale);
    } else {
      const cw = Math.min(w, h*ratio) / data.zoom, ch = cw/ratio;
      context.drawImage(rotated, (w-cw)*data.x/100, (h-ch)*data.y/100, cw, ch, 0, 0, canvas.width, canvas.height);
    }
    editor.querySelector('[data-editor-zoom-value]').textContent = data.zoom.toFixed(2) + '×';
    ['zoom', 'x', 'y'].forEach(name => { field(name).disabled = data.mode === 'fit' || busy; });
  }
  async function show() {
    baseline = null;
    const token = ++generation;
    if (objectURL) URL.revokeObjectURL(objectURL);
    objectURL = null; image = null;
    current = queue[index]; renderQueue();
    skip.hidden = !current.file;
    message('Открываем фотографию…');
    save.disabled = true;
    editor.querySelector('[data-editor-counter]').textContent = current.file ? `Фото ${index+1} из ${queue.length} · сохранено ${saved}` : 'Редактирование сохранённой фотографии';
    const data = current.edit || {};
    rotation = data.rotation || 0;
    for (const [name, value] of Object.entries({ratio:'4:3', mode:'crop', zoom:1, x:50, y:50, ...data})) {
      if (field(name)) field(name).value = value;
    }
    field('alt').value = current.alt || '';
    field('caption').value = current.caption || '';
    field('section').value = current.section || 'result';
    field('cover').checked = Boolean(current.cover);
    try {
      const loaded = new Image();
      if (current.file) { objectURL = URL.createObjectURL(current.file); loaded.src = objectURL; }
      else loaded.src = current.source;
      await loaded.decode();
      if (token !== generation || !editor.open) return;
      if (loaded.naturalWidth * loaded.naturalHeight > 16000000 || Math.min(loaded.naturalWidth,loaded.naturalHeight) < 64) throw new Error('Размер изображения: от 64 пикселей по стороне до 16 мегапикселей.');
      image = loaded;
      editor.querySelector('[data-editor-size]').textContent = `${current.file?.name || 'Сохранённый исходник'} · ${loaded.naturalWidth} × ${loaded.naturalHeight} px`;
      save.disabled = false; draw(); baseline = JSON.stringify(settings()); window.photoEditorDirty = Boolean(current.file);
      message('Настройте кадр и сохраните. При закрытии несохранённые фото не добавляются.');
    } catch (error) { if (token !== generation || !editor.open) return; message(error.message.includes('Размер') ? error.message : 'Не удалось открыть изображение. Пропустите его и выберите исправный JPEG, PNG или WebP.', true); }
  }
  function open(items, button) {
    if (changed || saving) { panelFeedback.textContent = 'Сначала сохраните изменения сведений о проекте.'; panelFeedback.scrollIntoView({block:'center'}); return; }
    queue = items; index = 0; saved = 0; opener = button;
    editor.showModal(); show();
  }
  async function finish() {
    if (busy) return;
    if ((image && baseline !== JSON.stringify(settings())) || (queue[index]?.file && index < queue.length)) {
      if (!await confirmDiscard()) return;
    }
    window.photoEditorDirty = false;
    generation++;
    editor.close();
    if (objectURL) URL.revokeObjectURL(objectURL);
    objectURL = null;
    if (saved) window.location.reload();
    else { uploadForm?.reset(); opener?.focus(); }
  }
  function next() { baseline = null; window.photoEditorDirty = false; image = null; if (++index < queue.length) show(); else finish(); }
  function startUpload(event) {
    event?.preventDefault();
    if (changed || saving) {
      uploadForm.querySelector('input[type=file]').value = '';
      panelFeedback.textContent = 'Сначала сохраните сведения о проекте, затем выберите фотографии.';
      panelFeedback.scrollIntoView({block:'center'});
      return;
    }
    const files = [...uploadForm.querySelector('input[type=file]').files];
    if (!files.length) return;
    if (files.some(file => !['image/jpeg','image/png','image/webp'].includes(file.type))) { uploadForm.querySelector('[data-upload-status]').textContent = 'Поддерживаются только JPEG, PNG и WebP. Проверьте выбранные файлы.'; return; }
    if (files.length + document.querySelectorAll('.media-item').length > 40) { uploadForm.querySelector('[data-upload-status]').textContent = 'В проекте может быть до 40 фотографий.'; return; }
    if (files.length > 8 || files.some(file => file.size > 12*1024*1024)) {
      uploadForm.querySelector('[data-upload-status]').textContent = 'Выберите до 8 файлов, не больше 12 МБ каждый.'; return;
    }
    const defaultAlt = document.querySelector('#id_title').value;
    open(files.map((file, i) => ({file, key:crypto.randomUUID(), alt:defaultAlt, section:uploadForm.elements.section.value, cover:i===0 && !document.querySelector('.media-item')})), document.querySelector('[data-pick-photos]'));
  }
  uploadForm?.addEventListener('submit', startUpload);
  uploadForm?.querySelector('input[type=file]').addEventListener('change', startUpload);
  const drop = uploadForm?.querySelector('[data-drop-zone]');
  drop?.addEventListener('dragover', event => { event.preventDefault(); drop.classList.add('drag-over'); });
  drop?.addEventListener('dragleave', () => drop.classList.remove('drag-over'));
  drop?.addEventListener('drop', event => { event.preventDefault(); drop.classList.remove('drag-over'); if (!event.dataTransfer.files.length) return; uploadForm.querySelector('input[type=file]').files = event.dataTransfer.files; startUpload(); });
  document.querySelectorAll('[data-image-edit]').forEach(button => button.addEventListener('click', () => {
    const card = button.closest('.media-item');
    open([{source:button.dataset.source, url:button.dataset.save, revision:button.dataset.revision,
      edit:JSON.parse(card.querySelector('script[type="application/json"]').textContent),
      alt:card.querySelector('input[name=alt]').value, caption:card.querySelector('input[name=caption]').value,
      section:card.querySelector('select[name=section]').value, cover:Boolean(card.querySelector('.status.published:not([hidden])'))}], button);
  }));
  form.addEventListener('input', draw);
  editor.querySelector('[data-editor-rotate]').addEventListener('click', () => { rotation = (rotation+90)%360; draw(); });
  editor.querySelector('[data-editor-reset]').addEventListener('click', () => {
    rotation = 0; field('zoom').value=1; field('x').value=50; field('y').value=50; field('mode').value='crop'; draw();
  });
  editor.querySelector('[data-editor-close]').addEventListener('click', finish);
  skip.addEventListener('click', () => { if (!busy) { current.state = 'Пропущено'; next(); } });
  editor.addEventListener('cancel', event => { event.preventDefault(); finish(); });
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (busy || !image) return;
    const data = settings();
    busy = true; window.photoEditorDirty = true;
    editor.querySelectorAll('button,input,select').forEach(control => control.disabled=true);
    const body = new FormData();
    body.append('csrfmiddlewaretoken', uploadForm.querySelector('[name=csrfmiddlewaretoken]').value);
    body.append('editing', JSON.stringify(data));
    if (current.file) { body.append('images', current.file); body.append('section', data.section); body.append('upload_key', current.key); }
    else body.append('revision', current.revision);
    const xhr = new XMLHttpRequest();
    xhr.open('POST', current.url || uploadForm.action);
    xhr.setRequestHeader('Accept','application/json'); xhr.responseType='json';
    message('Сохраняем фотографию…');
    xhr.upload.addEventListener('progress', event => {
      if (event.lengthComputable) message(`Загрузка ${Math.round(100*event.loaded/event.total)}%. Затем подготовим изображение.`);
    });
    const unlock = () => {
      busy=false; editor.querySelectorAll('button,input,select').forEach(control=>control.disabled=false); draw();
    };
    xhr.addEventListener('load', () => {
      unlock();
      if (xhr.status>=200 && xhr.status<300 && xhr.response?.saved) { current.state = 'Сохранено'; saved++; next(); }
      else message(xhr.response?.error || (xhr.status===403 ? 'Сессия истекла. Войдите заново; сохранённые фото останутся в проекте.' : 'Не удалось сохранить фото. Повторите или пропустите его.'),true);
    });
    xhr.addEventListener('error', () => { unlock(); message('Связь прервалась. Повторите сохранение: фотография не добавится дважды.',true); });
    xhr.send(body);
  });
}
