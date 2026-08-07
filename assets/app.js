/* ============================================================
   FINANCIAL IDENTITY AI — Application Logic
   Charts (custom SVG), sidebar, theme, command palette, etc.
   ============================================================ */

const APP = (() => {
  /* -------------------------------- Helpers ------------------------------ */
  const $ = (s, p = document) => p.querySelector(s);
  const $$ = (s, p = document) => [...p.querySelectorAll(s)];
  const fmt = {
    n: (v, d = 0) => Number(v).toLocaleString('en-IN', { maximumFractionDigits: d, minimumFractionDigits: d }),
    money: v => '₹' + Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 }),
    short: v => {
      const n = Number(v);
      if (Math.abs(n) >= 1e7) return '₹' + (n / 1e7).toFixed(1) + 'Cr';
      if (Math.abs(n) >= 1e5) return '₹' + (n / 1e5).toFixed(1) + 'L';
      if (Math.abs(n) >= 1e3) return '₹' + (n / 1e3).toFixed(1) + 'k';
      return '₹' + n;
    },
    pct: v => (Number(v) >= 0 ? '+' : '') + Number(v).toFixed(1) + '%',
  };

  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const palette = () => ({
    accent: css('--accent') || '#2563EB',
    accent2: css('--accent-2') || '#3B82F6',
    accent3: css('--accent-3') || '#60A5FA',
    success: css('--success') || '#22C55E',
    warning: css('--warning') || '#F59E0B',
    danger: css('--danger') || '#EF4444',
    violet: css('--violet') || '#8B5CF6',
    pink: css('--pink') || '#EC4899',
    teal: css('--teal') || '#14B8A6',
    text: css('--text') || '#0F172A',
    muted: css('--muted') || '#64748B',
    border: css('--border') || '#E2E8F0',
    surface: css('--surface') || '#FFFFFF',
  });

  /* ------------------------------ Sidebar ------------------------------- */
  const initSidebar = () => {
    const sidebar = $('.sidebar');
    if (!sidebar) return;
    const toggle = $('[data-toggle-sidebar]');
    if (toggle) {
      toggle.addEventListener('click', () => {
        $('.app')?.classList.toggle('collapsed');
        document.cookie = "fia_sidebar=collapsed; path=/; max-age=" + 60 * 60 * 24 * 30;
        window.dispatchEvent(new Event('resize'));
      });
    }
    if (document.cookie.includes('fia_sidebar=collapsed')) {
      $('.app')?.classList.add('collapsed');
    }
    /* Active link highlighting based on URL */
    const here = location.pathname.split('/').pop();
    $$('.nav-link').forEach(a => {
      const href = a.getAttribute('href');
      if (href === here || (here === 'index.html' && href === 'landing.html')) {
        a.classList.add('active');
      }
    });
  };

  /* ------------------------------- Theme -------------------------------- */
  const initTheme = () => {
    const saved = localStorage.getItem('fia_theme') || 'light';
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
    $$('[data-theme-toggle]').forEach(btn => {
      btn.addEventListener('click', () => {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        if (isDark) document.documentElement.removeAttribute('data-theme');
        else document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('fia_theme', isDark ? 'light' : 'dark');
        document.dispatchEvent(new Event('themechange'));
      });
    });
  };

  /* ------------------------------ Charts -------------------------------- */
  const W = 700, H = 240, P = 36;

  function makeSVG(ns, children = '') {
    return `<svg xmlns="${ns}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${children}</svg>`;
  }

  /* Animated line chart */
  function lineChart(data, opts = {}) {
    const { color = 'var(--accent)', area = true, height = 240, yLabel = '', yPrefix = '', smooth = true, second = null, xLabels = null } = opts;
    const max = Math.max(...data, ...(second ? second.data : [])) * 1.15;
    const min = 0;
    const range = max - min || 1;
    const xStep = (W - P * 2) / (data.length - 1);
    const pts = data.map((v, i) => [P + i * xStep, H - P - ((v - min) / range) * (H - P * 2)]);
    const path = smooth ? smoothPath(pts) : pts.map((p, i) => (i ? 'L' : 'M') + p[0] + ',' + p[1]).join(' ');
    const areaPath = `${path} L ${pts[pts.length - 1][0]},${H - P} L ${pts[0][0]},${H - P} Z`;
    const id1 = 'grad-' + Math.random().toString(36).slice(2, 7);
    const id2 = 'grad2-' + Math.random().toString(36).slice(2, 7);

    let secondPath = '';
    if (second) {
      const sps = second.data.map((v, i) => [P + i * xStep, H - P - ((v - min) / range) * (H - P * 2)]);
      const p2 = smoothPath(sps);
      secondPath = `
        <path d="${p2}" stroke="${second.color || 'var(--violet)'}" stroke-width="2.5" fill="none" stroke-dasharray="4 4" stroke-linecap="round" />
        ${(second.data.map((v, i) => `<circle cx="${sps[i][0]}" cy="${sps[i][1]}" r="2.5" fill="${second.color || 'var(--violet)'}" />`)).join('')}
      `;
    }

    const dots = pts.map((p, i) => `<g class="dot-grp"><circle class="dot" cx="${p[0]}" cy="${p[1]}" r="3" fill="${color}" stroke="var(--surface)" stroke-width="2"><title>${data[i].toLocaleString()}</title></circle></g>`).join('');

    const xA = xLabels || data.map((_, i) => '');
    const xAxis = xA.map((l, i) => l ? `<text x="${P + i * xStep}" y="${H - 10}" text-anchor="middle" class="axis-label">${l}</text>` : '').join('');
    const yAxis = [0, 0.25, 0.5, 0.75, 1].map(t => {
      const y = H - P - t * (H - P * 2);
      const v = min + t * range;
      return `<line class="grid-line" x1="${P}" x2="${W - P}" y1="${y}" y2="${y}" /><text class="axis-label" x="${P - 6}" y="${y + 3}" text-anchor="end">${yPrefix ? yPrefix + Math.round(v).toLocaleString() : Math.round(v)}</text>`;
    }).join('');

    return `
      <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="height:${height}px">
        <defs>
          <linearGradient id="${id1}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${color}" stop-opacity="0.28"/>
            <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
          </linearGradient>
          <linearGradient id="${id2}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${color}" stop-opacity="0.05"/>
            <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
          </linearGradient>
        </defs>
        ${yAxis}
        ${area ? `<path d="${areaPath}" fill="url(#${id1})" />` : ''}
        <path d="${path}" stroke="${color}" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" pathLength="1000" stroke-dasharray="1000" stroke-dashoffset="1000">
          <animate attributeName="stroke-dashoffset" from="1000" to="0" dur="1.4s" fill="freeze" />
        </path>
        ${secondPath}
        ${dots}
        ${xAxis}
      </svg>
    `;
  }

  function smoothPath(pts) {
    if (pts.length < 2) return '';
    return pts.reduce((acc, p, i, a) => {
      if (i === 0) return `M${p[0]},${p[1]}`;
      const prev = a[i - 1];
      const cx = (prev[0] + p[0]) / 2;
      return acc + ` C${cx},${prev[1]} ${cx},${p[1]} ${p[0]},${p[1]}`;
    }, '');
  }

  /* Bar chart */
  function barChart(data, opts = {}) {
    const { color = 'var(--accent)', color2 = null, height = 240, xLabels = null, stacked = false } = opts;
    const max = Math.max(...data.map(d => Array.isArray(d) ? Math.max(...d) : d)) * 1.15;
    const xStep = (W - P * 2) / data.length;
    const bw = xStep * 0.55;
    const yAxis = [0, 0.25, 0.5, 0.75, 1].map(t => {
      const y = H - P - t * (H - P * 2);
      const v = t * max;
      return `<line class="grid-line" x1="${P}" x2="${W - P}" y1="${y}" y2="${y}" /><text class="axis-label" x="${P - 6}" y="${y + 3}" text-anchor="end">${Math.round(v).toLocaleString()}</text>`;
    }).join('');
    const bars = data.map((d, i) => {
      const cx = P + i * xStep + (xStep - bw) / 2;
      if (Array.isArray(d)) {
        let y0 = H - P;
        return d.map((v, j) => {
          const h = (v / max) * (H - P * 2);
          const y = H - P - h;
          const bar = `<rect x="${cx}" y="${y0 - (y0 - y)}" width="${bw}" height="${y0 - y}" rx="3" fill="${j === 0 ? color : (color2 || 'var(--violet)')}"><animate attributeName="height" from="0" to="${y0 - y}" dur="0.6s" begin="${i * 0.05}s" fill="freeze" /><animate attributeName="y" from="${y0}" to="${y}" dur="0.6s" begin="${i * 0.05}s" fill="freeze" /></rect>`;
          y0 = y;
          return bar;
        }).join('');
      } else {
        const h = (d / max) * (H - P * 2);
        const y = H - P - h;
        return `<rect x="${cx}" y="${y}" width="${bw}" height="${h}" rx="3" fill="url(#bg-${i})"><animate attributeName="height" from="0" to="${h}" dur="0.6s" begin="${i * 0.05}s" fill="freeze" /><animate attributeName="y" from="${H - P}" to="${y}" dur="0.6s" begin="${i * 0.05}s" fill="freeze" /></rect>
                <defs><linearGradient id="bg-${i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${color}"/><stop offset="100%" stop-color="${color}" stop-opacity="0.6"/></linearGradient></defs>`;
      }
    }).join('');
    const xA = xLabels || data.map((_, i) => '');
    const xAxis = xA.map((l, i) => l ? `<text x="${P + i * xStep + xStep / 2}" y="${H - 10}" text-anchor="middle" class="axis-label">${l}</text>` : '').join('');
    return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="height:${height}px">${yAxis}${bars}${xAxis}</svg>`;
  }

  /* Radar */
  function radarChart(values, opts = {}) {
    const { size = 360, levels = 5, labels = [], stroke = 'var(--accent)' } = opts;
    const cx = size / 2, cy = size / 2;
    const r = size * 0.36;
    const angleStep = (2 * Math.PI) / values.length;
    const start = -Math.PI / 2;
    const grid = [];
    const axes = [];
    const dots = [];
    for (let l = 1; l <= levels; l++) {
      const lr = (r * l) / levels;
      const pts = [];
      for (let i = 0; i < values.length; i++) {
        const a = start + i * angleStep;
        pts.push(`${cx + Math.cos(a) * lr},${cy + Math.sin(a) * lr}`);
      }
      grid.push(`<polygon points="${pts.join(' ')}" fill="var(--surface-2)" fill-opacity="0.2" stroke="var(--border)" stroke-width="1" />`);
    }
    for (let i = 0; i < values.length; i++) {
      const a = start + i * angleStep;
      axes.push(`<line x1="${cx}" y1="${cy}" x2="${cx + Math.cos(a) * r}" y2="${cy + Math.sin(a) * r}" stroke="var(--border)" />`);
    }
    const dataPts = values.map((v, i) => {
      const a = start + i * angleStep;
      return [cx + Math.cos(a) * (r * v / 100), cy + Math.sin(a) * (r * v / 100)];
    });
    const dataPath = dataPts.map((p, i) => (i ? 'L' : 'M') + p[0] + ',' + p[1]).join(' ') + ' Z';
    dataPts.forEach((p, i) => dots.push(`<circle cx="${p[0]}" cy="${p[1]}" r="4.5" fill="white" stroke="${stroke}" stroke-width="2.5" />`));
    const labelEls = labels.map((l, i) => {
      const a = start + i * angleStep;
      const x = cx + Math.cos(a) * (r + 28);
      const y = cy + Math.sin(a) * (r + 28);
      return `<text x="${x}" y="${y}" text-anchor="middle" alignment-baseline="middle" font-size="12" font-weight="600" fill="var(--text)">${l}</text><text x="${x}" y="${y + 14}" text-anchor="middle" alignment-baseline="middle" font-size="11" fill="var(--muted)">${values[i]}/100</text>`;
    }).join('');

    return `<svg viewBox="0 0 ${size} ${size}">
      <defs>
        <radialGradient id="radar-g" cx="50%" cy="50%">
          <stop offset="0%" stop-color="${stroke}" stop-opacity="0.55"/>
          <stop offset="100%" stop-color="${stroke}" stop-opacity="0.05"/>
        </radialGradient>
      </defs>
      ${grid.join('')}
      ${axes.join('')}
      <path d="${dataPath}" fill="url(#radar-g)" stroke="${stroke}" stroke-width="2.5" stroke-linejoin="round" />
      ${dots.join('')}
      ${labelEls}
    </svg>`;
  }

  /* Donut */
  function donutChart(slices, opts = {}) {
    const { size = 200, thickness = 22, label = '' } = opts;
    const c = size / 2;
    const r = c - thickness / 2 - 4;
    const total = slices.reduce((s, x) => s + x.value, 0);
    let offset = -90;
    let paths = '';
    slices.forEach((s, i) => {
      const a = (s.value / total) * 360;
      const start = polar(c, c, r, offset);
      const end = polar(c, c, r, offset + a);
      const large = a > 180 ? 1 : 0;
      paths += `<path d="M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y}" stroke="${s.color}" stroke-width="${thickness}" fill="none" stroke-linecap="round" />`;
      offset += a;
    });
    const colors = slices.map(s => `<div class="row" style="gap:10px;font-size:0.82rem;padding:4px 0"><span style="width:10px;height:10px;border-radius:3px;background:${s.color}"></span><span style="color:var(--muted)">${s.label}</span><span style="margin-left:auto;font-weight:600">${((s.value/total)*100).toFixed(0)}%</span></div>`).join('');
    return `<div style="display:grid;grid-template-columns:auto 1fr;gap:24px;align-items:center">
      <svg viewBox="0 0 ${size} ${size}" style="width:${size}px;height:${size}px;transform:rotate(-90deg)">
        <circle cx="${c}" cy="${c}" r="${r}" stroke="var(--surface-2)" stroke-width="${thickness}" fill="none" />
        ${paths}
        <g style="transform:rotate(90deg);transform-origin:${c}px ${c}px">
          <text x="${c}" y="${c - 6}" text-anchor="middle" font-size="13" fill="var(--muted)" font-weight="500">${label}</text>
          <text x="${c}" y="${c + 14}" text-anchor="middle" font-size="20" fill="var(--text)" font-weight="700">${total}</text>
        </g>
      </svg>
      <div>${colors}</div>
    </div>`;
  }
  function polar(cx, cy, r, deg) {
    const rad = (deg - 90) * Math.PI / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  /* Pie (filled) */
  function pieChart(slices, size = 220) {
    const c = size / 2;
    const r = c - 10;
    const total = slices.reduce((s, x) => s + x.value, 0);
    let offset = -90;
    let paths = '';
    slices.forEach((s, i) => {
      const a = (s.value / total) * 360;
      const start = polar(c, c, r, offset);
      const end = polar(c, c, r, offset + a);
      const large = a > 180 ? 1 : 0;
      const c1 = polar(c, c, r, offset + a / 4);
      const c2 = polar(c, c, r, offset + a * 0.75);
      paths += `<path d="M ${c} ${c} L ${start.x} ${start.y} A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y} Z" fill="${s.color}" stroke="var(--surface)" stroke-width="2" />`;
      offset += a;
    });
    return `<svg viewBox="0 0 ${size} ${size}" style="width:100%;max-width:${size}px;height:auto"><circle cx="${c}" cy="${c}" r="${r}" fill="var(--surface-2)" />${paths}</svg>`;
  }

  /* Heatmap (rows × months) — driven by data, deterministic per seed */
  function heatmap(rows, months, seed = 'x') {
    let h = 2166136261;
    for (let i = 0; i < seed.length; i++) { h ^= seed.charCodeAt(i); h = Math.imul(h, 16777619); }
    const rand = () => { h += 0x6D2B79F5; let t = h; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    const heat = rows.map(src => `
      <div class="row-label">${src}</div>
      ${months.map((m) => {
        const v = Math.max(0, Math.min(5, Math.floor(rand() * 5) + 1));
        return `<div class="cell h${v}" title="${src} · ${m}"></div>`;
      }).join('')}
    `).join('');
    return `<div></div>${months.map(m => `<div class="row-label" style="justify-content:center;font-size:0.65rem">${m}</div>`).join('')}${heat}`;
  }

  /* Counters (animate numbers) */
  function animateNumber(el, from = 0, to = 100, dur = 1200, prefix = '', suffix = '') {
    const start = performance.now();
    function step(now) {
      const p = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      const val = from + (to - from) * eased;
      el.textContent = prefix + (Number.isInteger(to) ? Math.round(val).toLocaleString() : val.toFixed(1)) + suffix;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  function initCounters() {
    $$('[data-counter]').forEach(el => {
      const to = parseFloat(el.dataset.counter);
      const prefix = el.dataset.prefix || '';
      const suffix = el.dataset.suffix || '';
      const dur = parseFloat(el.dataset.dur || 1200);
      animateNumber(el, 0, to, dur, prefix, suffix);
    });
  }

  /* ------------------------------ Particles canvas ---------------------- */
  function initParticles() {
    const c = $('canvas.particles');
    if (!c) return;
    const ctx = c.getContext('2d');
    const resize = () => {
      c.width = c.offsetWidth * window.devicePixelRatio;
      c.height = c.offsetHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    };
    resize();
    window.addEventListener('resize', resize);

    const N = 50;
    const dots = [...Array(N)].map(() => ({
      x: Math.random() * c.offsetWidth,
      y: Math.random() * c.offsetHeight,
      r: Math.random() * 2 + 0.6,
      vx: (Math.random() - 0.5) * 0.2,
      vy: (Math.random() - 0.5) * 0.2,
    }));
    function tick() {
      ctx.clearRect(0, 0, c.offsetWidth, c.offsetHeight);
      const accent = css('--accent') || '#2563EB';
      for (let i = 0; i < N; i++) {
        const d = dots[i];
        d.x += d.vx; d.y += d.vy;
        if (d.x < 0 || d.x > c.offsetWidth) d.vx *= -1;
        if (d.y < 0 || d.y > c.offsetHeight) d.vy *= -1;
        ctx.fillStyle = accent + '70';
        ctx.beginPath();
        ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
        ctx.fill();
        for (let j = i + 1; j < N; j++) {
          const dx = d.x - dots[j].x, dy = d.y - dots[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 110) {
            ctx.strokeStyle = accent + (Math.floor(60 * (1 - dist / 110))).toString(16).padStart(2, '0');
            ctx.lineWidth = 0.5;
            ctx.beginPath();
            ctx.moveTo(d.x, d.y);
            ctx.lineTo(dots[j].x, dots[j].y);
            ctx.stroke();
          }
        }
      }
      requestAnimationFrame(tick);
    }
    tick();
  }

  /* ------------------------------ Command palette ----------------------- */
  function initCommandPalette() {
    const overlay = $('[data-command]');
    if (!overlay) return;
    const open = () => { overlay.style.display = 'grid'; $('[data-command-input]', overlay).focus(); };
    const close = () => overlay.style.display = 'none';
    $$('[data-command-open]').forEach(b => b.addEventListener('click', open));
    overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
    document.addEventListener('keydown', e => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); open(); }
      if (e.key === 'Escape') close();
    });
    /* search filter */
    const input = $('[data-command-input]', overlay);
    input?.addEventListener('input', () => {
      const v = input.value.toLowerCase();
      $$('[data-cmd-item]', overlay).forEach(it => {
        it.style.display = it.textContent.toLowerCase().includes(v) ? 'flex' : 'none';
      });
    });
    $$('[data-cmd-item]', overlay).forEach(it => {
      it.addEventListener('click', () => {
        location.href = it.dataset.href;
      });
    });
  }

  /* ------------------------------ Range sliders ------------------------- */
  function initSliders() {
    $$('[data-slider]').forEach(s => {
      const fill = $('.fill', s);
      const inp = $('input', s);
      const out = $('.out', s.parentElement || s.parentNode);
      const update = () => {
        const v = inp.value;
        if (fill) fill.style.width = ((v - inp.min) / (inp.max - inp.min) * 100) + '%';
        if (out) out.textContent = inp.dataset.prefix === 'money' ? fmt.money(v) : v + (inp.dataset.suffix || '');
      };
      inp.addEventListener('input', update);
      update();
    });
  }

  /* ------------------------------- Hot init ----------------------------- */
  const init = () => {
    initSidebar();
    initTheme();
    initCounters();
    initParticles();
    initCommandPalette();
    initSliders();
    /* simulate page entry */
    document.body.style.opacity = 0;
    requestAnimationFrame(() => document.body.style.transition = 'opacity .5s', document.body.style.opacity = 1);
  };

  return { init, fmt, palette, lineChart, barChart, radarChart, donutChart, pieChart, heatmap, animateNumber };
})();

document.addEventListener('DOMContentLoaded', () => APP.init());

/* === Re-render on STORE changes === */
const REFRESHABLE_PAGES = ['dashboard', 'client-dep', 'income-quality'];
let _renderRaf = null;
function renderCurrentPage() {
  if (!window.Render) return;
  const page = document.body.dataset.page;
  if (!REFRESHABLE_PAGES.includes(page)) return;
  cancelAnimationFrame(_renderRaf);
  _renderRaf = requestAnimationFrame(() => {
    const root = document.getElementById('pageRoot') || document;
    if (page === 'dashboard') Render.dashboard(root);
    else if (page === 'client-dep') Render.clientDep(root);
    else if (page === 'income-quality') Render.incomeQuality(root);
  });
}
document.addEventListener('storechange', renderCurrentPage);

/* === Initial render: render after shell injection finishes === */
document.addEventListener('DOMContentLoaded', () => {
  /* Wait one frame so chrome.js has a chance to inject the wrapper + move
     page content into #content before we try to query for [data-r] nodes. */
  requestAnimationFrame(() => requestAnimationFrame(renderCurrentPage));
});

/* === Gate app pages: redirect to onboarding if no identity === */
const OPEN_PAGES = ['landing', 'login', 'onboarding', 'admin', 'index', 'settings'];
document.addEventListener('DOMContentLoaded', () => {
  if (!window.STORE) return;
  const page = document.body.dataset.page;
  if (!page || OPEN_PAGES.includes(page)) return;
  if (!STORE.isOnboarded()) {
    location.replace('onboarding.html');
  }
});

/* === Inline early gate (runs before paint if STORE is ready) === */
(function () {
  if (!window.STORE) return;
  const page = document.body && document.body.dataset && document.body.dataset.page;
  if (!page || OPEN_PAGES.includes(page)) return;
  if (!STORE.isOnboarded()) {
    document.documentElement.style.visibility = 'hidden';
    location.replace('onboarding.html');
  }
})();

/* === Reusable helpers exposed globally === */
window.FIA = APP;
