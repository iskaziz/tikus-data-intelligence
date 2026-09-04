(() => {
  const root = window.TIKUS_DI = window.TIKUS_DI || {};
  root.fmt = {
    int(value) { return value == null ? '—' : new Intl.NumberFormat('en-MY').format(value); },
    pct(value, digits = 1) { return value == null ? '—' : `${(value * 100).toFixed(digits)}%`; },
    ratio(value) { return value == null ? '—' : `${value.toFixed(2)}×`; },
    avg(value) { return value == null ? '—' : value.toFixed(1); },
    signed(value, digits = 0) {
      if (value == null || !Number.isFinite(value)) return '—';
      const n = digits ? value.toFixed(digits) : Math.round(value).toString();
      return `${value > 0 ? '+' : ''}${n}`;
    },
    time(iso) {
      if (!iso) return '—';
      const d = new Date(iso);
      return new Intl.DateTimeFormat('en-MY', { hour: '2-digit', minute: '2-digit', hour12: false }).format(d);
    },
    datetime(iso) {
      if (!iso) return '—';
      const d = new Date(iso);
      return new Intl.DateTimeFormat('en-MY', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Kuala_Lumpur' }).format(d);
    },
  };
})();
