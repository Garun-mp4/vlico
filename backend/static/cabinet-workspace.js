/* Cabinet workflow: explicit text saves, independent gallery saves. */
const projectForm = document.querySelector('#project-form');
let changed = false;
let saving = false;
let pendingPhotos = new Set();
const saveState = document.querySelector('[data-save-state]');
const panelFeedback = document.querySelector('[data-panel-feedback]');
const csrf = () => document.querySelector('[name=csrfmiddlewaretoken]')?.value;
const discardDialog = document.querySelector('[data-discard-dialog]');
function confirmDiscard() {
  return new Promise(resolve => {
    discardDialog.showModal();
    const finish = value => { discardDialog.close(); resolve(value); };
    discardDialog.querySelector('[data-discard-yes]').onclick = () => finish(true);
    discardDialog.querySelector('[data-discard-cancel]').onclick = () => finish(false);
    discardDialog.oncancel = event => { event.preventDefault(); finish(false); };
  });
}
window.addEventListener('beforeunload', event => {
  if (changed || saving || pendingPhotos.size || window.photoEditorDirty) { event.preventDefault(); event.returnValue = ''; }
});
function publicationState() {
  document.querySelectorAll('[data-status-form] button').forEach(button => {
    if (!button.dataset.initialDisabled) button.dataset.initialDisabled = String(button.disabled);
    button.disabled = changed || saving || button.dataset.initialDisabled === 'true';
  });
  if (panelFeedback) panelFeedback.textContent = changed ? 'Сначала сохраните сведения: публикация и предпросмотр используют сохранённую версию.' : '';
}
document.querySelectorAll('[data-unsaved]:not(#project-form)').forEach(form => {
  form.addEventListener('input', () => { changed=true; });
  form.addEventListener('submit', () => { changed=false; });
});
document.addEventListener('input', event => {
  if (projectForm && event.target.form === projectForm) {
    changed = true;
    saveState.textContent = 'Есть несохранённые изменения';
    publicationState();
  }
});
if (projectForm) projectForm.addEventListener('submit', async event => {
  event.preventDefault();
  if (saving) return;
  const fields = [...projectForm.elements];
  if (!fields.every(field => !field.reportValidity || field.reportValidity())) return;
  saving = true;
  const button = document.querySelector('[data-project-save]');
  const label = button.textContent;
  button.disabled = true; button.textContent = 'Сохраняем…'; saveState.textContent = 'Сохранение…';
  publicationState();
  const body = new FormData(projectForm);
  // Freeze this snapshot until the request completes; typing cannot become falsely saved.
  const editable = fields.filter(field => field.type !== 'hidden' && !field.disabled);
  editable.forEach(field => field.disabled = true);
  document.querySelectorAll('.field-errors').forEach(el => el.replaceChildren());
  document.querySelectorAll('[aria-invalid]').forEach(el => el.removeAttribute('aria-invalid'));
  const errors = projectForm.querySelector('[data-form-errors]'); errors.replaceChildren();
  try {
    const response = await fetch(projectForm.action || location.href, {method:'POST', body, headers:{Accept:'application/json'}});
    const result = await response.json();
    if (!response.ok) {
      for (const [name, messages] of Object.entries(result.errors || {})) {
        const target = document.querySelector(`[data-field="${name}"] .field-errors`) || errors;
        const list = document.createElement('ul'); list.className = 'errorlist'; list.id = `error-${name}`;
        messages.forEach(message => { const li=document.createElement('li'); li.textContent=message.message; list.append(li); });
        target.append(list);
        const field = projectForm.elements.namedItem(name);
        if (field?.setAttribute) { field.setAttribute('aria-invalid','true'); field.setAttribute('aria-describedby',list.id); }
      }
      throw new Error('Не удалось сохранить. Проверьте отмеченные поля.');
    }
    changed = false;
    if (result.created) { saving = false; location.assign(result.url); return; }
    projectForm.elements.revision.value = result.revision;
    document.querySelector('[data-project-title]').textContent = result.title;
    document.title = `${result.title} · Кабинет VLICO`;
    saveState.textContent = 'Изменения сохранены';
    const solution = projectForm.elements.solution.value.trim();
    const solutionCheck = document.querySelector('[data-check="solution"]');
    if (solutionCheck) solutionCheck.textContent = `${solution ? '✓' : '○'} Решение и результат`;
    const publish = document.querySelector('[data-publish]');
    if (publish) publish.dataset.initialDisabled = String(!solution || !document.querySelector('.photo-open .status'));
    const reason=document.querySelector('[data-publish-reason]');
    if (reason) reason.textContent = !solution || !document.querySelector('.photo-open .status') ? 'Добавьте обложку и описание решения перед публикацией.' : '';
  } catch (error) {
    saveState.textContent = 'Изменения не сохранены';
    if (!errors.textContent) errors.textContent = error.message.includes('Проверьте') ? error.message : 'Не удалось сохранить. Проверьте соединение и повторите. Ваши данные остались в форме.';
    errors.scrollIntoView({block:'center'});
  } finally {
    saving=false; editable.forEach(field => field.disabled=false); button.disabled=false; button.textContent=label; publicationState();
    document.querySelector('[aria-invalid=true]')?.focus();
  }
});
document.addEventListener('click', async event => {
  const link = event.target.closest('a');
  if (link && (changed || saving) && !link.getAttribute('href')?.startsWith('#')) {
    event.preventDefault();
    if (link.matches('[data-preview]')) { panelFeedback.textContent='Сохраните сведения, чтобы увидеть их в предпросмотре.'; return; }
    if (saving) return;
    if (await confirmDiscard()) { changed=false; location.assign(link.href); }
  }
});
document.querySelectorAll('[data-status-form], [data-gallery-action], [data-photo-form]').forEach(form => {
  form.addEventListener('submit', event => {
    if (changed || saving) {
      event.preventDefault(); panelFeedback.textContent='Сначала сохраните сведения о проекте.';
      panelFeedback.scrollIntoView({block:'center'}); return;
    }
    if (form.dataset.submitting) { event.preventDefault(); return; }
    if (form.matches('[data-photo-form]')) pendingPhotos.delete(form);
    form.dataset.submitting='true';
    // Keep submitter enabled so its action remains part of the native POST.
    form.setAttribute('aria-busy','true');
  });
});
document.querySelectorAll('[data-photo-open]').forEach(button => button.addEventListener('click', () => {
  const dialog = document.getElementById(button.dataset.photoOpen);
  button.closest('details')?.removeAttribute('open');
  dialog.showModal();
}));
document.querySelectorAll('.photo-drawer').forEach(dialog => {
  const form=dialog.querySelector('[data-photo-form]');
  form.addEventListener('input', () => pendingPhotos.add(form));
  async function close() {
    if (pendingPhotos.has(form)) {
      if (!await confirmDiscard()) return;
      form.reset(); pendingPhotos.delete(form);
    }
    dialog.close();
  }
  dialog.querySelector('[data-photo-close]').addEventListener('click', close);
  dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
});
// Keep photo menus within the viewport, including the first mobile thumbnail.
document.addEventListener('toggle', event => {
  const menu = event.target;
  if (!menu.matches('.media-meta .context-menu') || !menu.open) return;
  const content = menu.querySelector('.menu-content');
  content.style.left = ''; content.style.right = '';
  const bounds = content.getBoundingClientRect();
  if (bounds.left < 12) {
    content.style.right = 'auto';
    content.style.left = `${12 - menu.getBoundingClientRect().left}px`;
  }
}, true);
// Native disclosures keep menus keyboard accessible; close on Escape/outside click.
document.addEventListener('click', event => document.querySelectorAll('.context-menu[open]').forEach(menu => {
  if (!menu.contains(event.target)) menu.open=false;
}));
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') document.querySelectorAll('.context-menu[open]').forEach(menu => {menu.open=false;menu.querySelector('summary').focus();});
});
const filterForm = document.querySelector('[data-project-filters]');
if (filterForm) {
  const feedback=document.querySelector('[data-list-feedback]');
  let controller, timer, sequence=0;
  filterForm.querySelector('[data-filter-submit]').hidden=true;
  async function load() {
    const current=++sequence;
    controller?.abort(); controller=new AbortController();
    const params=new URLSearchParams(new FormData(filterForm));
    const url=`${location.pathname}?${params}`;
    const results=document.querySelector('[data-project-results]');
    results.setAttribute('aria-busy','true'); feedback.textContent='Загружаем проекты…';
    try {
      const response=await fetch(url,{signal:controller.signal});
      if (!response.ok) throw new Error();
      const doc=new DOMParser().parseFromString(await response.text(),'text/html');
      const next=doc.querySelector('[data-project-results]');
      if (!next) throw new Error();
      if (current !== sequence) return;
      results.replaceWith(next); history.replaceState(null,'',url);
      feedback.textContent=`Найдено проектов: ${next.querySelectorAll('.project-row').length}`;
    } catch(error) {
      if (error.name === 'AbortError' || current !== sequence) return;
      feedback.textContent='Не удалось загрузить список. Проверьте соединение. ';
      const retry=document.createElement('button'); retry.className='button'; retry.textContent='Повторить'; retry.onclick=load; feedback.append(retry);
    } finally {if(current === sequence) results.removeAttribute('aria-busy');}
  }
  filterForm.addEventListener('submit',event=>{event.preventDefault();clearTimeout(timer);load();});
  filterForm.addEventListener('input',event=>{if(event.target.name==='q'){clearTimeout(timer);timer=setTimeout(load,250);}});
  filterForm.addEventListener('change',event=>{if(event.target.name!=='q'){clearTimeout(timer);load();}});
  document.addEventListener('click',event=>{
    const tab=event.target.closest('[data-status]');
    if(!tab)return;
    event.preventDefault();filterForm.elements.status.value=tab.dataset.status;clearTimeout(timer);load();
  });
}
document.querySelector('[data-pick-photos]')?.addEventListener('click', () => document.querySelector('#images').click());
const grid=document.querySelector('[data-reorder-url]');
if(grid) {
  let dragged, busy=false;
  const feedback=document.querySelector('[data-gallery-feedback]');
  const cards=()=>[...grid.querySelectorAll(':scope > .media-item')];
  const addTile=grid.querySelector('[data-pick-photos]');
  grid.addEventListener('dragstart',event=>{
    if(busy || changed || saving || event.target.closest('dialog, .context-menu')) {event.preventDefault();return;}
    dragged=event.target.closest('.media-item');
    if(!dragged)return;
    event.dataTransfer.setData('text/plain',dragged.dataset.mediaId);event.dataTransfer.effectAllowed='move';dragged.classList.add('dragging');
  });
  grid.addEventListener('dragover',event=>{const card=event.target.closest('.media-item');if(dragged&&card){event.preventDefault();document.querySelectorAll('.drop-target').forEach(el=>el.classList.remove('drop-target'));card.classList.add('drop-target');}});
  grid.addEventListener('dragend',()=>{dragged?.classList.remove('dragging');dragged=null;document.querySelectorAll('.drop-target').forEach(el=>el.classList.remove('drop-target'));});
  grid.addEventListener('drop',async event=>{
    event.preventDefault();const target=event.target.closest('.media-item');
    if(!dragged||!target||dragged===target||busy)return;
    const old=cards(), from=old.indexOf(dragged), to=old.indexOf(target);
    if(from<to)target.after(dragged);else target.before(dragged);
    const body=new FormData();body.append('csrfmiddlewaretoken',csrf());body.append('revision',projectForm.elements.revision.value);
    cards().forEach(el=>body.append('order',el.dataset.mediaId));
    busy=true;saving=true;publicationState();feedback.textContent='Сохраняем порядок…';grid.setAttribute('aria-busy','true');
    // Lock project save until gallery revision is known.
    const button=document.querySelector('[data-project-save]');button.disabled=true;
    try {
      const response=await fetch(grid.dataset.reorderUrl,{method:'POST',body,headers:{Accept:'application/json'}});
      const result=await response.json();if(!response.ok)throw new Error(result.error);
      projectForm.elements.revision.value=result.revision;feedback.textContent='Порядок фотографий сохранён';
      cards().forEach((card,index)=>{card.querySelector('button[value=up]').disabled=index===0;card.querySelector('button[value=down]').disabled=index===cards().length-1;});
    }catch(error){old.forEach(card=>grid.insertBefore(card,addTile));feedback.textContent=error.message.includes('Галерея')||error.message.includes('Состав')?error.message:'Не удалось подтвердить сохранение. На экране восстановлен прежний порядок. Обновите страницу и повторите.';}
    finally{busy=false;saving=false;publicationState();button.disabled=false;grid.removeAttribute('aria-busy');}
  });
}
