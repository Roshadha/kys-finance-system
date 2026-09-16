document.addEventListener('DOMContentLoaded', () => {
  const menu = document.getElementById('menuButton');
  const sidebar = document.getElementById('sidebar');
  if (menu && sidebar) menu.addEventListener('click', () => sidebar.classList.toggle('open'));

  const amounts = ['subtotal', 'sscl', 'vat'].map(id => document.getElementById(id)).filter(Boolean);
  const total = document.getElementById('grandTotal');
  const updateTotal = () => {
    if (!total) return;
    const value = amounts.reduce((sum, input) => sum + (Number.parseFloat(input.value) || 0), 0);
    total.value = value.toLocaleString('en-LK', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };
  amounts.forEach(input => input.addEventListener('input', updateTotal));
  updateTotal();

  const category = document.getElementById('categorySelect');
  const vehicle = document.getElementById('vehicleField');
  const updateVehicle = () => {
    if (!category || !vehicle) return;
    const option = category.options[category.selectedIndex];
    vehicle.classList.toggle('visible', option && option.dataset.vehicle === '1');
  };
  if (category) category.addEventListener('change', updateVehicle);
  updateVehicle();

  const role = document.getElementById('roleSelect');
  const tasks = document.getElementById('taskFieldset');
  const updateTasks = () => { if (role && tasks) tasks.hidden = role.value === 'admin'; };
  if (role) role.addEventListener('change', updateTasks);
  updateTasks();

  document.querySelectorAll('.flash').forEach((el) => setTimeout(() => el.remove(), 6000));
});
