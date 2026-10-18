document.addEventListener('DOMContentLoaded', () => {
  const entryForm = document.getElementById('transactionForm');
  if (entryForm && entryForm.dataset.periodUrl) {
    const month = entryForm.elements.month_number;
    const year = entryForm.elements.year;
    const status = document.getElementById('entryPeriodStatus');
    let periodQueue = Promise.resolve();
    let selectionVersion = 0;
    const saveEntryPeriod = () => {
      const version = ++selectionVersion;
      const data = new URLSearchParams({month_number: month.value, year: year.value,
        csrf_token: entryForm.elements.csrf_token.value});
      status.textContent = 'Remembering your selection…';
      periodQueue = periodQueue.catch(() => {}).then(async () => {
        try {
          const response = await fetch(entryForm.dataset.periodUrl, {method: 'POST', body: data,
            credentials: 'same-origin', keepalive: true});
          if (!response.ok || response.redirected) throw new Error('Not saved');
          if (version === selectionVersion) status.textContent = 'Month and year saved. They stay selected until you change them.';
        } catch (_) {
          if (version === selectionVersion) status.textContent = 'Could not remember this selection. Select it again to retry, or save your entry to remember it.';
        }
      });
    };
    month.addEventListener('change', saveEntryPeriod);
    year.addEventListener('change', saveEntryPeriod);
  }
  const deleteModal = document.getElementById('deleteEntryModal');
  const deleteForm = document.getElementById('deleteEntryForm');
  const deleteSubmit = document.getElementById('deleteEntrySubmit');
  let deleteTrigger = null;
  let deletionPending = false;
  const modalBackground = [];
  const closeDeleteModal = () => {
    if (!deleteModal || deletionPending) return;
    deleteModal.hidden = true;
    document.body.classList.remove('confirmation-open');
    modalBackground.forEach(([el, previous]) => {
      if (previous === null) el.removeAttribute('aria-hidden');
      else el.setAttribute('aria-hidden', previous);
    });
    modalBackground.length = 0;
    if (deleteTrigger) deleteTrigger.focus();
  };
  document.querySelectorAll('[data-confirm-delete]').forEach(link => {
    link.addEventListener('click', event => {
      if (!deleteModal || !deleteForm) return; // Keep the confirmation-page fallback.
      event.preventDefault();
      deleteTrigger = link;
      deleteForm.action = link.href;
      document.getElementById('deleteEntrySummary').textContent = link.dataset.entrySummary;
      deleteModal.hidden = false;
      document.body.classList.add('confirmation-open');
      document.getElementById('deleteEntryCancel').focus();
      document.querySelectorAll('.sidebar, .app-shell').forEach(el => {
        modalBackground.push([el, el.getAttribute('aria-hidden')]);
        el.setAttribute('aria-hidden', 'true');
      });
    });
  });
  if (deleteModal) {
    deleteModal.querySelectorAll('[data-dismiss-delete]').forEach(button => button.addEventListener('click', closeDeleteModal));
    deleteModal.addEventListener('click', event => { if (event.target === deleteModal) closeDeleteModal(); });
    document.addEventListener('keydown', event => {
      if (deleteModal.hidden) return;
      if (event.key === 'Escape') { event.preventDefault(); closeDeleteModal(); }
      if (event.key === 'Tab') {
        const buttons = Array.from(deleteModal.querySelectorAll('button:not([disabled])'));
        const first = buttons[0], last = buttons[buttons.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    });
    deleteForm.addEventListener('submit', event => {
      if (deletionPending) { event.preventDefault(); return; }
      deletionPending = true;
      deleteSubmit.disabled = true;
      deleteSubmit.textContent = 'Deleting…';
    });
    window.addEventListener('pageshow', () => {
      deletionPending = false;
      deleteSubmit.disabled = false;
      deleteSubmit.textContent = 'Yes, delete entry';
      closeDeleteModal();
    });
  }
  const menu = document.getElementById('menuButton');
  const sidebar = document.getElementById('sidebar');
  if (menu && sidebar) menu.addEventListener('click', () => sidebar.classList.toggle('open'));

  const amounts = ['subtotal'].map(id => document.getElementById(id)).filter(Boolean);
  const total = document.getElementById('grandTotal');
  const updateTotal = () => {
    if (!total) return;
    const value = amounts.reduce((sum, input) => sum + (Number.parseFloat(input.value.replaceAll(',', '')) || 0), 0);
    total.value = value.toLocaleString('en-LK', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };
  amounts.forEach(input => input.addEventListener('input', () => {
    const before = input.value.slice(0, input.selectionStart || 0).replace(/[^\d.]/g, '').length;
    const cleaned = input.value.replace(/[^\d.]/g, '');
    const dot = cleaned.indexOf('.');
    const integer = (dot < 0 ? cleaned : cleaned.slice(0, dot)).replace(/^0+(?=\d)/, '');
    const decimal = dot < 0 ? '' : '.' + cleaned.slice(dot + 1).replace(/\./g, '').slice(0, 2);
    input.value = (integer ? integer.replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '') + decimal;
    let position = 0;
    let counted = 0;
    while (position < input.value.length && counted < before) {
      if (/[\d.]/.test(input.value[position])) counted++;
      position++;
    }
    input.setSelectionRange(position, position);
    updateTotal();
  }));
  updateTotal();

  const category = document.getElementById('categorySelect');
  const transactionGroup = document.getElementById('transactionGroupSelect');
  const accountOptions = category ? Array.from(category.options).slice(1).map(option => option.cloneNode(true)) : [];
  const updateAccounts = () => {
    if (!category || !transactionGroup) return;
    const previous = category.value;
    category.replaceChildren(new Option(transactionGroup.value ? 'Select an account' : 'Select a group first', ''));
    accountOptions.filter(option => option.dataset.group === transactionGroup.value).forEach(option => category.add(option.cloneNode(true)));
    if (Array.from(category.options).some(option => option.value === previous)) category.value = previous;
    if (transactionGroup.value && category.value && !Array.from(category.options).some(option => option.value === category.value)) category.value = '';
  };
  if (transactionGroup) transactionGroup.addEventListener('change', updateAccounts);
  if (transactionGroup) updateAccounts();

  const kind = document.getElementById('kindSelect');
  const group = document.getElementById('groupSelect');
  const updateGroups = () => {
    if (!kind || !group) return;
    Array.from(group.options).forEach((option) => {
      if (!option.value) return;
      option.hidden = option.dataset.kind !== kind.value;
    });
    const selected = group.options[group.selectedIndex];
    if (selected && selected.value && selected.hidden) group.value = '';
  };
  if (kind) kind.addEventListener('change', updateGroups);
  updateGroups();

  const bindCodePrefix = (formId, prefixes, newItem) => {
    const form = document.getElementById(formId);
    if (!form) return;
    const type = form.elements.kind;
    const code = form.elements.code;
    const prefix = value => prefixes[value];
    let previousPrefix = prefix(type.value);
    if (newItem && !code.value.trim()) code.value = previousPrefix + '0';
    type.addEventListener('change', () => {
      const nextPrefix = prefix(type.value);
      const current = code.value.trim().toUpperCase();
      if (!current || current === previousPrefix || current === previousPrefix + '0') {
        code.value = nextPrefix + '0';
      } else if (current.startsWith(previousPrefix)) {
        code.value = nextPrefix + current.slice(previousPrefix.length);
      }
      previousPrefix = nextPrefix;
    });
  };
  bindCodePrefix('groupCreateForm', {income: 'IG_', expense: 'EG_'}, true);
  bindCodePrefix('groupEditForm', {income: 'IG_', expense: 'EG_'}, false);
  bindCodePrefix('categoryCreateForm', {income: 'IP_', expense: 'EP_'}, true);

  const role = document.getElementById('roleSelect');
  const tasks = document.getElementById('taskFieldset');
  const updateTasks = () => { if (role && tasks) tasks.hidden = role.value === 'admin'; };
  if (role) role.addEventListener('change', updateTasks);
  updateTasks();

  document.querySelectorAll('.flash').forEach((el) => setTimeout(() => el.remove(), 6000));
});
