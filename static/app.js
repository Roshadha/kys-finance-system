document.addEventListener('DOMContentLoaded', () => {
  const menu = document.getElementById('menuButton');
  const sidebar = document.getElementById('sidebar');
  if (menu && sidebar) menu.addEventListener('click', () => sidebar.classList.toggle('open'));

  const amounts = ['subtotal', 'sscl', 'vat'].map(id => document.getElementById(id)).filter(Boolean);
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
    updateVehicle();
  };
  const vehicle = document.getElementById('vehicleField');
  const updateVehicle = () => {
    if (!category || !vehicle) return;
    const option = category.options[category.selectedIndex];
    vehicle.classList.toggle('visible', option && option.dataset.vehicle === '1');
  };
  if (category) category.addEventListener('change', updateVehicle);
  if (transactionGroup) transactionGroup.addEventListener('change', updateAccounts);
  if (transactionGroup) updateAccounts(); else updateVehicle();

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

  const role = document.getElementById('roleSelect');
  const tasks = document.getElementById('taskFieldset');
  const updateTasks = () => { if (role && tasks) tasks.hidden = role.value === 'admin'; };
  if (role) role.addEventListener('change', updateTasks);
  updateTasks();

  document.querySelectorAll('.flash').forEach((el) => setTimeout(() => el.remove(), 6000));
});
