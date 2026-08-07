/* ============================================================
   FIA STORE — single source of truth for user identity
   Backed by localStorage. Fires `storechange` on every write.
   ============================================================ */

const STORE = (() => {
  const KEY = 'fia_identity_v1';

  /* ----- Defaults ----- */
  const defaults = () => ({
    onboarded: false,
    personal: {
      name: '',
      dob: '',
      city: 'Mumbai',
      phone: '',
      email: '',
    },
    occupation: '',
    incomeSources: [],
    banks: {
      primary: '',
      uploaded: '',
    },
    upi: [],
    gigPlatforms: [],
    goals: [],
    annualGoal: 1500000,
    permissions: {
      email: true,
      push: true,
      lenderShare: true,
      aiTrainer: false,
    },
  });

  /* ----- Read / write ----- */
  const read = () => {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return defaults();
      const parsed = JSON.parse(raw);
      /* merge in case shape grew between versions */
      return Object.assign(defaults(), parsed);
    } catch (e) {
      console.warn('[STORE] corrupt data, resetting', e);
      return defaults();
    }
  };

  let _state = read();

  const get = () => JSON.parse(JSON.stringify(_state));

  const set = (patch) => {
    _state = Object.assign({}, _state, patch);
    localStorage.setItem(KEY, JSON.stringify(_state));
    document.dispatchEvent(new CustomEvent('storechange', { detail: get() }));
    return _state;
  };

  const reset = () => {
    localStorage.removeItem(KEY);
    _state = defaults();
    document.dispatchEvent(new CustomEvent('storechange', { detail: get() }));
  };

  const isOnboarded = () => !!_state.onboarded;

  /* ----- Canonical catalogs ----- */
  const SOURCES = [
    { i: '💼', n: 'Client Projects', d: 'Direct contracts & freelance' },
    { i: '🏢', n: 'Salaried role', d: 'Full-time or part-time job' },
    { i: '🛵', n: 'Gig Platforms', d: 'Uber, Zomato, Rapido' },
    { i: '🛒', n: 'Online Sales', d: 'Etsy, Amazon, Shopify' },
    { i: '📈', n: 'Investments', d: 'Dividends, interest, capital gains' },
    { i: '🏠', n: 'Rental Income', d: 'Property & sublets' },
  ];
  const UPI_APPS = ['PhonePe', 'Google Pay', 'Paytm', 'BHIM', 'Amazon Pay'];
  const GIG = ['Uber', 'Zomato', 'Swiggy', 'Rapido', 'Urban Company', 'YouTube', 'Spotify', 'Flipkart', 'Instagram'];
  const GOALS = ['Home Loan', 'Emergency Fund', 'Tax Savings', 'Retirement', 'Business Loan', 'Higher Studies', 'Vacation', 'New Gadget', 'Wedding', 'Health Insurance'];
  const CITIES = ['Mumbai', 'Bengaluru', 'Delhi', 'Pune', 'Hyderabad', 'Chennai', 'Kolkata', 'Ahmedabad'];
  const BANKS = ['HDFC', 'ICICI', 'Axis', 'SBI', 'Kotak', 'Yes Bank', 'IndusInd', 'Federal', 'IDFC', 'PNB'];

  /* ----- Derived metrics (pure) ----- */
  const computeDerived = (s = _state) => {
    const sources = s.incomeSources || [];
    const n = sources.length;
    const monthlyIncome = Math.round((s.annualGoal || 1500000) / 12);

    /* Build the "client" list. Every selected income source becomes
       a client. Client Projects is split into 1 synthetic "Client A"
       so we have a proper top-client signal. */
    const clients = [];
    if (sources.includes('Client Projects')) clients.push({ name: 'Client A', kind: 'project', share: 70 });
    if (sources.includes('Salaried role')) clients.push({ name: 'Employer', kind: 'salary', share: 100 });
    if (sources.includes('Gig Platforms')) {
      /* split across selected gig platforms */
      const gigs = (s.gigPlatforms || []).slice(0, 3);
      const gigsToShow = gigs.length ? gigs : ['Zomato'];
      const shareEach = 100 / gigsToShow.length;
      gigsToShow.forEach(g => clients.push({ name: g, kind: 'gig', share: shareEach }));
    }
    if (sources.includes('Online Sales')) clients.push({ name: 'Marketplace', kind: 'sales', share: 60 });
    if (sources.includes('Investments')) clients.push({ name: 'Portfolio', kind: 'investment', share: 100 });
    if (sources.includes('Rental Income')) clients.push({ name: 'Tenants', kind: 'rental', share: 100 });

    /* Re-normalize shares to sum to 100 */
    const totalShare = clients.reduce((a, c) => a + c.share, 0) || 1;
    clients.forEach(c => c.share = +(c.share / totalShare * 100).toFixed(1));

    const sortedClients = [...clients].sort((a, b) => b.share - a.share);
    const topClientShare = sortedClients.length ? sortedClients[0].share : 0;
    const herfindahl = Math.round(clients.reduce((a, c) => a + Math.pow(c.share, 2), 0));
    const diversificationIndex = n <= 1 ? 18 : Math.min(95, 30 + (n - 1) * 12 + (sortedClients.length > 2 ? 8 : 0));

    /* sub-scores 0-100 */
    const stability = Math.max(30, 100 - Math.round(topClientShare * 0.5));         // single-source = ~50
    const discipline = s.permissions.push ? 78 : 70;                                  // demo heuristic
    const growth = Math.min(95, 65 + n * 4);                                           // more sources → faster growth
    const savings = sources.includes('Investments') ? 76 : sources.includes('Salaried role') ? 68 : 54;
    const diversification = diversificationIndex;                                     // alias
    const risk = Math.max(35, 95 - Math.round(topClientShare * 0.6) - (s.banks.primary ? 0 : 6));

    /* DNA weighted blend: stability 30, discipline 20, growth 15, savings 15, diversification 10, risk 10 */
    const dnaScore = Math.round(
      stability * 0.30 +
      discipline * 0.20 +
      growth * 0.15 +
      savings * 0.15 +
      diversification * 0.10 +
      risk * 0.10
    );

    /* Income quality 0-100: penalises single-source, rewards gig platforms & investments */
    let incomeQuality = 70;
    if (n === 0) incomeQuality = 0;
    else if (n === 1) incomeQuality = 35;
    else if (n === 2) incomeQuality = 55;
    else if (n >= 4) incomeQuality = 82;
    if (sources.includes('Gig Platforms') && (s.gigPlatforms || []).length >= 2) incomeQuality += 6;
    if (sources.includes('Investments')) incomeQuality += 4;
    if (topClientShare > 60) incomeQuality -= 12;
    if (topClientShare > 80) incomeQuality -= 10;
    incomeQuality = Math.max(0, Math.min(100, incomeQuality));

    /* Coefficient of variation — synthetic, lower when diversified */
    const cv = n <= 1 ? 24 : n === 2 ? 16 : n === 3 ? 11 : 7;

    /* YoY growth synthetic */
    const yoy = 6 + n * 2;

    /* Late payouts synthetic, lower when stable */
    const latePayouts = Math.max(0.5, +(8 - n * 1.2).toFixed(1));

    return {
      monthlyIncome,
      clients,
      sortedClients,
      topClientShare,
      herfindahl,
      diversificationIndex,
      stability,
      discipline,
      growth,
      savings,
      risk,
      dnaScore,
      incomeQuality,
      cv,
      yoy,
      latePayouts,
    };
  };

  /* Public */
  return {
    get,
    set,
    reset,
    isOnboarded,
    computeDerived,
    /* exposed catalogs so renderers & onboarding stay in sync */
    catalogs: { SOURCES, UPI_APPS, GIG, GOALS, CITIES, BANKS },
  };
})();

window.STORE = STORE;