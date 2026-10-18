document.addEventListener('DOMContentLoaded', () => {
  const panel = document.getElementById('liveUpdates');
  if (!panel) return;
  const status = document.getElementById('liveUpdateStatus');
  const refresh = document.getElementById('liveUpdateNow');
  const storageKey = 'kys-live-view:' + location.pathname + location.search;
  let dirty = false;
  let pending = false;
  let busy = false;
  let stopped = false;
  let submitting = false;
  let etag = '';
  let failures = 0;
  let timer;
  const schedule = () => {
    clearTimeout(timer);
    if (!stopped) timer = setTimeout(poll, Math.min(60000, 5000 * Math.pow(2, failures)) + Math.random() * 1000);
  };
  const reload = () => {
    try {
      sessionStorage.setItem(storageKey, JSON.stringify({scroll: window.scrollY,
        details: Array.from(document.querySelectorAll('details')).map(element => element.open)}));
    } catch (_) {}
    location.reload();
  };
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey));
    sessionStorage.removeItem(storageKey);
    if (saved) {
      document.querySelectorAll('details').forEach((element, index) => { element.open = !!saved.details[index]; });
      window.scrollTo(0, saved.scroll);
    }
  } catch (_) {}
  document.querySelectorAll('main form').forEach(form => {
    form.addEventListener('input', () => { dirty = true; });
    form.addEventListener('change', () => { dirty = true; });
  });
  document.addEventListener('submit', () => { submitting = true; });
  refresh.addEventListener('click', () => {
    if (dirty) {
      status.textContent = 'Unsaved selections are present. Apply or reset them before refreshing.';
      return;
    }
    reload();
  });
  const unsafeToReload = () => dirty || submitting || document.body.classList.contains('confirmation-open') ||
    (document.activeElement && document.activeElement.matches('input, select, textarea'));
  const poll = async () => {
    if (busy || stopped) return;
    if (document.hidden) { schedule(); return; }
    busy = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch(panel.dataset.url, {credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
        headers: etag ? {'If-None-Match': etag} : {}});
      if (response.status === 304) {
        failures = 0;
        if (pending && !unsafeToReload()) reload();
        return;
      }
      if (response.status === 401) {
        stopped = true;
        status.textContent = 'Session ended. Reload to sign in.';
        refresh.hidden = false;
        return;
      }
      if (!response.ok || response.redirected) throw new Error('Unavailable');
      const data = await response.json();
      if (typeof data.version !== 'string') throw new Error('Invalid response');
      etag = response.headers.get('ETag') || '';
      failures = 0;
      pending = data.version !== panel.dataset.version;
      if (pending && !unsafeToReload()) { reload(); return; }
      status.textContent = pending ? 'New data available. Finish your selection or show latest data.' : 'Auto-update on · checks every 5 seconds';
      refresh.hidden = !pending;
    } catch (_) {
      failures = Math.min(failures + 1, 4);
      status.textContent = 'Connection interrupted · retrying automatically';
    } finally {
      clearTimeout(timeout);
      busy = false;
      schedule();
    }
  };
  schedule();
  document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });
  window.addEventListener('online', poll);
});
