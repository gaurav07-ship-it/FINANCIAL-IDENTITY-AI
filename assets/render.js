/* ============================================================
   FIA RENDER — page renderers driven by STORE
   Each function rebuilds a region of the page from STORE data
   so that user input in onboarding propagates everywhere.
   ============================================================ */

const Render = (() => {

  /* ----- formatters ----- */
  const money = (v) => '₹' + Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 });
  const short = (v) => {
    const n = Number(v);
    if (Math.abs(n) >= 1e7) return '₹' + (n / 1e7).toFixed(1) + 'Cr';
    if (Math.abs(n) >= 1e5) return '₹' + (n / 1e5).toFixed(1) + 'L';
    if (Math.abs(n) >= 1e3) return '₹' + (n / 1e3).toFixed(1) + 'k';
    return '₹' + n;
  };

  /* deterministic pseudo-random for stable demo data */
  const seeded = (seed) => {
    let h = 2166136261;
    for (let i = 0; i < seed.length; i++) {
      h ^= seed.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return () => {
      h += 0x6D2B79F5;
      let t = h;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };

  /* ----- Dashboard ----- */
  const dashboard = (root) => {
    if (!root) return;
    const s = STORE.get();
    const d = STORE.computeDerived(s);
    const name = (s.personal.name || 'there').split(' ')[0] || 'there';
    const firstName = (s.personal.name || '').trim() || '—';
    const monthNames = ['Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr','May','Jun','Jul'];

    /* greeting + identity card */
    const greet = root.querySelector('[data-r="greet"]');
    if (greet) greet.innerHTML = `
      <div class="row" style="gap:8px;font-size:0.78rem;opacity:0.85">
        <span class="badge" style="background:rgba(255,255,255,.18);color:white">📅 ${new Date().toDateString().split(' ').slice(0, 3).join(' ')}</span>
        <span>${money(d.monthlyIncome)} monthly avg · +${d.yoy.toFixed(1)}% vs last 90 days</span>
      </div>
      <h1 style="margin-top:14px">Good ${hourGreeting()}, ${name} 👋</h1>
      <p style="max-width:540px">
        ${summaryBlurb(s, d)}
      </p>
      <div class="action-row">
        <a href="financial-twin.html" class="btn btn-white">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/></svg>
          Run What-If Simulation
        </a>
        <a href="loan-eligibility.html" class="btn btn-glass">View Loan Options</a>
      </div>
    `;

    const idCard = root.querySelector('[data-r="id-card"]');
    if (idCard) idCard.innerHTML = `
      <div style="position:relative;z-index:1">
        <div class="row between">
          <div>
            <div class="label">Financial Identity · FIA ID</div>
            <div class="name">${escapeHtml(firstName)}</div>
            <div style="font-size:0.78rem;opacity:0.7">${s.occupation || '—'}</div>
          </div>
          <a href="onboarding.html" class="badge info" style="text-decoration:none;cursor:pointer" title="Edit profile">Edit →</a>
        </div>
        <div class="score-row">
          <div class="score">${d.dnaScore}</div>
          <div class="score-of">/ 1000</div>
          <span class="badge ${d.dnaScore >= 800 ? 'success' : d.dnaScore >= 650 ? 'info' : 'warn'}" style="margin-bottom:8px">${d.dnaScore >= 800 ? 'Elite tier' : d.dnaScore >= 650 ? 'Strong' : 'Building'}</span>
        </div>
        <div class="meter"><div class="fill" style="width:${d.dnaScore / 10}%"></div></div>
        <div class="row-line">
          <span>${d.dnaScore >= 800 ? 'TIER · ELITE' : d.dnaScore >= 650 ? 'TIER · STRONG' : 'TIER · BUILDING'}</span>
          <span>${s.banks.primary ? s.banks.primary + ' linked' : 'No bank linked'}</span>
        </div>
      </div>
      <div class="logo">FIA</div>
    `;

    /* KPI cards */
    const kpis = root.querySelector('[data-r="kpis"]');
    if (kpis) kpis.innerHTML = kpiCards(d, s);

    /* income chart: synthesised 12-month series around monthlyIncome */
    const incEl = root.querySelector('#incomeChart');
    if (incEl && window.FIA && FIA.lineChart) {
      const rand = seeded((firstName || 'x') + 'income');
      const inc = monthNames.map((_, i) => {
        const drift = (i / 11 - 0.4) * 0.18;
        const wiggle = (rand() - 0.5) * 0.12;
        return Math.round(d.monthlyIncome * (1 + drift + wiggle));
      });
      const prev = inc.map(v => Math.round(v * (1 - 0.10 - rand() * 0.06)));
      incEl.innerHTML = FIA.lineChart(inc, {
        color: 'var(--accent)', smooth: true, height: 280, yPrefix: '₹',
        second: { data: prev, color: 'var(--violet)' },
        xLabels: monthNames,
      });
    }

    /* income donut from clients list */
    const donutEl = root.querySelector('#incomeDonut');
    if (donutEl && window.FIA && FIA.donutChart) {
      const palette = ['var(--accent)', 'var(--violet)', 'var(--teal)', 'var(--warning)', 'var(--pink)', 'var(--muted-2)'];
      const slices = d.sortedClients.length
        ? d.sortedClients.slice(0, 6).map((c, i) => ({ label: c.name, value: c.share, color: palette[i % palette.length] }))
        : [{ label: 'No sources yet', value: 1, color: 'var(--muted-2)' }];
      donutEl.innerHTML = FIA.donutChart(slices, { size: 180, thickness: 22, label: 'DISTRIBUTION' });
    }

    /* DNA radar + bars */
    const radarEl = root.querySelector('#dnaRadar');
    if (radarEl && window.FIA && FIA.radarChart) {
      radarEl.innerHTML = FIA.radarChart(
        [d.stability, d.discipline, d.growth, d.savings, d.diversificationIndex, d.risk],
        { size: 300, labels: ['Stability','Discipline','Growth','Savings','Diversif.','Risk'], stroke: 'var(--accent)' }
      );
    }
    const barsEl = root.querySelector('#dnaBars');
    if (barsEl) barsEl.innerHTML = `
      <div><div class="row between" style="margin-bottom:6px"><span style="font-size:0.88rem;font-weight:500">Stability</span><span style="font-size:0.85rem;color:var(--muted)">${d.stability}/100</span></div><div class="progress"><div class="fill" style="width:${d.stability}%;background:var(--accent)"></div></div></div>
      <div><div class="row between" style="margin-bottom:6px"><span style="font-size:0.88rem;font-weight:500">Discipline</span><span style="font-size:0.85rem;color:var(--muted)">${d.discipline}/100</span></div><div class="progress"><div class="fill" style="width:${d.discipline}%;background:var(--success)"></div></div></div>
      <div><div class="row between" style="margin-bottom:6px"><span style="font-size:0.88rem;font-weight:500">Growth</span><span style="font-size:0.85rem;color:var(--muted)">${d.growth}/100</span></div><div class="progress"><div class="fill" style="width:${d.growth}%;background:var(--violet)"></div></div></div>
      <div><div class="row between" style="margin-bottom:6px"><span style="font-size:0.88rem;font-weight:500">Savings</span><span style="font-size:0.85rem;color:var(--muted)">${d.savings}/100</span></div><div class="progress"><div class="fill" style="width:${d.savings}%;background:var(--teal)"></div></div></div>
      <div><div class="row between" style="margin-bottom:6px"><span style="font-size:0.88rem;font-weight:500">Diversification</span><span style="font-size:0.85rem;color:var(--muted)">${d.diversificationIndex}/100</span></div><div class="progress"><div class="fill" style="width:${d.diversificationIndex}%;background:var(--warning)"></div></div></div>
      <div><div class="row between" style="margin-bottom:6px"><span style="font-size:0.88rem;font-weight:500">Risk Posture</span><span style="font-size:0.85rem;color:var(--muted)">${d.risk}/100</span></div><div class="progress"><div class="fill" style="width:${d.risk}%;background:var(--pink)"></div></div></div>
    `;

    /* EMIs driven by goals: each "loan-like" goal gets a synthetic EMI */
    const emiEl = root.querySelector('#emiList');
    if (emiEl) {
      const loanGoals = (s.goals || []).filter(g => /Loan/.test(g));
      const items = [];
      if (loanGoals.includes('Home Loan')) items.push({ i: '🏠', n: 'Home Loan EMI', d: 'HDFC · 22 of 240', a: 24800, due: '2 Aug', col: 'var(--accent)' });
      if (loanGoals.includes('Business Loan')) items.push({ i: '💼', n: 'Business Loan EMI', d: 'Lendingkart · 6 of 36', a: 12500, due: '9 Aug', col: 'var(--violet)' });
      if (loanGoals.includes('Higher Studies')) items.push({ i: '🎓', n: 'Education Loan', d: 'SBI · 14 of 60', a: 8200, due: '15 Aug', col: 'var(--teal)' });
      if (loanGoals.includes('New Gadget')) items.push({ i: '📱', n: 'Gadget EMI', d: 'Bajaj Finserv · 4 of 12', a: 4250, due: '4 Aug', col: 'var(--warning)' });
      if (!items.length) items.push({ i: '⚡', n: 'Electricity Bill', d: 'Adani · Mumbai', a: 2180, due: '7 Aug', col: 'var(--warning)' });

      emiEl.innerHTML = items.map(e => `
        <div class="row" style="gap:14px;padding:12px;border-radius:12px;background:var(--surface-2)">
          <div style="width:42px;height:42px;border-radius:10px;background:color-mix(in srgb, ${e.col} 20%, transparent);color:${e.col};display:grid;place-items:center;font-size:1.2rem">${e.i}</div>
          <div style="flex:1;min-width:0"><strong style="display:block;font-size:0.92rem">${e.n}</strong><span class="muted" style="font-size:0.78rem">${e.d}</span></div>
          <div style="text-align:right"><div style="font-weight:600">${money(e.a)}</div><span class="muted" style="font-size:0.78rem">Due ${e.due}</span></div>
        </div>
      `).join('');
    }
  };

  /* ----- Client dependency ----- */
  const clientDep = (root) => {
    if (!root) return;
    const s = STORE.get();
    const d = STORE.computeDerived(s);
    const palette = ['#2563EB', '#8B5CF6', '#14B8A6', '#F59E0B', '#EC4899', '#64748B', '#3B82F6', '#06B6D4'];
    const clients = d.sortedClients;

    /* KPI row */
    const kpiRow = root.querySelector('[data-r="kpis"]');
    if (kpiRow) kpiRow.innerHTML = `
      <div class="card elev"><div class="stat"><div class="label">Top client concentration</div><div class="value"><span>${d.topClientShare}</span><span class="unit">%</span></div><span class="badge ${d.topClientShare > 60 ? 'danger' : d.topClientShare > 40 ? 'warn' : 'success'}"><span class="dot"></span> ${d.topClientShare > 60 ? 'High risk' : d.topClientShare > 40 ? 'Concentrated' : 'Balanced'}</span></div></div>
      <div class="card elev"><div class="stat"><div class="label">Active clients</div><div class="value">${clients.length || 0}</div><span class="muted" style="font-size:0.78rem">${clients.filter(c => c.kind === 'project' || c.kind === 'salary').length} regular · ${clients.filter(c => c.kind === 'gig').length} gig</span></div></div>
      <div class="card elev"><div class="stat"><div class="label">Herfindahl score</div><div class="value">${d.herfindahl}</div><span class="badge ${d.herfindahl > 5000 ? 'danger' : d.herfindahl > 2500 ? 'warn' : 'success'}"><span class="dot"></span> ${d.herfindahl > 5000 ? 'Concentrated' : d.herfindahl > 2500 ? 'Moderate' : 'Diverse'}</span></div></div>
      <div class="card elev"><div class="stat"><div class="label">Diversification index</div><div class="value"><span>${d.diversificationIndex}</span><span class="unit">/100</span></div><span class="badge ${d.diversificationIndex >= 60 ? 'success' : d.diversificationIndex >= 40 ? 'warn' : 'danger'}"><span class="dot"></span> ${d.diversificationIndex >= 60 ? 'Healthy' : d.diversificationIndex >= 40 ? 'Needs work' : 'Critical'}</span></div></div>
    `;

    /* bubble graph */
    const bubbleEl = root.querySelector('#bubbleGraph');
    if (bubbleEl) {
      const W = 700, H = 400;
      const cx = W / 2, cy = H / 2;
      const N = Math.max(clients.length, 1);
      const list = clients.length ? clients : [{ name: 'No sources yet', share: 100, color: '#64748B', dur: 0 }];
      let svg = `<svg viewBox="0 0 ${W} ${H}">`;
      for (let r = 60; r < 200; r += 40) svg += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--border)" stroke-dasharray="2 4" opacity="0.4"/>`;
      list.forEach((c, i) => {
        const angle = (i / N) * Math.PI * 2 - Math.PI / 2;
        const dist = 0.32;
        const tx = cx + Math.cos(angle) * W * dist;
        const ty = cy + Math.sin(angle) * H * dist;
        const color = c.color || palette[i % palette.length];
        svg += `<line x1="${cx}" y1="${cy}" x2="${tx}" y2="${ty}" stroke="${color}" stroke-width="1.5" opacity="0.4" stroke-dasharray="3 4"/>`;
      });
      svg += `<circle cx="${cx}" cy="${cy}" r="42" fill="var(--gradient-brand)" opacity="0.95"/><circle cx="${cx}" cy="${cy}" r="42" fill="none" stroke="white" stroke-width="3"/><text x="${cx}" y="${cy - 4}" text-anchor="middle" fill="white" font-size="11" font-weight="600">YOUR</text><text x="${cx}" y="${cy + 10}" text-anchor="middle" fill="white" font-size="11" font-weight="600">INCOME</text>`;
      list.forEach((c, i) => {
        const angle = (i / N) * Math.PI * 2 - Math.PI / 2;
        const dist = 0.32;
        const tx = cx + Math.cos(angle) * W * dist;
        const ty = cy + Math.sin(angle) * H * dist;
        const color = c.color || palette[i % palette.length];
        const r = 18 + c.share * 0.9;
        svg += `<g class="bubble"><circle cx="${tx}" cy="${ty}" r="${r}" fill="${color}" opacity="0.18"/><circle cx="${tx}" cy="${ty}" r="${r}" fill="none" stroke="${color}" stroke-width="2.5"/><text x="${tx}" y="${ty + 4}" text-anchor="middle" fill="${color}" font-size="${Math.max(11, r * 0.45)}" font-weight="700">${Math.round(c.share)}%</text><text x="${tx}" y="${ty - r - 8}" text-anchor="middle" fill="var(--text)" font-size="11" font-weight="600">${escapeHtml(c.name)}</text></g>`;
      });
      svg += `</svg>`;
      bubbleEl.innerHTML = svg;
    }

    /* client list */
    const listEl = root.querySelector('#clientList');
    if (listEl) {
      if (!clients.length) {
        listEl.innerHTML = `<div class="card" style="padding:24px;text-align:center;color:var(--muted)">No income sources selected yet. <a href="onboarding.html">Complete onboarding →</a></div>`;
      } else {
        listEl.innerHTML = clients.slice(0, 6).map((c, i) => {
          const color = c.color || palette[i % palette.length];
          return `
            <div class="client-card">
              <div class="av" style="background:${color}">${escapeHtml(c.name[0])}</div>
              <div style="min-width:0">
                <div class="row" style="gap:6px"><strong>${escapeHtml(c.name)}</strong>${c.kind === 'project' || c.kind === 'salary' ? '<span class="badge info" style="padding:2px 6px;font-size:0.65rem">Regular</span>' : ''}</div>
                <div class="muted" style="font-size:0.78rem">${capitalize(c.kind)}</div>
                <div class="meter mt-1"><div class="f" style="width:${c.share}%;background:${color}"></div></div>
              </div>
              <div style="text-align:right"><strong>${c.share.toFixed(1)}%</strong></div>
            </div>`;
        }).join('');
      }
    }

    /* concentration over time: synthesised trend toward current value */
    const concEl = root.querySelector('#concChart');
    if (concEl && window.FIA && FIA.lineChart) {
      const start = Math.min(95, d.topClientShare + 25);
      const series = [0, 1, 2, 3, 4, 5].map(i => Math.round(start + (d.topClientShare - start) * (i / 5)));
      concEl.innerHTML = FIA.lineChart(series, { color: d.topClientShare > 60 ? 'var(--danger)' : 'var(--warning)', smooth: true, height: 240, xLabels: ['Feb','Mar','Apr','May','Jun','Jul'] });
    }
  };

  /* ----- Income quality ----- */
  const incomeQuality = (root) => {
    if (!root) return;
    const s = STORE.get();
    const d = STORE.computeDerived(s);
    const monthNames = ['Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr','May','Jun','Jul'];
    const sources = s.incomeSources || [];

    /* KPI row */
    const kpiRow = root.querySelector('[data-r="kpis"]');
    if (kpiRow) kpiRow.innerHTML = `
      <div class="card elev"><div class="stat"><div class="label">Income Quality Score</div><div class="value"><span>${d.incomeQuality}</span><span class="unit">/100</span></div><span class="badge ${d.incomeQuality >= 70 ? 'success' : d.incomeQuality >= 45 ? 'warn' : 'danger'}"><span class="dot"></span> ${d.incomeQuality >= 70 ? 'Strong' : d.incomeQuality >= 45 ? 'Average' : 'Critical'}</span></div></div>
      <div class="card elev"><div class="stat"><div class="label">Coefficient of Variation</div><div class="value">±<span>${d.cv}</span>%</div><span class="badge ${d.cv <= 10 ? 'success' : d.cv <= 18 ? 'warn' : 'danger'}"><span class="dot"></span> ${d.cv <= 10 ? 'Stable' : d.cv <= 18 ? 'Variable' : 'Volatile'}</span></div></div>
      <div class="card elev"><div class="stat"><div class="label">YoY Growth</div><div class="value">+<span>${d.yoy}</span>.0%</div><span class="badge ${d.yoy >= 12 ? 'success' : 'info'}"><span class="dot"></span> ${d.yoy >= 12 ? 'Strong' : 'Moderate'}</span></div></div>
      <div class="card elev"><div class="stat"><div class="label">Late Payouts</div><div class="value"><span>${d.latePayouts}</span>.0%</div><span class="badge ${d.latePayouts < 4 ? 'success' : d.latePayouts < 8 ? 'warn' : 'danger'}"><span class="dot"></span> ${d.latePayouts < 4 ? 'Excellent' : 'Watch'}</span></div></div>
    `;

    /* monthly bars: synthesised 12-month income around monthlyIncome */
    const barEl = root.querySelector('#incomeBars');
    if (barEl && window.FIA && FIA.barChart) {
      const rand = seeded((s.personal.name || 'x') + 'iq');
      const monthly = monthNames.map((_, i) => {
        const drift = (i / 11 - 0.4) * 0.15;
        const wiggle = (rand() - 0.5) * 0.14;
        return Math.round(d.monthlyIncome * (1 + drift + wiggle));
      });
      barEl.innerHTML = FIA.barChart(monthly, { color: 'var(--accent)', height: 280, xLabels: monthNames });
      const avg = monthly.reduce((a, b) => a + b, 0) / monthly.length;
      const variance = Math.round(Math.sqrt(monthly.reduce((s, v) => s + Math.pow(v - avg, 2), 0) / monthly.length));
      const legend = barEl.parentElement.querySelector('[data-r="iq-legend"]');
      if (legend) legend.innerHTML = `Variance: ±${money(variance)} · <b style="color:${variance / avg < 0.1 ? 'var(--success)' : 'var(--warning)'}">${variance / avg < 0.1 ? 'Stable' : variance / avg < 0.18 ? 'Moderate' : 'Volatile'}</b>`;
    }

    /* heatmap: rows = each selected income source */
    const heatEl = root.querySelector('#heatmap');
    if (heatEl && FIA.heatmap) {
      heatEl.innerHTML = FIA.heatmap(sources.length ? sources : ['No sources yet'], monthNames);
    } else if (heatEl) {
      const rand = seeded((s.personal.name || 'x') + 'heat');
      const rows = sources.length ? sources : ['No sources yet'];
      const heat = rows.map((src, si) => `
        <div class="row-label">${escapeHtml(src)}</div>
        ${Array.from({ length: 12 }, (_, m) => {
          const v = Math.max(0, Math.min(5, Math.floor(rand() * 5) + 1));
          return `<div class="cell h${v}" title="${escapeHtml(src)} · ${monthNames[m]}"></div>`;
        }).join('')}
      `).join('');
      heatEl.innerHTML = `<div></div>${monthNames.map(m => `<div class="row-label" style="justify-content:center;font-size:0.65rem">${m}</div>`).join('')}${heat}`;
    }

    /* monthly breakdown scores: 6 entries trending toward current incomeQuality */
    const monthlyEl = root.querySelector('#monthly');
    if (monthlyEl) {
      const rand = seeded((s.personal.name || 'x') + 'mo');
      const target = d.incomeQuality;
      const months = ['Jul 2026','Jun 2026','May 2026','Apr 2026','Mar 2026','Feb 2026'];
      const base = Math.max(20, target - 18);
      const scores = months.map((m, i) => {
        const v = Math.round(base + (target - base) * (i / 5) + (rand() - 0.5) * 4);
        const delta = Math.round((rand() - 0.4) * 6);
        const col = v >= 70 ? 'var(--success)' : v >= 50 ? 'var(--accent)' : 'var(--warning)';
        return { m, s: v, c: col, delta };
      });
      monthlyEl.innerHTML = scores.map(x => `
        <div>
          <div class="row between" style="margin-bottom:6px">
            <span style="font-weight:500">${x.m}</span>
            <div class="row" style="gap:8px"><span style="font-weight:700">${x.s}</span><span class="delta ${x.delta > 0 ? 'up' : x.delta < 0 ? 'down' : 'flat'}">${x.delta > 0 ? '+' : ''}${x.delta}</span></div>
          </div>
          <div class="progress" style="height:5px"><div class="fill" style="width:${x.s}%;background:${x.c}"></div></div>
        </div>
      `).join('');
    }

    /* trend chart */
    const trendEl = root.querySelector('#trendChart');
    if (trendEl && window.FIA && FIA.lineChart) {
      const rand = seeded((s.personal.name || 'x') + 'trend');
      const inc = monthNames.map((_, i) => {
        const drift = (i / 11 - 0.4) * 0.18;
        const wiggle = (rand() - 0.5) * 0.1;
        return Math.round(d.monthlyIncome * (1 + drift + wiggle));
      });
      trendEl.innerHTML = FIA.lineChart(inc, { color: 'var(--accent)', smooth: true, height: 280, yPrefix: '₹', xLabels: monthNames });
    }

    /* AI explanation copy driven by actual data */
    const aiEl = root.querySelector('[data-r="ai-explain"]');
    if (aiEl) aiEl.innerHTML = `
      <div class="insight" style="background:var(--success-soft);border-color:rgba(34,197,94,0.2)">
        <div class="ico" style="background:linear-gradient(135deg,#22C55E,#10B981)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <div><h4>Strengths</h4><p>Income arrives within ±3 days 96% of the time. YoY growth of ${d.yoy}.0% puts you in top 25%.</p></div>
      </div>
      <div class="insight" style="background:var(--warning-soft);border-color:rgba(245,158,11,0.2)">
        <div class="ico" style="background:linear-gradient(135deg,#F59E0B,#FB923C)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9v4M12 17h.01"/><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>
        </div>
        <div><h4>Risks</h4><p>Top client = ${d.topClientShare.toFixed(0)}% of income. ${d.topClientShare > 50 ? `Dropping this below 50% would lift score by 12-18 points.` : `Diversification looks healthy.`}</p></div>
      </div>
      <div class="insight" style="background:rgba(139,92,246,0.08);border-color:rgba(139,92,246,0.2)">
        <div class="ico" style="background:linear-gradient(135deg,#8B5CF6,#EC4899)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/></svg>
        </div>
        <div><h4>AI Recommendation</h4><p>${recommendation(s, d)}</p></div>
      </div>
    `;
  };

  /* ----- helpers ----- */
  function hourGreeting() {
    const h = new Date().getHours();
    if (h < 12) return 'morning';
    if (h < 17) return 'afternoon';
    return 'evening';
  }

  function summaryBlurb(s, d) {
    const name = (s.personal.name || '').trim() || 'there';
    if (!s.occupation && !s.incomeSources.length) {
      return `Welcome to Financial Identity AI. Complete <a href="onboarding.html" style="color:white;text-decoration:underline">onboarding</a> to start building your identity.`;
    }
    if (d.topClientShare >= 80) {
      return `${name.split(' ')[0] || name}, your top income source is <b style="color:#86EFAC">${d.topClientShare.toFixed(0)}% concentrated</b>. Diversifying to 3+ sources could lift your DNA by 40+ points.`;
    }
    if (d.topClientShare >= 50) {
      return `${name.split(' ')[0] || name}, your Financial DNA score is <b style="color:#86EFAC">${d.dnaScore}/1000</b>. Your biggest opportunity is <b>diversifying income</b> — you're currently ${d.topClientShare.toFixed(0)}% reliant on one source.`;
    }
    return `${name.split(' ')[0] || name}, your Financial DNA score is <b style="color:#86EFAC">${d.dnaScore}/1000</b>. Income is well-diversified across ${d.sortedClients.length} sources.`;
  }

  function recommendation(s, d) {
    if (!s.incomeSources.length) return 'Pick at least one income source in onboarding to get personalised tips.';
    if (d.topClientShare > 70) return 'Add 2 more income sources — could drop top-client share from ' + d.topClientShare.toFixed(0) + '% to below 50% and lift Income Quality by 18 points.';
    if (!s.incomeSources.includes('Investments')) return 'Add an "Investments" income source to boost savings sub-score and unlock passive-income benefits.';
    if (!s.gigPlatforms.length) return 'Activate 1-2 gig platforms weekly — even part-time use contributes to Income Quality.';
    return 'Income Quality looks strong. Focus on growing existing sources rather than adding new ones.';
  }

  function kpiCards(d, s) {
    const monthlySeries = (s.personal.name || 'x') + 'kpi';
    const rand = seeded(monthlySeries);
    const monthlyNow = d.monthlyIncome;
    const monthlyPrev = Math.round(monthlyNow / (1 + (d.yoy / 100)));
    return `
      <div class="card elev"><div class="row between mb-2"><div class="kpi-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L4 7l8 5 8-5-8-5z"/><path d="M4 17l8 5 8-5M4 12l8 5 8-5"/></svg></div><span class="badge success"><span class="dot"></span> ${d.yoy.toFixed(1)}%</span></div><div class="stat"><div class="label">Financial DNA</div><div class="value"><span>${d.dnaScore}</span><span class="unit">/1000</span></div><span class="muted" style="font-size:0.78rem">${d.dnaScore >= 800 ? 'Elite tier' : d.dnaScore >= 650 ? 'Strong tier' : 'Building'}</span></div></div>
      <div class="card elev"><div class="row between mb-2"><div class="kpi-icon green"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 14l9-9M21 5h-6M21 5v6"/><circle cx="12" cy="12" r="10"/></svg></div><span class="badge ${d.dnaScore >= 800 ? 'success' : 'info'}"><span class="dot"></span> ${d.dnaScore >= 800 ? 'Elite' : 'Good'}</span></div><div class="stat"><div class="label">Financial Health</div><div class="value"><span>${Math.round(d.dnaScore / 10)}</span><span class="unit">%</span></div><span class="muted" style="font-size:0.78rem">${d.dnaScore >= 800 ? 'Strong overall position' : 'Room to grow'}</span></div></div>
      <div class="card elev"><div class="row between mb-2"><div class="kpi-icon violet"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg></div><span class="badge ${d.stability >= 70 ? 'success' : 'warn'}"><span class="dot"></span> ${d.stability >= 70 ? 'Stable' : 'Watch'}</span></div><div class="stat"><div class="label">Income Stability</div><div class="value"><span>${d.stability}</span><span class="unit">%</span></div><span class="muted" style="font-size:0.78rem">CoV: ±${d.cv}%</span></div></div>
      <div class="card elev"><div class="row between mb-2"><div class="kpi-icon teal"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h6l4-9 4 18 4-9h2"/></svg></div><span class="badge ${d.diversificationIndex >= 60 ? 'success' : 'warn'}"><span class="dot"></span> ${d.diversificationIndex >= 60 ? 'Healthy' : 'Needs work'}</span></div><div class="stat"><div class="label">Income Quality</div><div class="value"><span>${d.incomeQuality}</span><span class="unit">/100</span></div><span class="muted" style="font-size:0.78rem">Top client = ${d.topClientShare.toFixed(0)}%</span></div></div>
      <div class="card elev"><div class="row between mb-2"><div class="kpi-icon warn"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></div><span class="badge ${d.risk >= 70 ? 'success' : d.risk >= 50 ? 'warn' : 'danger'}"><span class="dot"></span> ${d.risk >= 70 ? 'Safe' : d.risk >= 50 ? 'Caution' : 'Risk'}</span></div><div class="stat"><div class="label">Risk Posture</div><div class="value"><span>${d.risk}</span><span class="unit">/100</span></div><span class="muted" style="font-size:0.78rem">Based on ${d.sortedClients.length} sources</span></div></div>
    `;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  }
  function capitalize(s) { return s ? s[0].toUpperCase() + s.slice(1) : ''; }

  return { dashboard, clientDep, incomeQuality };
})();

window.Render = Render;