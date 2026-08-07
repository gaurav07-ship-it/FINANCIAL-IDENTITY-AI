/* ============================================================
   FIA API — fetch wrapper + STORE shim backed by the FastAPI backend.

   Drop <script src="assets/api.js"></script> before store.js. If the API
   is unreachable, api.js silently defers to the localStorage version
   already loaded.

   Public surface (window.API):
     API.base                          - default base URL
     API.fetch(path, opts)             - fetch wrapper w/ refresh-on-401
     API.me()                          - GET  /auth/me
     API.login(email, password)
     API.register(name, email, password)
     API.logout()
     API.refresh()
     API.getIdentity()
     API.computeDna()
     API.computeIncomeQuality()
     API.simulateTwin(body)
     API.listOffers(amount?)
     API.listOpportunities()
     API.consent()
     API.pullConsent(id)
     API.onboard.personal / occupation / incomeSources / banks / upi /
              gig / permissions / finish (payload)
     API.events                       - { login, logout, storechange }

   STORE (window.STORE) is replaced with an API-backed implementation that
   exposes the same surface the renderers already use.
   ============================================================ */

(function () {
  const DEFAULT_BASE = 'http://localhost:8000/api/v1';
  const base = window.FIA_API_BASE || DEFAULT_BASE;

  /* ── tiny event bus ──────────────────────────────────────────────── */
  const events = {};
  const emit = (name, detail) => {
    (events[name] || []).forEach((fn) => {
      try { fn(detail); } catch (e) { console.error('[api event]', name, e); }
    });
    document.dispatchEvent(new CustomEvent('fia:' + name, { detail }));
  };
  const on = (name, fn) => {
    (events[name] = events[name] || []).push(fn);
    return () => {
      events[name] = events[name].filter((f) => f !== fn);
    };
  };

  /* ── error class ─────────────────────────────────────────────────── */
  class ApiError extends Error {
    constructor(status, detail) {
      super(typeof detail === 'string' ? detail : JSON.stringify(detail));
      this.status = status;
      this.detail = detail;
      this.name = 'ApiError';
    }
  }

  /* ── fetch wrapper with refresh-on-401 ───────────────────────────── */
  let refreshInFlight = null;
  async function refreshOnce() {
    if (!refreshInFlight) {
      refreshInFlight = fetch(base + '/auth/refresh', {
        method: 'POST',
        credentials: 'include',
      }).finally(() => { refreshInFlight = null; });
    }
    const res = await refreshInFlight;
    return res.ok;
  }

  async function rawFetch(path, opts = {}, _retry = true) {
    const url = path.startsWith('http') ? path : base + path;
    const res = await fetch(url, {
      ...opts,
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        ...(opts.body && !(opts.body instanceof FormData)
          ? { 'Content-Type': 'application/json' }
          : {}),
        ...(opts.headers || {}),
      },
      body: opts.body && !(opts.body instanceof FormData) && typeof opts.body !== 'string'
        ? JSON.stringify(opts.body)
        : opts.body,
    });

    if (res.status === 401 && _retry && !path.startsWith('/auth/')) {
      const ok = await refreshOnce();
      if (ok) return rawFetch(path, opts, false);
    }

    if (res.status === 204) return null;

    let data = null;
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      data = await res.json().catch(() => null);
    } else {
      data = await res.text().catch(() => null);
    }
    if (!res.ok) {
      const detail = data && data.detail != null ? data.detail : data || res.statusText;
      throw new ApiError(res.status, detail);
    }
    return data;
  }

  /* ── typed wrappers ───────────────────────────────────────────────── */
  const API = {
    base,
    on,
    events,
    ApiError,
    fetch: rawFetch,

    /* auth */
    me: () => rawFetch('/auth/me'),
    login: (email, password) =>
      rawFetch('/auth/login', { method: 'POST', body: { email, password } }),
    register: (name, email, password) =>
      rawFetch('/auth/register', { method: 'POST', body: { name, email, password } }),
    logout: () => rawFetch('/auth/logout', { method: 'POST' }),
    refresh: () => refreshOnce(),

    /* identity */
    getIdentity: () => rawFetch('/identity/me'),

    /* scoring */
    computeDna: () => rawFetch('/score/dna'),
    computeIncomeQuality: () => rawFetch('/score/income-quality'),
    scoreHistory: (limit = 12) => rawFetch(`/score/history?limit=${limit}`),
    simulateTwin: (body) =>
      rawFetch('/score/twin/simulate', { method: 'POST', body }),

    /* lenders + opp */
    listOffers: (amount) =>
      rawFetch('/lenders/offers' + (amount ? `?amount=${amount}` : '')),
    listOpportunities: (limit = 6) =>
      rawFetch(`/opportunities?limit=${limit}`),

    /* aggregators */
    consent: (params = {}) => {
      const qs = new URLSearchParams();
      (params.fi_types || ['DEPOSIT']).forEach((f) => qs.append('fi_types', f));
      if (params.from_date) qs.set('from_date', params.from_date);
      if (params.to_date) qs.set('to_date', params.to_date);
      return rawFetch('/aggregators/consent?' + qs.toString(), { method: 'POST' });
    },
    pullConsent: (id) =>
      rawFetch(`/aggregators/consent/${encodeURIComponent(id)}/pull`, { method: 'POST' }),

    /* onboarding step helpers */
    onboard: {
      personal: (b) => rawFetch('/onboarding/personal', { method: 'POST', body: b }),
      occupation: (b) => rawFetch('/onboarding/occupation', { method: 'POST', body: b }),
      incomeSources: (b) =>
        rawFetch('/onboarding/income-sources', { method: 'POST', body: b }),
      banks: (b) => rawFetch('/onboarding/banks', { method: 'POST', body: b }),
      upi: (b) => rawFetch('/onboarding/upi', { method: 'POST', body: b }),
      gig: (b) => rawFetch('/onboarding/gig', { method: 'POST', body: b }),
      permissions: (b) => rawFetch('/onboarding/permissions', { method: 'POST', body: b }),
      finish: () => rawFetch('/onboarding/finish', { method: 'POST' }),
    },
  };

  /* ============================================================
     STORE — same public surface as assets/store.js but backed
     by the API. Cached identity + DNA; `set(patch)` posts to the
     matching /onboarding endpoint, then re-fetches.
     ============================================================ */

  const defaults = () => ({
    onboarded: false,
    personal: { name: '', dob: '', city: '', phone: '', email: '' },
    occupation: '',
    incomeSources: [],
    banks: { primary: '', uploaded: '' },
    upi: [],
    gigPlatforms: [],
    goals: [],
    annualGoal: 1500000,
    permissions: { email: true, push: true, lenderShare: true, aiTrainer: false },
  });

  /* same catalogs as store.js — wizard renders instantly without a fetch */
  const CATALOGS = {
    SOURCES: [
      { i: '💼', n: 'Client Projects', d: 'Direct contracts & freelance' },
      { i: '🏢', n: 'Salaried role', d: 'Full-time or part-time job' },
      { i: '🛵', n: 'Gig Platforms', d: 'Uber, Zomato, Rapido' },
      { i: '🛒', n: 'Online Sales', d: 'Etsy, Amazon, Shopify' },
      { i: '📈', n: 'Investments', d: 'Dividends, interest, capital gains' },
      { i: '🏠', n: 'Rental Income', d: 'Property & sublets' },
    ],
    UPI_APPS: ['PhonePe', 'Google Pay', 'Paytm', 'BHIM', 'Amazon Pay'],
    GIG: ['Uber', 'Zomato', 'Swiggy', 'Rapido', 'Urban Company', 'YouTube', 'Spotify', 'Flipkart', 'Instagram'],
    GOALS: ['Home Loan', 'Emergency Fund', 'Tax Savings', 'Retirement', 'Business Loan', 'Higher Studies', 'Vacation', 'New Gadget', 'Wedding', 'Health Insurance'],
    CITIES: ['Mumbai', 'Bengaluru', 'Delhi', 'Pune', 'Hyderabad', 'Chennai', 'Kolkata', 'Ahmedabad'],
    BANKS: ['HDFC', 'ICICI', 'Axis', 'SBI', 'Kotak', 'Yes Bank', 'IndusInd', 'Federal', 'IDFC', 'PNB'],
  };

  let _state = defaults();
  let _dna = null;             // last /score/dna payload
  let _iq = null;              // last /score/income-quality payload
  let _loaded = false;
  const _readyResolvers = [];
  const ready = new Promise((resolve) => _readyResolvers.push(resolve));

  function serverToState(s) {
    if (!s) return defaults();
    const banks = Array.isArray(s.banks) ? s.banks : [];
    const primary = banks.find((b) => b && b.primary) || banks[0] || null;
    return {
      onboarded: !!s.onboarded,
      personal: {
        name: s.name || '',
        dob: s.dob || '',
        city: s.city || '',
        phone: s.phone || '',
        email: s.email || '',
      },
      occupation: s.occupation || '',
      incomeSources: s.sources || [],
      banks: {
        primary: primary ? primary.bank : '',
        uploaded: '',
      },
      upi: s.upi_apps || s.upiApps || [],
      gigPlatforms: s.gig_platforms || s.gigPlatforms || [],
      goals: s.goals || [],
      annualGoal: s.annual_goal || s.annualGoal || 1500000,
      permissions: {
        email: true,
        push: !!(s.permissions && s.permissions.push),
        lenderShare: true,
        aiTrainer: false,
      },
      _raw: s,
    };
  }

  async function _load() {
    try {
      // me first — if 401 the user is logged out, keep defaults
      await API.me();
      const [identity, dna, iq] = await Promise.all([
        API.getIdentity(),
        API.computeDna().catch(() => null),
        API.computeIncomeQuality().catch(() => null),
      ]);
      _state = serverToState(identity);
      _dna = dna;
      _iq = iq;
      _loaded = true;
      emit('storechange', _state);
    } catch (e) {
      // unauthenticated or backend down — keep defaults but mark loaded so
      // pages can render their "you must sign in" state
      _state = defaults();
      _loaded = true;
      emit('storechange', _state);
      throw e;
    } finally {
      while (_readyResolvers.length) _readyResolvers.shift()();
    }
  }

  function dnaToDerived(dna) {
    if (!dna) return null;
    return {
      monthlyIncome: dna.monthlyIncome,
      clients: dna.clients || [],
      sortedClients: dna.sortedClients || [],
      topClientShare: dna.topClientShare,
      herfindahl: dna.herfindahl,
      diversificationIndex: dna.diversificationIndex,
      stability: dna.stability,
      discipline: dna.discipline,
      growth: dna.growth,
      savings: dna.savings,
      diversification: dna.diversification,
      risk: dna.risk,
      dnaScore: dna.dnaScore,
      incomeQuality: _iq ? _iq.incomeQuality : 0,
      cv: _iq ? _iq.cv : 0,
      yoy: _iq ? _iq.yoy : 0,
      latePayouts: _iq ? _iq.latePayouts : 0,
    };
  }

  const STORE = {
    /* ── state surface ── */
    get: () => JSON.parse(JSON.stringify(_state)),
    set: async (patch) => {
      // Best-effort: dispatch optimistically, then call any matching onboard
      // endpoint, then refetch.
      const tasks = [];
      if (patch.personal) tasks.push(API.onboard.personal(patch.personal).catch(() => null));
      if (patch.occupation || patch.annualGoal) {
        tasks.push(API.onboard.occupation({
          occupation: patch.occupation || _state.occupation || 'freelancer',
          annual_goal: patch.annualGoal || _state.annualGoal,
        }).catch(() => null));
      }
      if (patch.incomeSources) {
        const payload = (patch.incomeSources || []).map((name, i) => ({
          name,
          monthly_income: Math.round((_state.annualGoal || 1500000) / 12 / Math.max(1, patch.incomeSources.length)),
          primary: i === 0,
        }));
        tasks.push(API.onboard.incomeSources(payload).catch(() => null));
      }
      if (patch.gigPlatforms) tasks.push(API.onboard.gig(patch.gigPlatforms.map((p) => ({ platform: p }))).catch(() => null));
      if (patch.upi) tasks.push(API.onboard.upi(patch.upi.map((u) => ({ provider: u }))).catch(() => null));
      if (patch.goals) {
        // goals aren't a step yet; treat as no-op
      }
      if (patch.permissions) {
        const p = _state.permissions || {};
        tasks.push(API.onboard.permissions({
          push: !!(patch.permissions.push ?? p.push),
          primary_bank: !!(patch.permissions.primary_bank ?? p.primary_bank),
          aa_consent: !!(patch.permissions.aa_consent ?? p.aa_consent),
        }).catch(() => null));
      }
      if (patch.onboarded === true) tasks.push(API.onboard.finish().catch(() => null));

      await Promise.all(tasks);
      await _load();
      return _state;
    },
    reset: async () => {
      try { await API.logout(); } catch (e) { /* fine */ }
      _state = defaults();
      _dna = null;
      _iq = null;
      _loaded = false;
      emit('logout');
      emit('storechange', _state);
    },
    isOnboarded: () => !!_state.onboarded,
    computeDerived: () => dnaToDerived(_dna),
    catalogs: CATALOGS,

    /* ── api helpers exposed through STORE for one-call convenience ── */
    api: API,
    ready,
    _load,

    /* internal — exposed for renderers that want to refetch */
    invalidate: () => { _loaded = false; },
  };

  window.API = API;
  window.STORE = STORE;
  window.fiaReady = ready;
  window.fiaApiError = ApiError;

  /* ── tiny loading-flag helpers ───────────────────────────────────── */
  let inflight = 0;
  const origFetch = rawFetch;
  const trackedFetch = async function (...args) {
    inflight++;
    document.documentElement.setAttribute('data-fia-loading', String(inflight));
    document.dispatchEvent(new CustomEvent('fia:loading', { detail: inflight }));
    try {
      return await origFetch(...args);
    } finally {
      inflight = Math.max(0, inflight - 1);
      document.documentElement.setAttribute('data-fia-loading', String(inflight));
      if (inflight === 0) document.dispatchEvent(new CustomEvent('fia:loading:done'));
    }
  };
  API.fetch = trackedFetch;

  /* Kick off the initial load as soon as api.js is on the page. Pages that
     need the data listen on `fiaReady` or the `storechange` event. */
  _load().catch((e) => console.warn('[api] initial load failed', e && e.message));
})();