(() => {
  const root = window.TIKUS_DI = window.TIKUS_DI || {};
  const JSON_OPTIONS = { cache: 'no-store' };

  async function getJson(path) {
    const response = await fetch(path, JSON_OPTIONS);
    if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
    return response.json();
  }

  async function loadBootstrap() {
    if (location.protocol === 'file:') {
      if (!window.TIKUS_BROWSER_DATA) throw new Error('Local compatibility data is missing: data/browser-data.js');
      const b = window.TIKUS_BROWSER_DATA;
      return { current:b.current, index:b.index, cinemas:b.cinemas, exhibitors:b.exhibitors, methodology:b.methodology, status:b.status };
    }
    const [current, index, cinemas, exhibitors, methodology, status] = await Promise.all([
      getJson('data/current.json'), getJson('data/index.json'), getJson('data/meta/cinemas.json'),
      getJson('data/meta/exhibitors.json'), getJson('data/meta/methodology.json'),
      getJson('data/status.json').catch(() => ({ latestRun: null })),
    ]);
    return { current, index, cinemas, exhibitors, methodology, status };
  }

  async function loadDateProduct(date, index, current) {
    if (!date || current.showDate === date) return current;
    if (!(index.availableDates || []).includes(date)) throw new Error(`No stored observations for ${date}`);
    if (location.protocol === 'file:') {
      const day = window.TIKUS_BROWSER_DATA?.days?.[date];
      if (!day) throw new Error(`Local day product missing for ${date}`);
      return day;
    }
    return getJson(`data/days/${date}.json`);
  }

  async function loadTrendProducts(index, current) {
    const dates = index.availableDates || [];
    return Promise.all(dates.map(date => loadDateProduct(date, index, current)));
  }

  Object.assign(root, { loadBootstrap, loadDateProduct, loadTrendProducts });
})();
