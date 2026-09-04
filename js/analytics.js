(() => {
function ratio(n, d) { return n == null || d == null || d === 0 ? null : n / d; }

function isSeatMeasured(s) {
  return Boolean(s?.quality?.seatMeasured && Number.isInteger(s?.seat?.capacity) && s.seat.capacity > 0 && Number.isInteger(s?.seat?.used));
}

function sessionBand(session, methodology) {
  const hhmm = session.startAt.slice(11, 16);
  const bands = methodology.timeBands || [];
  return bands.find(b => hhmm >= b.start && hhmm < b.endExclusive)?.id || 'late';
}

function filterSessions(sessions, scope, registry, methodology) {
  const byId = new Map(registry.map(c => [c.id, c]));
  return sessions.filter(session => {
    const cinema = byId.get(session.cinemaId);
    if (!cinema) return false;
    if (scope.exhibitor !== 'all' && cinema.exhibitorId !== scope.exhibitor) return false;
    if (scope.state !== 'all' && cinema.state !== scope.state) return false;
    if (scope.time !== 'all' && sessionBand(session, methodology) !== scope.time) return false;
    return true;
  });
}

function scopedCinemas(registry, scope) {
  return registry.filter(cinema =>
    (scope.exhibitor === 'all' || cinema.exhibitorId === scope.exhibitor) &&
    (scope.state === 'all' || cinema.state === scope.state)
  );
}

function aggregate(sessions, methodology) {
  const measured = sessions.filter(isSeatMeasured);
  const capacity = measured.reduce((a, s) => a + s.seat.capacity, 0);
  const used = measured.reduce((a, s) => a + s.seat.used, 0);
  const availableVals = measured.map(s => s.seat.available).filter(Number.isInteger);
  const otherVals = measured.map(s => s.seat.otherUnavailable).filter(Number.isInteger);
  const prime = sessions.filter(s => sessionBand(s, methodology) === 'prime');
  const primeMeasured = prime.filter(isSeatMeasured);
  const primeCap = primeMeasured.reduce((a, s) => a + s.seat.capacity, 0);
  const primeUsed = primeMeasured.reduce((a, s) => a + s.seat.used, 0);
  return {
    totalShows: sessions.length,
    locationsWithConfirmedShows: new Set(sessions.map(s => s.cinemaId)).size,
    seatMeasuredSessions: measured.length,
    observedCapacity: measured.length ? capacity : null,
    observedUsed: measured.length ? used : null,
    available: availableVals.length ? availableVals.reduce((a, b) => a + b, 0) : null,
    otherUnavailable: otherVals.length ? otherVals.reduce((a, b) => a + b, 0) : null,
    occupancy: ratio(used, capacity),
    averageUsedPerMeasuredSession: ratio(used, measured.length),
    averageCapacityPerMeasuredSession: ratio(capacity, measured.length),
    primeTimeShows: prime.length,
    primeTimeOccupancy: ratio(primeUsed, primeCap),
    seatCoverage: ratio(measured.length, sessions.length),
  };
}

function cinemaRows(sessions, registry, scope, methodology, changes = {}) {
  const cinemas = scopedCinemas(registry, scope);
  const total = aggregate(sessions, methodology);
  const rows = cinemas.map(cinema => {
    const own = sessions.filter(s => s.cinemaId === cinema.id);
    const m = aggregate(own, methodology);
    const showShare = ratio(m.totalShows, total.totalShows);
    const seatShare = ratio(m.observedCapacity, total.observedCapacity);
    const usedShare = ratio(m.observedUsed, total.observedUsed);
    const performanceIndex = usedShare != null && seatShare != null ? ratio(usedShare, seatShare) : null;
    const changeValues = own.map(s => changes[s.sessionId]).filter(Boolean);
    const deltas = changeValues.map(c => c.usedDelta).filter(v => typeof v === 'number');
    const velocities = changeValues.map(c => c.seatsPerHour).filter(v => typeof v === 'number' && Number.isFinite(v));
    const latestObserved = own.map(s => s.collectedAt).sort().at(-1) || null;
    return {
      ...cinema, ...m, showShare, seatShare, usedShare, performanceIndex,
      usedDelta: deltas.length ? deltas.reduce((a, b) => a + b, 0) : null,
      averageSessionVelocity: velocities.length ? velocities.reduce((a, b) => a + b, 0) / velocities.length : null,
      velocityCoverage: velocities.length,
      latestObserved,
    };
  });
  return rows;
}

function exhibitorRows(sessions, exhibitors, registry, scope, methodology) {
  const all = aggregate(sessions, methodology);
  return exhibitors
    .filter(e => scope.exhibitor === 'all' || e.id === scope.exhibitor)
    .map(ex => {
      const own = sessions.filter(s => s.exhibitorId === ex.id);
      const m = aggregate(own, methodology);
      return { ...ex, ...m, showShare: ratio(m.totalShows, all.totalShows), seatShare: ratio(m.observedCapacity, all.observedCapacity) };
    })
    .filter(row => row.totalShows > 0 || registry.some(c => c.exhibitorId === row.id));
}

function occupancyDistribution(sessions, bands) {
  const measured = sessions.filter(isSeatMeasured);
  const out = bands.map(band => ({ ...band, count: 0, share: null }));
  for (const session of measured) {
    const value = session.seat.used / session.seat.capacity;
    const band = out.find(b => {
      const lower = b.minInclusive != null ? value >= b.minInclusive : value > b.minExclusive;
      const upper = b.maxInclusive != null ? value <= b.maxInclusive : value < b.maxExclusive;
      return lower && upper;
    });
    if (band) band.count += 1;
  }
  for (const row of out) row.share = ratio(row.count, measured.length);
  return out;
}

  Object.assign(window.TIKUS_DI = window.TIKUS_DI || {}, { isSeatMeasured, sessionBand, filterSessions, scopedCinemas, aggregate, cinemaRows, exhibitorRows, occupancyDistribution });
})();
