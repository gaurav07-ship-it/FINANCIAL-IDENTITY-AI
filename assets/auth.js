/* ============================================================
   FIA AUTH — login / register / logout + protected-page guard.

   Pair with assets/api.js (loaded before this file).
   Public surface (window.Auth):
     Auth.login(form)
     Auth.register(form)
     Auth.logout()
     Auth.guard()              - call from protected pages; bounces to login.html
                                 if the API says the user isn't authenticated
     Auth.notify(level, msg)   - tiny inline banner, no toast lib
   ============================================================ */

(function () {
  const PUBLIC_PAGES = new Set(['login.html', 'landing.html', 'index.html']);

  function here() {
    const p = location.pathname.split('/').pop() || '';
    return p || 'index.html';
  }

  function nextUrl() {
    const n = new URL(location.href).searchParams.get('next');
    return n || 'dashboard.html';
  }

  /* ── notifications ──────────────────────────────────────────────── */
  function ensureBanner() {
    let el = document.getElementById('fia-banner');
    if (el) return el;
    el = document.createElement('div');
    el.id = 'fia-banner';
    el.style.cssText = [
      'position:fixed', 'top:16px', 'left:50%', 'transform:translateX(-50%)',
      'z-index:9999', 'padding:10px 16px', 'border-radius:10px',
      'font:600 0.85rem/1.4 Inter,system-ui,sans-serif',
      'box-shadow:0 6px 24px rgba(0,0,0,.18)',
      'display:none', 'max-width:480px', 'text-align:center',
    ].join(';');
    document.body.appendChild(el);
    return el;
  }
  function notify(level, msg, ttl = 4000) {
    const el = ensureBanner();
    const colors = {
      error: { bg: '#FEF2F2', fg: '#B91C1C', bd: '#FCA5A5' },
      warn:  { bg: '#FFFBEB', fg: '#92400E', bd: '#FCD34D' },
      info:  { bg: '#EFF6FF', fg: '#1E3A8A', bd: '#BFDBFE' },
      ok:    { bg: '#ECFDF5', fg: '#065F46', bd: '#A7F3D0' },
    };
    const c = colors[level] || colors.info;
    el.style.background = c.bg;
    el.style.color = c.fg;
    el.style.border = '1px solid ' + c.bd;
    el.textContent = msg;
    el.style.display = 'block';
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.style.display = 'none'; }, ttl);
  }

  /* ── auth actions ───────────────────────────────────────────────── */
  async function login(form) {
    if (form && form.tagName === 'FORM') form.preventDefault && form.preventDefault();
    const email = readField(form, ['email', '#loginEmail', '[name="email"]']) || 'arjun@joshi.studio';
    const password = readField(form, ['password', '#loginPass', '[name="password"]']) || 'Arjun@2026';
    try {
      await API.login(email, password);
      notify('ok', 'Signed in');
      setTimeout(() => { location.href = nextUrl(); }, 200);
    } catch (e) {
      const msg = e && e.detail ? e.detail : (e && e.message) || 'Login failed';
      notify('error', typeof msg === 'string' ? msg : 'Login failed');
    }
  }

  async function register(form) {
    if (form && form.tagName === 'FORM') form.preventDefault && form.preventDefault();
    const name = readField(form, ['[name="name"]', '#regName']) || 'New User';
    const email = readField(form, ['email', '#regEmail', '[name="email"]']);
    const password = readField(form, ['password', '#regPass', '[name="password"]']);
    if (!email || !password) {
      notify('error', 'Email and password required');
      return;
    }
    try {
      await API.register(name, email, password);
      notify('ok', 'Account created');
      setTimeout(() => { location.href = 'onboarding.html'; }, 200);
    } catch (e) {
      const msg = e && e.detail ? e.detail : (e && e.message) || 'Sign-up failed';
      notify('error', typeof msg === 'string' ? msg : 'Sign-up failed');
    }
  }

  async function logout() {
    try { await STORE.reset(); } finally { location.href = 'login.html'; }
  }

  /* ── protected-page guard ───────────────────────────────────────── */
  async function guard() {
    if (PUBLIC_PAGES.has(here())) return true;
    try {
      await API.me();
      return true;
    } catch (e) {
      const target = 'login.html?next=' + encodeURIComponent(here());
      location.replace(target);
      return false;
    }
  }

  /* ── DOM helpers ─────────────────────────────────────────────────── */
  function readField(scope, selectors) {
    if (!scope) return null;
    const root = scope.tagName === 'FORM' ? scope : document;
    for (const sel of selectors) {
      const el = root.querySelector(sel);
      if (el && el.value) return el.value.trim();
    }
    return null;
  }

  window.Auth = { login, register, logout, guard, notify };
})();