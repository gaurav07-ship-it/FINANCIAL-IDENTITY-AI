/* ============================================================
   SHARED SHELL — inject sidebar + topbar into auth pages
   Drop <div id="shell"></div> on the page and include this script.

   This script can be loaded anywhere in the body. It defers the
   actual shell injection until DOMContentLoaded so the page content
   (which lives as siblings of #shell, not inside it) is fully
   parsed and we can lift it into the new #content wrapper.
   ============================================================ */

(function () {
  const run = () => {
  const shell = document.getElementById('shell');
  if (!shell) return;

  const here = location.pathname.split('/').pop();
  const PAGE = window.FIA_PAGE || {};

  const links = [
    { group: 'Overview', items: [
      { href: 'dashboard.html', label: 'Dashboard', icon: 'gauge' },
      { href: 'financial-dna.html', label: 'Financial DNA', icon: 'fingerprint' },
      { href: 'financial-twin.html', label: 'Financial Twin', icon: 'bot', badge: 'AI' },
    ]},
    { group: 'Insights', items: [
      { href: 'loan-eligibility.html', label: 'Loan Eligibility', icon: 'banknote' },
      { href: 'client-dependency.html', label: 'Client Dependency', icon: 'network' },
      { href: 'income-quality.html', label: 'Income Quality', icon: 'trending-up' },
      { href: 'emergency-score.html', label: 'Emergency Score', icon: 'shield' },
      { href: 'opportunity-engine.html', label: 'Opportunities', icon: 'sparkles' },
    ]},
    { group: 'Account', items: [
      { href: 'settings.html', label: 'Settings', icon: 'settings' },
      { href: 'admin.html', label: 'Admin Panel', icon: 'lock' },
    ]},
  ];

  const icons = {
    gauge: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 14l4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/></svg>',
    fingerprint: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 11v4a1 1 0 0 0 1 1h1"/><path d="M14 9a2 2 0 0 0-4 0v6"/><path d="M6 12a6 6 0 1 1 12 0v2a4 4 0 0 1-4 4h-1"/><path d="M9 16v-2.5a3 3 0 0 1 6 0V16"/><path d="M12 5a7 7 0 0 1 7 7v3a5 5 0 0 1-5 5h-1"/></svg>',
    bot: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>',
    banknote: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="12" x="2" y="6" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/></svg>',
    network: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><circle cx="4" cy="4" r="2"/><circle cx="20" cy="4" r="2"/><circle cx="4" cy="20" r="2"/><circle cx="20" cy="20" r="2"/><path d="M9.7 9.7 5.4 5.4M14.3 9.7l4.3-4.3M9.7 14.3l-4.3 4.3M14.3 14.3l4.3 4.3"/></svg>',
    'trending-up': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>',
    shield: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    sparkles: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z"/></svg>',
    settings: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    lock: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
    chevLeft: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>',
    chevRight: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>',
    search: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
    bell: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>',
    sun: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>',
    moon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
    command: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0-3-3H6a3 3 0 0 0-3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 3 3 0 0 0-3-3z"/></svg>',
  };

  const sidebarHTML = `
    <aside class="sidebar">
      <a href="landing.html" class="brand">
        <span class="brand-mark">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L4 7l8 5 8-5-8-5z"/><path d="M4 17l8 5 8-5M4 12l8 5 8-5"/></svg>
        </span>
        <span class="brand-name">Financial Identity AI</span>
      </a>
      <nav>
        ${links.map(g => `
          <div class="group-title label">${g.group}</div>
          ${g.items.map(i => `
            <a href="${i.href}" class="nav-link" data-nav="${i.href}">
              ${icons[i.icon] || ''}
              <span class="label">${i.label}</span>
              ${i.badge ? `<span class="badge" style="margin-left:auto">${i.badge}</span>` : ''}
            </a>
          `).join('')}
        `).join('')}
      </nav>
      <div class="footer">
        <div class="avatar">AJ</div>
        <div class="user-meta">
          <div class="name">Arjun Joshi</div>
          <div class="role">Freelance Designer · Pro</div>
        </div>
      </div>
    </aside>
  `;

  const title = PAGE.title || 'Dashboard';
  const sub = PAGE.sub || '';

  const topbarHTML = `
    <header class="topbar">
      <button class="btn icon ghost" data-toggle-sidebar title="Toggle sidebar">
        ${icons.chevLeft}
      </button>
      <span class="crumbs">${PAGE.crumbs || title}</span>
      <h1>${title}</h1>
      <div class="right">
        <div class="search" data-command-open style="cursor:pointer;max-width:300px">
          ${icons.search}
          <span>Search anything…</span>
          <kbd style="margin-left:auto;font-size:0.7rem;padding:1px 6px;background:var(--surface-2);border-radius:6px;border:1px solid var(--border);color:var(--muted)">⌘K</kbd>
        </div>
        <button class="btn icon ghost" data-theme-toggle title="Toggle theme">
          ${icons.sun}${icons.moon}
        </button>
        <button class="bell">${icons.bell}<span class="dot"></span></button>
        <div class="user-menu" style="position:relative">
          <button class="avatar" data-user-menu title="Profile" style="cursor:pointer;border:0;padding:0;background:transparent;color:inherit;font:inherit">AJ</button>
          <div data-user-menu-pop style="display:none;position:absolute;top:calc(100% + 8px);right:0;background:var(--surface);border:1px solid var(--border);border-radius:12px;box-shadow:var(--shadow-lg);min-width:180px;padding:6px;z-index:50">
            <a href="settings.html" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;color:var(--text);text-decoration:none">Settings</a>
            <button type="button" data-sign-out style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;width:100%;text-align:left;background:transparent;border:0;color:var(--text);font:inherit;cursor:pointer">Sign out</button>
          </div>
        </div>
      </div>
    </header>
  `;

  const commandHTML = `
    <div data-command style="display:none;position:fixed;inset:0;background:rgba(15,23,42,0.4);backdrop-filter:blur(6px);z-index:999;place-items:start center;padding-top:14vh">
      <div class="card" style="width:min(640px,92vw);padding:0;background:var(--surface);box-shadow:var(--shadow-xl)">
        <div class="input-group" style="padding:14px 18px;border-bottom:1px solid var(--border)">
          <div class="lead" style="color:var(--muted)">${icons.search}</div>
          <input class="input" data-command-input placeholder="Search pages, insights, settings…" style="padding-left:36px;background:transparent;border:0;font-size:1rem" />
        </div>
        <div style="padding:14px 12px;max-height:50vh;overflow:auto" class="no-bar">
          ${links.flatMap(g => g.items).map(i => `
            <div data-cmd-item data-href="${i.href}" style="padding:10px 14px;border-radius:8px;cursor:pointer;display:flex;align-items:center;gap:10px">
              <span style="color:var(--muted)">${icons[i.icon] || ''}</span>
              <span style="font-weight:500">${i.label}</span>
            </div>
          `).join('')}
        </div>
        <div style="padding:10px 18px;border-top:1px solid var(--border);font-size:0.75rem;color:var(--muted);display:flex;gap:14px">
          <span><kbd style="padding:1px 6px;background:var(--surface-2);border-radius:6px">↑↓</kbd> Navigate</span>
          <span><kbd style="padding:1px 6px;background:var(--surface-2);border-radius:6px">↵</kbd> Open</span>
          <span><kbd style="padding:1px 6px;background:var(--surface-2);border-radius:6px">Esc</kbd> Close</span>
        </div>
      </div>
    </div>
  `;

  const assistantHTML = `
    <button class="assistant-fab" onclick="alert('AI Assistant (demo)')" title="Ask AI">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
    </button>
    <nav class="bottom-nav">
      <a href="dashboard.html">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 14l4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/></svg>
        <span>Home</span>
      </a>
      <a href="financial-dna.html">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 11v4a1 1 0 0 0 1 1h1"/><path d="M14 9a2 2 0 0 0-4 0v6"/></svg>
        <span>DNA</span>
      </a>
      <a href="financial-twin.html">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/></svg>
        <span>Twin</span>
      </a>
      <a href="opportunity-engine.html">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.9 5.8"/></svg>
        <span>More</span>
      </a>
      <a href="settings.html">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/><circle cx="12" cy="12" r="10"/></svg>
        <span>Profile</span>
      </a>
    </nav>
  `;

  /* Capture siblings of #shell that should be moved into the new content area.
     The page body looks like:
       <div id="shell"></div>          ← anchor
       <script>...</script>
       <div>... actual page content ...</div>
     We want the page content to land inside the new #content div that
     shell.outerHTML creates, otherwise the body becomes a 2-row layout
     (wrapper + orphan content) and the sidebar/topbar can't see the content. */
  const shellParent = shell.parentNode;
  const siblingsToMove = [];
  let n = shell.nextSibling;
  while (n) {
    const next = n.nextSibling;
    /* Keep script tags where they are — they need to keep running in body. */
    if (n.tagName !== 'SCRIPT') siblingsToMove.push(n);
    n = next;
  }

  /* Move children of shell into the new content BEFORE replacing */
  const innerChildren = [...shell.children];
  shell.outerHTML = `
    <div class="app page-in">
      ${sidebarHTML}
      <div class="main">
        ${topbarHTML}
        <main class="content" id="content"></main>
      </div>
      ${assistantHTML}
      ${commandHTML}
    </div>
  `;

  /* Now move children into the new content area */
  const content = document.getElementById('content');
  innerChildren.forEach(ch => content.appendChild(ch));
  siblingsToMove.forEach(ch => content.appendChild(ch));

  /* Mark active nav link + bottom-nav item for the current page */
  document.querySelectorAll('.nav-link[data-nav]').forEach(a => {
    if (a.dataset.nav === here) a.classList.add('active');
  });
  document.querySelectorAll('.bottom-nav a').forEach(a => {
    const href = a.getAttribute('href') || '';
    if (href === here) a.classList.add('active');
  });

  /* Hydrate sidebar user info + avatar from STORE if present */
  if (window.STORE && STORE.isOnboarded && STORE.isOnboarded()) {
    const s = STORE.get();
    const name = (s.personal.name || '').trim();
    const initials = name ? name.split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase() : 'AJ';
    document.querySelectorAll('.sidebar .avatar, .topbar .avatar').forEach(el => {
      el.textContent = initials || 'AJ';
      if (el.tagName !== 'A') el.removeAttribute('href');
    });
    const nameEl = document.querySelector('.sidebar .user-meta .name');
    if (nameEl) nameEl.textContent = name || '—';
    const roleEl = document.querySelector('.sidebar .user-meta .role');
    if (roleEl) {
      const occ = s.occupation || '';
      roleEl.textContent = occ ? `${occ} · Pro` : 'Pro';
    }
  }

  /* ── user menu + sign-out (depends on api.js + auth.js) ── */
  function wireUserMenu() {
    const trigger = document.querySelector('[data-user-menu]');
    const pop = document.querySelector('[data-user-menu-pop]');
    const signOut = document.querySelector('[data-sign-out]');
    if (!trigger || !pop) return;
    const close = () => { pop.style.display = 'none'; };
    const open = () => { pop.style.display = 'block'; };
    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      pop.style.display === 'block' ? close() : open();
    });
    document.addEventListener('click', (e) => {
      if (!pop.contains(e.target)) close();
    });
    if (signOut) signOut.addEventListener('click', () => {
      close();
      if (window.Auth && Auth.logout) Auth.logout();
      else location.href = 'login.html';
    });
  }
  wireUserMenu();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
