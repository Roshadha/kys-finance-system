(() => {
  const storageKey = 'kys-finance-theme';
  let selected = 'light';
  try {
    if (window.localStorage.getItem(storageKey) === 'dark') selected = 'dark';
  } catch (_) {
    // Private browsing can disable storage; the switch still works for this page.
  }
  document.documentElement.dataset.theme = selected;

  document.addEventListener('DOMContentLoaded', () => {
    const button = document.getElementById('themeSwitch');
    if (!button) return;
    const render = () => {
      const dark = document.documentElement.dataset.theme === 'dark';
      button.setAttribute('aria-pressed', String(dark));
      button.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
      button.querySelectorAll('span')[0].textContent = dark ? '☀' : '☾';
      button.querySelectorAll('span')[1].textContent = dark ? 'Light' : 'Dark';
    };
    button.addEventListener('click', () => {
      const dark = document.documentElement.dataset.theme !== 'dark';
      document.documentElement.dataset.theme = dark ? 'dark' : 'light';
      try { window.localStorage.setItem(storageKey, dark ? 'dark' : 'light'); } catch (_) {}
      render();
    });
    render();
  });
})();
