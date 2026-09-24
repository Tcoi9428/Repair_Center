document.querySelectorAll('[data-record-form]').forEach(form => {
  let changed = false;
  form.addEventListener('input', () => { changed = true; });
  form.addEventListener('change', () => { changed = true; });
  form.addEventListener('submit', () => { changed = false; });
  window.addEventListener('beforeunload', event => {
    if (changed) { event.preventDefault(); event.returnValue = ''; }
  });
  const firstError = form.querySelector('.field-invalid input, .field-invalid select, .field-invalid textarea');
  if (firstError) firstError.focus();
});

document.querySelectorAll('[data-password-toggle]').forEach(button => {
  button.addEventListener('click', () => {
    const input = button.closest('.password-control')?.querySelector('input');
    if (!input) return;
    const visible = input.type === 'text';
    input.type = visible ? 'password' : 'text';
    button.textContent = visible ? 'Показать' : 'Скрыть';
    button.setAttribute('aria-label', visible ? 'Показать пароль' : 'Скрыть пароль');
    button.setAttribute('aria-pressed', String(!visible));
  });
});

document.querySelectorAll('[data-row-href]').forEach(row => {
  const open = event => {
    if (event.target.closest('a, button, input, select, textarea')) return;
    window.location.assign(row.dataset.rowHref);
  };
  row.addEventListener('click', open);
  row.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      open(event);
    }
  });
});

document.querySelectorAll('[data-tab-group]').forEach(group => {
  const buttons = [...group.querySelectorAll('[data-tab-target]')];
  const panels = [...group.querySelectorAll('[data-tab-panel]')];
  const activate = id => {
    buttons.forEach(button => {
      const active = button.dataset.tabTarget === id;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', String(active));
    });
    panels.forEach(panel => { panel.hidden = panel.dataset.tabPanel !== id; });
  };
  buttons.forEach(button => button.addEventListener('click', () => activate(button.dataset.tabTarget)));
  const invalidPanel = panels.find(panel => panel.querySelector('.field-invalid, .field-error'));
  if (invalidPanel) activate(invalidPanel.dataset.tabPanel);
});

document.querySelectorAll('[data-equipment-form]').forEach(form => {
  const typeSelect = form.querySelector('#id_equipment_type');
  const modelSelect = form.querySelector('#id_equipment_model');
  if (!typeSelect || !modelSelect) return;
  const syncModels = () => {
    const typeId = typeSelect.value;
    let selectedAvailable = false;
    [...modelSelect.options].forEach(option => {
      if (!option.value) return;
      const available = !typeId || option.dataset.equipmentType === typeId;
      option.hidden = !available;
      option.disabled = !available;
      if (option.selected && available) selectedAvailable = true;
    });
    if (modelSelect.value && !selectedAvailable) modelSelect.value = '';
  };
  typeSelect.addEventListener('change', syncModels);
  syncModels();
});
