(() => {
const { loadBootstrap, loadDateProduct, loadTrendProducts, aggregate, cinemaRows, exhibitorRows, filterSessions, occupancyDistribution, scopedCinemas, fmt } = window.TIKUS_DI;

const state = {
  bootstrap: null,
  product: null,
  trendProducts: [],
  scope: { date: null, time: 'all', exhibitor: 'all', state: 'all', observation: 'latest', replay: null },
  search: '',
  sort: { key: 'observedUsed', direction: 'desc' },
  visibleColumns: new Set(['rank','cinema','shows','showShare','capacity','used','occupancy','avgUsed','primeShows','primeOccupancy','performanceIndex','usedDelta']),
  comparisonCinemaIds: [],
  restoringUrlState: false,
};

const columns = [
  ['rank','#','rank','ordinal'], ['cinema','Cinema','name','text'], ['exhibitor','Exhibitor','exhibitorId','text'], ['state','State','state','text'],
  ['shows','Shows','totalShows','int'], ['showShare','Show Share','showShare','pct'], ['measured','Seat Measured','seatMeasuredSessions','coverage'],
  ['capacity','Capacity','observedCapacity','int'], ['seatShare','Seat Share','seatShare','pct'], ['used','Used / Booked','observedUsed','int'],
  ['available','Available','available','int'], ['occupancy','Occupancy','occupancy','pct'], ['avgUsed','Avg Used','averageUsedPerMeasuredSession','avg'],
  ['avgCapacity','Avg Capacity','averageCapacityPerMeasuredSession','avg'], ['primeShows','Prime Shows','primeTimeShows','int'], ['primeOccupancy','Prime Occ.','primeTimeOccupancy','pct'],
  ['performanceIndex','Perf. Index','performanceIndex','ratio'], ['usedDelta','Latest Δ','usedDelta','signed'], ['velocity','Avg Velocity','averageSessionVelocity','velocity'],
  ['lastObserved','Last Observed','latestObserved','datetime']
].map(([id,label,key,type]) => ({id,label,key,type}));

const bandLabels = { zero:'0%', 'very-low':'>0–10%', low:'>10–25%', moderate:'>25–50%', strong:'>50–75%', 'very-strong':'>75–90%', 'near-full':'>90%' };
const geoPositions = {
  'Pulau Pinang':['pen',20,24,'PNG'], Kedah:['pen',34,12,'KDH'], Terengganu:['pen',70,31,'TRG'], Pahang:['pen',61,48,'PHG'],
  'Kuala Lumpur':['pen',43,56,'KUL'], Selangor:['pen',34,58,'SEL'], Putrajaya:['pen',47,66,'PJY'], Melaka:['pen',50,76,'MLK'], Johor:['pen',61,88,'JHR'],
  Sarawak:['borneo',39,67,'SWK'], Sabah:['borneo',73,29,'SBH']
};

const $ = selector => document.querySelector(selector);
const el = (tag, className, text) => { const n=document.createElement(tag); if(className)n.className=className; if(text!=null)n.textContent=text; return n; };

async function init() {
  try {
    state.bootstrap = await loadBootstrap();
    state.product = state.bootstrap.current;
    state.scope.date = state.product.showDate || state.bootstrap.index.latestDate;
    const restored = parseUrlState();
    if (restored.date && restored.date !== state.scope.date && (state.bootstrap.index.availableDates || []).includes(restored.date)) {
      state.product = await loadDateProduct(restored.date, state.bootstrap.index, state.bootstrap.current);
      state.scope.date = restored.date;
    }
    applyParsedUrlState(restored);
    setupControls();
    state.trendProducts = await loadTrendProducts(state.bootstrap.index, state.bootstrap.current).catch(() => []);
    render();
  } catch (error) {
    showError(error.message || String(error));
    renderEmptyShell();
  }
}

function setupControls() {
  const { index, cinemas, exhibitors } = state.bootstrap;
  const date = $('#date-filter');
  date.innerHTML = '';
  const dates = index.availableDates || [];
  if (!dates.length) date.append(new Option('No observations yet', ''));
  dates.slice().reverse().forEach(d => date.append(new Option(dateLabel(d, index.releaseDate), d)));
  date.value = state.scope.date || '';
  date.addEventListener('change', async () => {
    if (!date.value) return;
    state.scope.date = date.value;
    state.product = await loadDateProduct(date.value, index, state.bootstrap.current);
    populateReplayControl();
    render();
  });

  const exhib = $('#exhibitor-filter');
  exhibitors.exhibitors.forEach(e => exhib.append(new Option(e.name, e.id)));
  exhib.value = state.scope.exhibitor;
  exhib.addEventListener('change', () => { state.scope.exhibitor = exhib.value; render(); });

  const states = [...new Set(cinemas.cinemas.map(c => c.state))].sort();
  const stateSelect = $('#state-filter');
  states.forEach(name => stateSelect.append(new Option(name, name)));
  stateSelect.value = state.scope.state;
  stateSelect.addEventListener('change', () => { state.scope.state = stateSelect.value; render(); });

  $('#time-filter').value = state.scope.time;
  $('#observation-filter').value = state.scope.observation;
  $('#time-filter').addEventListener('change', e => { state.scope.time = e.target.value; render(); });
  $('#observation-filter').addEventListener('change', e => { state.scope.observation = e.target.value; updateReplayVisibility(); render(); });
  $('#replay-time-filter').addEventListener('change', e => { state.scope.replay = e.target.value || null; render(); });
  $('#cinema-search').addEventListener('input', e => { state.search = e.target.value.toLowerCase().trim(); renderTable(); });
  $('#reset-filters').addEventListener('click', () => {
    state.scope.time='all'; state.scope.exhibitor='all'; state.scope.state='all'; state.scope.observation='latest'; state.scope.replay=null; state.search='';
    $('#time-filter').value='all'; $('#exhibitor-filter').value='all'; $('#state-filter').value='all'; $('#observation-filter').value='latest'; $('#cinema-search').value=''; populateReplayControl(); updateReplayVisibility();
    render();
  });
  populateReplayControl();
  updateReplayVisibility();
  setupColumnMenu();
  $('#column-toggle').addEventListener('click', () => {
    const menu=$('#column-menu'); const open=menu.hidden; menu.hidden=!open; $('#column-toggle').setAttribute('aria-expanded', String(open));
  });
  $('#session-dialog .dialog-close').addEventListener('click', () => $('#session-dialog').close());
  $('#session-dialog').addEventListener('click', e => { if (e.target === $('#session-dialog')) $('#session-dialog').close(); });
  $('#trajectory-session-filter').addEventListener('change', e => renderScreeningTrajectory(e.target.value));
  const autoCompare=$('#comparison-auto'); if(autoCompare) autoCompare.addEventListener('click',()=>{ seedComparison(true); renderCinemaComparison(); });
  const exportCsv=$('#comparison-export-csv'); if(exportCsv) exportCsv.addEventListener('click', exportCinemaComparisonCsv);
  const printComparison=$('#comparison-print'); if(printComparison) printComparison.addEventListener('click', printCinemaComparison);
  const copyShare=$('#comparison-copy-link'); if(copyShare) copyShare.addEventListener('click', copyShareLink);
  window.addEventListener('hashchange', restoreFromHashChange);
}




function parseUrlState() {
  const raw=window.location.hash.startsWith('#')?window.location.hash.slice(1):window.location.hash;
  const params=new URLSearchParams(raw);
  const compare=(params.get('compare')||'').split(',').map(v=>v.trim()).filter(Boolean).slice(0,4);
  return {
    date: params.get('date') || null,
    time: params.get('time') || null,
    exhibitor: params.get('exhibitor') || null,
    state: params.get('state') || null,
    observation: params.get('obs') || null,
    replay: params.get('replay') || null,
    compare,
  };
}

function applyParsedUrlState(parsed) {
  const validTimes=new Set(['all','matinee','prime','late']);
  const validObs=new Set(['latest','live','final','asof']);
  const exhibitorIds=new Set((state.bootstrap?.exhibitors?.exhibitors||[]).map(e=>e.id));
  const geography=new Set((state.bootstrap?.cinemas?.cinemas||[]).map(c=>c.state));
  const cinemaIds=new Set((state.bootstrap?.cinemas?.cinemas||[]).map(c=>c.id));
  if(parsed.time && validTimes.has(parsed.time)) state.scope.time=parsed.time;
  if(parsed.exhibitor && (parsed.exhibitor==='all'||exhibitorIds.has(parsed.exhibitor))) state.scope.exhibitor=parsed.exhibitor;
  if(parsed.state && (parsed.state==='all'||geography.has(parsed.state))) state.scope.state=parsed.state;
  if(parsed.observation && validObs.has(parsed.observation)) state.scope.observation=parsed.observation;
  if(parsed.replay) state.scope.replay=parsed.replay;
  if(parsed.compare?.length) state.comparisonCinemaIds=[...new Set(parsed.compare.filter(id=>cinemaIds.has(id)))].slice(0,4);
}

function encodedUrlState() {
  const params=new URLSearchParams();
  params.set('v','1');
  if(state.scope.date) params.set('date',state.scope.date);
  if(state.scope.time!=='all') params.set('time',state.scope.time);
  if(state.scope.exhibitor!=='all') params.set('exhibitor',state.scope.exhibitor);
  if(state.scope.state!=='all') params.set('state',state.scope.state);
  if(state.scope.observation!=='latest') params.set('obs',state.scope.observation);
  if(state.scope.observation==='asof' && state.scope.replay) params.set('replay',state.scope.replay);
  if(state.comparisonCinemaIds.length) params.set('compare',state.comparisonCinemaIds.slice(0,4).join(','));
  return params.toString();
}

function syncUrlState() {
  if(state.restoringUrlState) return;
  const hash=encodedUrlState();
  const next=`${window.location.pathname}${window.location.search}${hash?`#${hash}`:''}`;
  window.history.replaceState(null,'',next);
}

async function restoreFromHashChange() {
  if(state.restoringUrlState || !state.bootstrap) return;
  state.restoringUrlState=true;
  try {
    const parsed=parseUrlState();
    const targetDate=parsed.date;
    if(targetDate && targetDate!==state.scope.date && (state.bootstrap.index.availableDates||[]).includes(targetDate)) {
      state.product=await loadDateProduct(targetDate,state.bootstrap.index,state.bootstrap.current);
      state.scope.date=targetDate;
    }
    state.scope.time='all'; state.scope.exhibitor='all'; state.scope.state='all'; state.scope.observation='latest'; state.scope.replay=null; state.comparisonCinemaIds=[];
    applyParsedUrlState(parsed);
    $('#date-filter').value=state.scope.date||'';
    $('#time-filter').value=state.scope.time;
    $('#exhibitor-filter').value=state.scope.exhibitor;
    $('#state-filter').value=state.scope.state;
    $('#observation-filter').value=state.scope.observation;
    populateReplayControl(); updateReplayVisibility(); render();
  } finally { state.restoringUrlState=false; }
}

async function copyShareLink() {
  syncUrlState();
  const note=$('#comparison-note');
  const url=window.location.href;
  try {
    if(navigator.clipboard?.writeText) await navigator.clipboard.writeText(url);
    else {
      const area=document.createElement('textarea'); area.value=url; area.setAttribute('readonly',''); area.style.position='fixed'; area.style.opacity='0'; document.body.append(area); area.select(); document.execCommand('copy'); area.remove();
    }
    if(note) note.textContent=`Share link copied · ${comparisonScopeLabel()}.`;
  } catch {
    if(note) note.textContent='Could not copy automatically. Copy the current browser URL; it already contains this comparison state.';
  }
}

function populateReplayControl() {
  const select=$('#replay-time-filter'); if(!select) return;
  const checkpoints=state.product?.asOfReplay?.checkpoints||[];
  select.innerHTML='';
  if(!checkpoints.length){ select.append(new Option('No replay checkpoints', '')); state.scope.replay=null; return; }
  checkpoints.forEach(cp=>select.append(new Option(`${cp.label} MYT`,cp.id)));
  const exists=checkpoints.some(cp=>cp.id===state.scope.replay);
  state.scope.replay=exists?state.scope.replay:checkpoints[checkpoints.length-1].id;
  select.value=state.scope.replay;
}

function updateReplayVisibility() {
  const label=$('#replay-time-label'); if(!label) return;
  label.hidden=state.scope.observation!=='asof';
}

function activeReplay() {
  if(state.scope.observation!=='asof') return null;
  const checkpoints=state.product?.asOfReplay?.checkpoints||[];
  return checkpoints.find(cp=>cp.id===state.scope.replay) || checkpoints[checkpoints.length-1] || null;
}

function currentIntelligence() { return activeReplay()?.intelligence || state.product.intelligence || {}; }
function currentSessionChanges() { return activeReplay()?.sessionChanges || state.product.sessionChanges || {}; }

function setupColumnMenu() {
  const menu=$('#column-menu'); menu.innerHTML='';
  columns.filter(c => !['rank','cinema'].includes(c.id)).forEach(col => {
    const label=el('label'); const input=document.createElement('input'); input.type='checkbox'; input.checked=state.visibleColumns.has(col.id);
    input.addEventListener('change', () => { input.checked ? state.visibleColumns.add(col.id) : state.visibleColumns.delete(col.id); renderTable(); });
    label.append(input, document.createTextNode(col.label)); menu.append(label);
  });
}

function currentSessions() {
  const replay=activeReplay(); const base = state.scope.observation === 'final' ? (state.product.finalPreShowSessions || []) : state.scope.observation === 'live' ? (state.product.liveSessions || []) : state.scope.observation === 'asof' ? (replay?.sessions || []) : (state.product.sessions || []);
  return filterSessions(base, state.scope, state.bootstrap.cinemas.cinemas, state.bootstrap.methodology);
}

function render() {
  if (!state.bootstrap || !state.product) return;
  const sessions = currentSessions();
  const scoped = scopedCinemas(state.bootstrap.cinemas.cinemas, state.scope);
  const metrics = aggregate(sessions, state.bootstrap.methodology);
  renderFreshness(); renderScope(metrics, scoped); renderKpis(metrics, scoped.length); renderTable(); renderExhibitors(sessions); renderDistribution(sessions); renderMomentum(); renderPrimeEfficiency(); renderTrajectories(); renderCinemaComparison(); renderAllocation(); renderDecisionSignals(); renderTrend(); renderGeography(sessions); renderQuality();
  syncUrlState();
}

function renderFreshness() {
  const node=$('#freshness'); const dot=node.querySelector('.status-dot');
  const replay=activeReplay(); const when=replay?.asOf || state.product.observationWindow?.lastCollectedAt;
  dot.classList.toggle('is-live', Boolean(when));
  node.querySelector('span:last-child').textContent = when ? (replay ? `As-of replay ${fmt.datetime(when)} MYT · no later observations used` : `Last observed ${fmt.datetime(when)} MYT`) : 'No session observations stored yet';
}

function renderScope(metrics, scoped) {
  const parts=[];
  if(state.scope.exhibitor!=='all') parts.push(state.bootstrap.exhibitors.exhibitors.find(e=>e.id===state.scope.exhibitor)?.name);
  if(state.scope.state!=='all') parts.push(state.scope.state);
  if(state.scope.time!=='all') parts.push($('#time-filter').selectedOptions[0].textContent);
  $('#scope-label').textContent = `${parts.length ? parts.join(' · ') : 'Tracked network'} · ${scoped.length} cinema${scoped.length===1?'':'s'}`;
  const lateSeen = state.product.collection?.firstSeenAfterShowCount || 0;
  const correctionCount = state.product.quality?.excludedObservationCount || 0;
  const finalState = state.product.finalPreShowState?.status;
  const finalNote = state.scope.observation==='final' && finalState ? ` · final pre-show ${finalState}` : '';
  const replayNote = activeReplay() ? ` · replay cutoff ${activeReplay().label} MYT` : '';
  $('#coverage-note').textContent = metrics.totalShows ? `Seat measurement coverage ${metrics.seatMeasuredSessions}/${metrics.totalShows} sessions · ${fmt.pct(metrics.seatCoverage)}${lateSeen ? ` · ${lateSeen} session${lateSeen===1?'':'s'} first observed after showtime` : ''}${correctionCount ? ` · ${correctionCount} corrected observation${correctionCount===1?'':'s'} excluded` : ''}${finalNote}${replayNote}` : (state.scope.observation==='final' && finalState==='provisional' ? 'No finalized pre-show sessions yet · day remains provisional.' : 'No observed TIKUS! sessions in this scope.');
  $('#table-meta').textContent = `${metrics.totalShows} observed show${metrics.totalShows===1?'':'s'} · ${metrics.locationsWithConfirmedShows} location${metrics.locationsWithConfirmedShows===1?'':'s'} with shows · denominator follows scope filters, not search`;
}

function renderKpis(m, scopedCount) {
  const items = [
    ['Total Shows',fmt.int(m.totalShows),`${m.locationsWithConfirmedShows}/${scopedCount} locations`],
    ['Observed Capacity',fmt.int(m.observedCapacity),`${m.seatMeasuredSessions} measured sessions`],
    ['Used / Booked',fmt.int(m.observedUsed),'observed seat state'],
    ['Available',fmt.int(m.available),'direct / derived by source'],
    ['Occupancy',fmt.pct(m.occupancy),'capacity-weighted'],
    ['Avg Used / Session',fmt.avg(m.averageUsedPerMeasuredSession),'measured sessions only'],
    ['Prime Shows',fmt.int(m.primeTimeShows),'18:00–20:59 starts'],
    ['Prime Occupancy',fmt.pct(m.primeTimeOccupancy),'capacity-weighted'],
  ];
  const grid=$('#kpi-grid'); grid.innerHTML='';
  items.forEach(([label,value,detail])=>{ const n=el('article','kpi'); n.innerHTML=`<span class="kpi__label">${escapeHtml(label)}</span><strong class="kpi__value">${escapeHtml(value)}</strong><span class="kpi__detail">${escapeHtml(detail)}</span>`; grid.append(n); });
}

function renderTable() {
  if(!state.bootstrap || !state.product) return;
  const sessions=currentSessions();
  let rows=cinemaRows(sessions, state.bootstrap.cinemas.cinemas, state.scope, state.bootstrap.methodology, currentSessionChanges());
  if(state.search) rows=rows.filter(r=>`${r.name} ${r.city} ${r.state} ${r.exhibitorId}`.toLowerCase().includes(state.search));
  const {key,direction}=state.sort;
  rows.sort((a,b)=>compare(a[key],b[key],direction));
  rows.forEach((r,i)=>r.rank=i+1);
  const visible=columns.filter(c=>state.visibleColumns.has(c.id));
  const thead=$('#cinema-table thead'); const tbody=$('#cinema-table tbody'); thead.innerHTML=''; tbody.innerHTML='';
  const tr=el('tr'); visible.forEach(col=>{ const th=el('th'); if(col.id==='cinema') th.scope='col'; const button=el('button',null,col.label); button.type='button'; button.addEventListener('click',()=>sortBy(col.key)); th.append(button); th.setAttribute('aria-sort', state.sort.key===col.key ? (state.sort.direction==='asc'?'ascending':'descending') : 'none'); tr.append(th); }); thead.append(tr);
  rows.forEach(row=>{ const r=el('tr'); visible.forEach(col=>{ const td=el('td'); td.append(renderCell(row,col,sessions)); r.append(td); }); tbody.append(r); });
}

function renderCell(row,col,sessions) {
  if(col.id==='cinema') { const wrap=el('span'); const b=el('button','cinema-button',row.name); b.type='button'; b.addEventListener('click',()=>openCinema(row,sessions)); wrap.append(b, Object.assign(el('span','cell-sub'),{textContent:`${row.city} · ${row.state}`})); return wrap; }
  if(col.id==='exhibitor') return document.createTextNode(state.bootstrap.exhibitors.exhibitors.find(e=>e.id===row.exhibitorId)?.name || row.exhibitorId);
  if(col.id==='measured') return document.createTextNode(`${row.seatMeasuredSessions}/${row.totalShows}`);
  let text='—', cls='';
  if(col.type==='int') text=fmt.int(row[col.key]);
  else if(col.type==='pct') { text=fmt.pct(row[col.key]); cls='metric-share'; }
  else if(col.type==='ratio') { text=fmt.ratio(row[col.key]); cls='metric-ratio'; }
  else if(col.type==='avg') text=fmt.avg(row[col.key]);
  else if(col.type==='signed') { text=fmt.signed(row[col.key]); cls=`metric-change ${row[col.key]>0?'pos':row[col.key]<0?'neg':''}`; }
  else if(col.type==='velocity') { text=row[col.key]==null?'—':`${fmt.signed(row[col.key],1)}/hr`; cls='metric-change'; }
  else if(col.type==='datetime') text=fmt.datetime(row[col.key]);
  else text=row[col.key]??'—';
  const span=el('span', text==='—'?'na':cls, text); return span;
}

function sortBy(key) { if(state.sort.key===key) state.sort.direction=state.sort.direction==='desc'?'asc':'desc'; else { state.sort.key=key; state.sort.direction=['name','state','exhibitorId'].includes(key)?'asc':'desc'; } renderTable(); }
function compare(a,b,direction) { const nullA=a==null, nullB=b==null; if(nullA&&nullB)return 0; if(nullA)return 1; if(nullB)return -1; const v=typeof a==='string'?a.localeCompare(b):a-b; return direction==='asc'?v:-v; }

function renderExhibitors(sessions) {
  const rows=exhibitorRows(sessions,state.bootstrap.exhibitors.exhibitors,state.bootstrap.cinemas.cinemas,state.scope,state.bootstrap.methodology);
  const table=$('#exhibitor-table'); table.innerHTML='<thead><tr><th>Exhibitor</th><th>Shows</th><th>Show Share</th><th>Capacity</th><th>Used</th><th>Occ.</th><th>Seat Share</th></tr></thead>';
  const body=el('tbody'); rows.forEach(r=>{ const tr=el('tr'); [r.name,fmt.int(r.totalShows),fmt.pct(r.showShare),fmt.int(r.observedCapacity),fmt.int(r.observedUsed),fmt.pct(r.occupancy),fmt.pct(r.seatShare)].forEach(v=>{const td=el('td',v==='—'?'na':'',v);tr.append(td)}); body.append(tr); }); table.append(body);
}

function renderDistribution(sessions) {
  const rows=occupancyDistribution(sessions,state.bootstrap.methodology.occupancyBands||[]); const root=$('#occupancy-distribution'); root.innerHTML='';
  const max=Math.max(1,...rows.map(r=>r.count)); rows.forEach(r=>{ const n=el('div','dist-row'); n.innerHTML=`<span class="dist-label">${escapeHtml(bandLabels[r.id]||r.id)}</span><span class="dist-track"><span class="dist-fill" style="width:${(r.count/max)*100}%"></span></span><span class="dist-value">${r.count} · ${fmt.pct(r.share,0)}</span>`; root.append(n); });
  if(!sessions.some(s=>s.quality?.seatMeasured)) root.append(el('p','subtle','No seat-measured sessions in this scope.'));
}

function intelligenceCinemaAllowed(cinemaId) {
  const c=state.bootstrap.cinemas.cinemas.find(x=>x.id===cinemaId);
  if(!c) return false;
  if(state.scope.exhibitor!=='all' && c.exhibitorId!==state.scope.exhibitor) return false;
  if(state.scope.state!=='all' && c.state!==state.scope.state) return false;
  return true;
}

function cinemaName(cinemaId) {
  return state.bootstrap.cinemas.cinemas.find(x=>x.id===cinemaId)?.name || cinemaId;
}

function renderMomentum() {
  const table=$('#momentum-table'); if(!table) return;
  table.innerHTML='<thead><tr><th>Cinema</th><th>Measured Sessions</th><th>Net Δ Used</th><th>Avg Seats/hr</th><th>Peak Seats/hr</th></tr></thead>';
  const body=el('tbody');
  const rows=(currentIntelligence()?.cinemaMomentum||[]).filter(r=>intelligenceCinemaAllowed(r.cinemaId)).slice(0,10);
  rows.forEach(r=>{ const tr=el('tr'); [cinemaName(r.cinemaId),fmt.int(r.qualifyingSessions),fmt.signed(r.netUsedDelta),r.averageSeatsPerHour==null?'—':`${fmt.signed(r.averageSeatsPerHour,1)}/hr`,r.maxSeatsPerHour==null?'—':`${fmt.signed(r.maxSeatsPerHour,1)}/hr`].forEach(v=>tr.append(el('td',v==='—'?'na':'',v))); body.append(tr); });
  if(!rows.length){ const tr=el('tr'); const td=el('td','na','Momentum appears after sessions have at least two valid seat-state measurements.'); td.colSpan=5; tr.append(td); body.append(tr); }
  table.append(body);
}

function renderPrimeEfficiency() {
  const table=$('#prime-efficiency-table'); if(!table) return;
  table.innerHTML='<thead><tr><th>Cinema</th><th>Prime Shows</th><th>Measured</th><th>Prime Occ.</th><th>All-day Occ.</th><th>Δ pp</th></tr></thead>';
  const body=el('tbody');
  const rows=(currentIntelligence()?.primeTimeEfficiency||[]).filter(r=>intelligenceCinemaAllowed(r.cinemaId)&&r.primeShows>0).slice(0,12);
  rows.forEach(r=>{ const pp=r.occupancyDelta==null?'—':`${fmt.signed(r.occupancyDelta*100,2)} pp`; const tr=el('tr'); [cinemaName(r.cinemaId),fmt.int(r.primeShows),`${r.primeMeasuredSessions}/${r.primeShows}`,fmt.pct(r.primeOccupancy),fmt.pct(r.allDayOccupancy),pp].forEach(v=>tr.append(el('td',v==='—'?'na':'',v))); body.append(tr); });
  if(!rows.length){ const tr=el('tr'); const td=el('td','na','No prime-time sessions in this cinema/geography scope.'); td.colSpan=6; tr.append(td); body.append(tr); }
  table.append(body);
}


function renderTrajectories() {
  const table=$('#trajectory-table'); if(!table) return;
  const data=currentIntelligence()?.sessionTrajectories||{};
  const quality=$('#trajectory-quality');
  const rows=(data.cinemas||[]).filter(r=>intelligenceCinemaAllowed(r.cinemaId));
  const complete=rows.reduce((n,r)=>n+(r.completeTrajectories||0),0);
  const measured=rows.reduce((n,r)=>n+(r.measuredSessions||0),0);
  quality.textContent=measured?`${complete}/${measured} complete curves`:'No trajectory data';
  table.innerHTML='<thead><tr><th>Cinema</th><th>T−6h</th><th>T−3h</th><th>T−1h</th><th>Final</th><th>Δ 6h→Final</th><th>Complete</th></tr></thead>';
  const body=el('tbody');
  rows.forEach(r=>{
    const cp=r.checkpoints||{};
    const occ=k=>cp[k]?.occupancy==null?'—':fmt.pct(cp[k].occupancy);
    const lift=r.occupancyLift6hToFinal==null?'—':`${fmt.signed(r.occupancyLift6hToFinal*100,2)} pp`;
    const tr=el('tr'); [cinemaName(r.cinemaId),occ('tMinus6h'),occ('tMinus3h'),occ('tMinus1h'),occ('finalPreShow'),lift,`${r.completeTrajectories||0}/${r.measuredSessions||0}`].forEach(v=>tr.append(el('td',v==='—'?'na':'',v))); body.append(tr);
  });
  if(!rows.length){ const tr=el('tr'); const td=el('td','na','Trajectory checkpoints appear as comparable pre-show observations accumulate.'); td.colSpan=7; tr.append(td); body.append(tr); }
  table.append(body);
}



function selectedComparisonRecords() {
  const rows=comparisonRows();
  seedComparison(false);
  return state.comparisonCinemaIds
    .map(id=>rows.find(r=>r.id===id))
    .filter(Boolean)
    .slice(0,4)
    .map(row=>comparisonRecord(row));
}

function comparisonScopeLabel() {
  const replay=activeReplay();
  const parts=[`Show date ${state.product.showDate}`];
  if(state.scope.exhibitor!=='all') parts.push(`Exhibitor ${state.scope.exhibitor.toUpperCase()}`);
  if(state.scope.state!=='all') parts.push(`State ${state.scope.state}`);
  if(state.scope.time!=='all') parts.push(`Time ${state.scope.time}`);
  parts.push(replay?`As-of ${replay.label} MYT`:state.scope.observation==='final'?'Final pre-show':state.scope.observation==='live'?'Live / upcoming':'Latest eligible observations');
  return parts.join(' · ');
}

function csvEscape(value) {
  if(value==null) return '';
  const text=String(value);
  return /[",\n]/.test(text)?`"${text.replace(/"/g,'""')}"`:text;
}

function exportCinemaComparisonCsv() {
  const records=selectedComparisonRecords();
  const note=$('#comparison-note');
  if(records.length<2){ if(note) note.textContent='Select at least two seat-measured cinemas before exporting.'; return; }
  const replay=activeReplay();
  const headers=[
    'film','show_date','observation_scope','replay_cutoff','cinema','city','state','exhibitor',
    'shows','prime_shows','observed_capacity','observed_used_booked','occupancy',
    'seat_state_performance_index','momentum_seats_per_hour','prime_efficiency_delta_pp',
    'trajectory_t_minus_6h','trajectory_t_minus_3h','trajectory_t_minus_1h','final_pre_show_occupancy',
    'complete_trajectories','measured_trajectories','allocation_delta_shows','decision_signal','signal_confidence'
  ];
  const rows=records.map(rec=>{
    const cp=rec.trajectory?.checkpoints||{};
    return [
      'TIKUS!',state.product.showDate,state.scope.observation,replay?.label||'',
      rec.row.name,rec.row.city,rec.row.state,rec.row.exhibitorId.toUpperCase(),
      rec.row.totalShows,rec.row.primeTimeShows,rec.row.observedCapacity,rec.row.observedUsed,rec.row.occupancy,
      rec.row.performanceIndex,rec.momentum?.averageSeatsPerHour,
      rec.prime?.occupancyDelta==null?'':rec.prime.occupancyDelta*100,
      cp.tMinus6h?.occupancy,cp.tMinus3h?.occupancy,cp.tMinus1h?.occupancy,cp.finalPreShow?.occupancy,
      rec.trajectory?.completeTrajectories,rec.trajectory?.measuredSessions,rec.allocation?.showDelta,
      rec.decision?.label||rec.decision?.signal||'Monitor',rec.decision?.confidence||'low'
    ];
  });
  const caveat=['# Observed seat-state intelligence only. Used/booked states are not confirmed paid ticket sales.'];
  const csv=[...caveat,headers.map(csvEscape).join(','),...rows.map(row=>row.map(csvEscape).join(','))].join('\n');
  const blob=new Blob([`\uFEFF${csv}`],{type:'text/csv;charset=utf-8'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  const stamp=(replay?.id||state.scope.observation||'latest').replace(/[^a-z0-9_-]+/gi,'-');
  a.href=url; a.download=`tikus-cinema-comparison-${state.product.showDate}-${stamp}.csv`;
  document.body.append(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  if(note) note.textContent=`Exported ${records.length}-cinema CSV · ${comparisonScopeLabel()}.`;
}

function renderComparisonPrintHeader(records) {
  const root=$('#comparison-print-header'); if(!root) return;
  const names=records.map(rec=>escapeHtml(rec.row.name)).join(' · ');
  root.innerHTML=`<p class="comparison-print-kicker">FEISK PRODUCTIONS · TIKUS! DATA INTELLIGENCE</p><h1>Cinema Comparison</h1><p>${escapeHtml(comparisonScopeLabel())}</p><p>${names}</p><p class="comparison-print-caveat">Observed seat-state intelligence only. Used/booked states are not confirmed paid ticket sales. Schedule-only cinemas do not expose seat measurements.</p>`;
}

function printCinemaComparison() {
  const records=selectedComparisonRecords();
  const note=$('#comparison-note');
  if(records.length<2){ if(note) note.textContent='Select at least two seat-measured cinemas before printing.'; return; }
  renderComparisonPrintHeader(records);
  document.body.classList.add('comparison-print-mode');
  const cleanup=()=>document.body.classList.remove('comparison-print-mode');
  window.addEventListener('afterprint',cleanup,{once:true});
  window.print();
  setTimeout(()=>{ if(document.body.classList.contains('comparison-print-mode')) cleanup(); },1000);
}

function comparisonRows() {
  const sessions=currentSessions();
  return cinemaRows(sessions, state.bootstrap.cinemas.cinemas, state.scope, state.bootstrap.methodology, currentSessionChanges())
    .filter(r=>intelligenceCinemaAllowed(r.id));
}

function seedComparison(force=false) {
  const rows=comparisonRows().filter(r=>r.seatMeasuredSessions>0);
  const valid=new Set(rows.map(r=>r.id));
  state.comparisonCinemaIds=state.comparisonCinemaIds.filter(id=>valid.has(id));
  if(force || state.comparisonCinemaIds.length<2){
    const ranked=[...rows].sort((a,b)=>(b.observedUsed??-1)-(a.observedUsed??-1)||(b.occupancy??-1)-(a.occupancy??-1));
    state.comparisonCinemaIds=ranked.slice(0,Math.min(2,ranked.length)).map(r=>r.id);
  }
}

function metricByCinema(list, cinemaId) { return (list||[]).find(r=>r.cinemaId===cinemaId) || null; }

function comparisonRecord(row) {
  const intel=currentIntelligence()||{};
  const momentum=metricByCinema(intel.cinemaMomentum,row.id);
  const prime=metricByCinema(intel.primeTimeEfficiency,row.id);
  const trajectory=metricByCinema(intel.sessionTrajectories?.cinemas,row.id);
  const decision=metricByCinema(intel.decisionSignals?.cinemas,row.id);
  const allocation=metricByCinema(intel.allocationComparison?.cinemas,row.id);
  return {row,momentum,prime,trajectory,decision,allocation};
}

function renderComparisonSelectors(rows) {
  const root=$('#comparison-selectors'); if(!root) return; root.innerHTML='';
  const selected=new Set(state.comparisonCinemaIds);
  for(let slot=0;slot<4;slot++){
    const label=el('label','comparison-selector'); label.append(document.createTextNode(`Cinema ${slot+1}`));
    const select=document.createElement('select'); select.dataset.slot=String(slot); select.setAttribute('aria-label',`Comparison cinema ${slot+1}`);
    select.append(new Option(slot<2?'Select cinema':'Optional',''));
    rows.forEach(r=>{ const opt=new Option(`${r.name} · ${r.city}`,r.id); if(selected.has(r.id)&&state.comparisonCinemaIds[slot]!==r.id) opt.disabled=true; select.append(opt); });
    select.value=state.comparisonCinemaIds[slot]||'';
    select.addEventListener('change',()=>{
      const next=[...state.comparisonCinemaIds];
      if(select.value) next[slot]=select.value; else next.splice(slot,1);
      state.comparisonCinemaIds=[...new Set(next.filter(Boolean))].slice(0,4);
      renderCinemaComparison();
      syncUrlState();
    });
    label.append(select); root.append(label);
  }
}

function comparisonValue(value, kind) {
  if(kind==='int') return fmt.int(value);
  if(kind==='pct') return fmt.pct(value);
  if(kind==='ratio') return fmt.ratio(value);
  if(kind==='velocity') return value==null?'—':`${fmt.signed(value,1)}/hr`;
  if(kind==='pp') return value==null?'—':`${fmt.signed(value*100,2)} pp`;
  return value==null?'—':String(value);
}

function renderCinemaComparison() {
  const table=$('#cinema-comparison-table'); if(!table) return;
  const rows=comparisonRows(); seedComparison(false); renderComparisonSelectors(rows);
  const selected=state.comparisonCinemaIds.map(id=>rows.find(r=>r.id===id)).filter(Boolean).slice(0,4);
  const note=$('#comparison-note');
  if(selected.length<2){ table.innerHTML=''; note.textContent='Select at least two seat-measured cinemas to compare.'; return; }
  note.textContent=`${selected.length} cinemas · current analytical scope · ${activeReplay()?'hindsight-safe replay':'latest eligible observations'}.`;
  const records=selected.map(comparisonRecord);
  table.innerHTML='';
  const head=el('thead'); const hr=el('tr'); hr.append(el('th',null,'Metric')); selected.forEach(r=>{ const th=el('th'); th.innerHTML=`${escapeHtml(r.name)}<span class="comparison-sub">${escapeHtml(r.city)} · ${escapeHtml(r.exhibitorId.toUpperCase())}</span>`; hr.append(th); }); head.append(hr); table.append(head);
  const body=el('tbody');
  const metrics=[
    ['Shows',rec=>comparisonValue(rec.row.totalShows,'int')],
    ['Prime shows',rec=>comparisonValue(rec.row.primeTimeShows,'int')],
    ['Observed capacity',rec=>comparisonValue(rec.row.observedCapacity,'int')],
    ['Observed used / booked',rec=>comparisonValue(rec.row.observedUsed,'int')],
    ['All-day occupancy',rec=>comparisonValue(rec.row.occupancy,'pct')],
    ['Seat-State Performance Index',rec=>comparisonValue(rec.row.performanceIndex,'ratio')],
    ['Momentum',rec=>comparisonValue(rec.momentum?.averageSeatsPerHour,'velocity')],
    ['Prime efficiency Δ',rec=>comparisonValue(rec.prime?.occupancyDelta,'pp')],
    ['T−6h trajectory',rec=>comparisonValue(rec.trajectory?.checkpoints?.tMinus6h?.occupancy,'pct')],
    ['T−3h trajectory',rec=>comparisonValue(rec.trajectory?.checkpoints?.tMinus3h?.occupancy,'pct')],
    ['T−1h trajectory',rec=>comparisonValue(rec.trajectory?.checkpoints?.tMinus1h?.occupancy,'pct')],
    ['Final pre-show occupancy',rec=>comparisonValue(rec.trajectory?.checkpoints?.finalPreShow?.occupancy,'pct')],
    ['Complete trajectories',rec=>rec.trajectory?`${rec.trajectory.completeTrajectories||0}/${rec.trajectory.measuredSessions||0}`:'—'],
    ['Allocation Δ shows',rec=>comparisonValue(rec.allocation?.showDelta,'int')],
    ['Decision signal',rec=>rec.decision?.label||rec.decision?.signal||'Monitor'],
    ['Signal confidence',rec=>rec.decision?.confidence||'low'],
  ];
  metrics.forEach(([label,get])=>{ const tr=el('tr'); tr.append(el('th',null,label)); records.forEach(rec=>{ const value=get(rec); tr.append(el('td',value==='—'?'na':'',value)); }); body.append(tr); });
  table.append(body);
}

function renderAllocation() {
  const table=$('#allocation-table'); if(!table) return;
  const cmp=currentIntelligence()?.allocationComparison||{};
  const quality=$('#allocation-quality');
  quality.textContent=cmp.status!=='ok'?'No previous day':(cmp.quality==='comparable'?'Comparable days':'Limited · partial observation');
  table.innerHTML='<thead><tr><th>Cinema</th><th>Shows</th><th>Prev.</th><th>Δ Shows</th><th>Prime</th><th>Prev. Prime</th><th>Δ Prime</th></tr></thead>';
  const body=el('tbody');
  let rows=(cmp.cinemas||[]).filter(r=>intelligenceCinemaAllowed(r.cinemaId));
  rows.sort((a,b)=>Math.abs(b.showDelta)-Math.abs(a.showDelta)||Math.abs(b.primeShowDelta)-Math.abs(a.primeShowDelta)||cinemaName(a.cinemaId).localeCompare(cinemaName(b.cinemaId)));
  rows.forEach(r=>{ const tr=el('tr'); [cinemaName(r.cinemaId),fmt.int(r.shows),fmt.int(r.previousShows),fmt.signed(r.showDelta),fmt.int(r.primeShows),fmt.int(r.previousPrimeShows),fmt.signed(r.primeShowDelta)].forEach(v=>tr.append(el('td',v==='—'?'na':'',v))); body.append(tr); });
  if(!rows.length){ const tr=el('tr'); const td=el('td','na','Allocation comparison becomes available when a previous observed theatrical day exists.'); td.colSpan=7; tr.append(td); body.append(tr); }
  table.append(body);
  const note=$('#allocation-note');
  if(cmp.status==='ok') note.textContent=`Observed schedule-count comparison: ${cmp.previousDate} → ${state.product.showDate}. ${activeReplay()?'Current-day side is restricted to the replay cutoff; comparison is intentionally limited.':(cmp.quality==='comparable'?'Both days pass the repository completeness rule.':'At least one day is partial; treat deltas as observed differences, not definitive exhibitor programming changes.')}`;
}

function renderDecisionSignals() {
  const table=$('#decision-table'); if(!table) return;
  const data=currentIntelligence()?.decisionSignals||{};
  const quality=$('#decision-quality');
  quality.textContent=data.quality==='observed-day'?'Observed-day evidence':'Provisional · live observation';
  const summary=$('#decision-summary'); summary.innerHTML='';
  const counts=data.counts||{};
  [['Review opportunity',counts['review-opportunity']||0],['Mixed signal',counts.mixed||0],['Capacity watch',counts['capacity-watch']||0],['Monitor',counts.monitor||0]].forEach(([label,value])=>{ const card=el('div','decision-stat'); card.innerHTML=`<strong>${fmt.int(value)}</strong><span>${escapeHtml(label)}</span>`; summary.append(card); });
  table.innerHTML='<thead><tr><th>Cinema</th><th>Signal</th><th>Confidence</th><th>Evidence</th><th>PI</th><th>Momentum</th><th>Prime Δ</th></tr></thead>';
  const body=el('tbody');
  const rows=(data.cinemas||[]).filter(r=>intelligenceCinemaAllowed(r.cinemaId));
  rows.forEach(r=>{
    const tr=el('tr'); tr.dataset.signal=r.signal||'monitor';
    const evidence=(r.evidence||[]).join(' · ') || r.rationale || '—';
    const vals=[cinemaName(r.cinemaId),r.label||r.signal||'Monitor',r.confidence||'low',evidence,fmt.ratio(r.performanceIndex),r.averageSeatsPerHour==null?'—':`${fmt.signed(r.averageSeatsPerHour,1)}/hr`,r.primeOccupancyDelta==null?'—':`${fmt.signed(r.primeOccupancyDelta*100,2)} pp`];
    vals.forEach((v,i)=>tr.append(el('td',v==='—'?'na':(i===1?'decision-signal':''),v))); body.append(tr);
  });
  if(!rows.length){ const tr=el('tr'); const td=el('td','na','Decision signals require seat-measured cinema observations.'); td.colSpan=7; tr.append(td); body.append(tr); }
  table.append(body);
}


function renderTrend() {
  const table=$('#day-trend'); table.innerHTML='<thead><tr><th>Day</th><th>Shows</th><th>Locations</th><th>Capacity</th><th>Used</th><th>Occ.</th><th>Prime Occ.</th><th>Coverage</th></tr></thead>';
  const body=el('tbody'); const release=state.bootstrap.index.releaseDate;
  state.trendProducts.forEach((p,i)=>{ const finalComplete=p.finalPreShowState?.status==='complete'; const s=finalComplete && p.finalPreShowSummary?.totalShows ? p.finalPreShowSummary : p.summary; const dayNum=release?Math.round((new Date(`${p.showDate}T00:00:00+08:00`)-new Date(`${release}T00:00:00+08:00`))/86400000)+1:i+1; const label=`D${dayNum} · ${p.showDate.slice(5)}`; const tr=el('tr'); [label,fmt.int(s.totalShows),fmt.int(s.locationsWithConfirmedShows),fmt.int(s.observedCapacity),fmt.int(s.observedUsed),fmt.pct(s.occupancy),fmt.pct(s.primeTimeOccupancy),fmt.pct(s.seatCoverage)].forEach(v=>tr.append(el('td',v==='—'?'na':'',v))); body.append(tr); });
  if(!state.trendProducts.length){ const tr=el('tr'); const td=el('td','na','Historical day products appear after observations are collected.'); td.colSpan=8; tr.append(td); body.append(tr); } table.append(body);
}

function renderGeography(sessions) {
  const root=$('#geo-map'); root.innerHTML=''; const counts={}; sessions.forEach(s=>{ const c=state.bootstrap.cinemas.cinemas.find(x=>x.id===s.cinemaId); if(c) counts[c.state]=(counts[c.state]||0)+1; });
  for(const [region,label] of [['pen','PENINSULAR'],['borneo','BORNEO']]) { const box=el('div','geo-region'); box.dataset.label=label; Object.entries(geoPositions).filter(([,p])=>p[0]===region).forEach(([stateName,p])=>{ const b=el('button','geo-button',p[3]); b.type='button'; b.style.left=`${p[1]}%`; b.style.top=`${p[2]}%`; b.dataset.count=String(counts[stateName]||0); b.title=`${stateName}: ${counts[stateName]||0} scoped shows`; if(state.scope.state===stateName)b.classList.add('is-active'); const count=el('span',null,String(counts[stateName]||0)); b.append(count); b.addEventListener('click',()=>{ state.scope.state=state.scope.state===stateName?'all':stateName; $('#state-filter').value=state.scope.state; render(); }); box.append(b); }); root.append(box); }
}

function renderQuality() {
  const root=$('#quality-grid'); root.innerHTML=''; const statuses=state.bootstrap.status.latestRun?.sourceStatuses || {};
  const exs=state.bootstrap.exhibitors.exhibitors; exs.forEach(ex=>{ const s=statuses[ex.id] || {status:'not-collected',snapshots:0}; const item=el('div','quality-item'); const cls=s.status==='error'?'quality-status error':'quality-status'; const loc = Array.isArray(s.cinemaIds) ? ` · ${s.cinemaIds.length}/${s.expectedCinemas ?? '?'} locations observed` : ''; item.innerHTML=`<strong>${escapeHtml(ex.name)}</strong><span class="${cls}">${escapeHtml(s.status)}</span><span>${fmt.int(s.snapshots||0)} snapshots${s.seatMeasured!=null?` · ${s.seatMeasured} seat-measured`:''}${loc}</span><span>${escapeHtml(ex.seatDataCapability)}</span>`; root.append(item); });
}

function activeTrajectoryData() { return currentIntelligence()?.sessionTrajectories || {}; }

function trajectoryRow(sessionId) {
  return (activeTrajectoryData().sessions || []).find(r => r.sessionId === sessionId) || null;
}

function trajectoryCheckpointLabel(key) {
  return ({tMinus6h:'T−6h',tMinus3h:'T−3h',tMinus1h:'T−1h',finalPreShow:'Final pre-show'})[key] || key;
}

function renderScreeningTrajectory(sessionId) {
  const strip=$('#trajectory-session-strip'); const note=$('#trajectory-session-note');
  if(!strip||!note) return;
  strip.innerHTML='';
  const row=trajectoryRow(sessionId);
  if(!row){
    note.textContent='No seat-measured trajectory is available for this screening in the current observation scope.';
    const empty=el('div','trajectory-empty','Trajectory unavailable.'); strip.append(empty); return;
  }
  const session=(currentSessions().find(s=>s.sessionId===sessionId) || state.product.sessions?.find(s=>s.sessionId===sessionId));
  const start=session?.startAt || row.startAt;
  note.textContent=`${fmt.time(start)} screening · ${row.knownCheckpoints}/4 checkpoints observed${row.completeTrajectory?' · complete curve':''}. Each checkpoint uses the latest valid observation at or before its cutoff.`;
  ['tMinus6h','tMinus3h','tMinus1h','finalPreShow'].forEach((key,idx,arr)=>{
    const point=row.points?.[key];
    const card=el('article','trajectory-point');
    card.dataset.status=point?'observed':'unavailable';
    const head=el('div','trajectory-point__head'); head.append(el('strong',null,trajectoryCheckpointLabel(key)), el('span',null,point?'OBSERVED':'UNAVAILABLE')); card.append(head);
    if(point){
      const usedCap=el('div','trajectory-point__value',`${fmt.int(point.used)} / ${fmt.int(point.capacity)}`);
      const occ=el('div','trajectory-point__occ',`${fmt.pct(point.occupancy)} occupancy`);
      const meta=el('div','trajectory-point__meta');
      meta.append(el('span',null,`Observed ${fmt.datetime(point.collectedAt)}`));
      meta.append(el('span',null,`${fmt.int(point.minutesBeforeShow)} min before show`));
      card.append(usedCap,occ,meta);
    } else {
      const finalKey=key==='finalPreShow';
      const future=start && new Date(start)>new Date(activeReplay()?.asOf || state.product.generatedAt);
      const msg=finalKey&&future?'Not finalized yet.':'No valid observation by this cutoff.';
      card.append(el('div','trajectory-point__missing',msg));
    }
    strip.append(card);
    if(idx<arr.length-1) strip.append(el('div','trajectory-connector','→'));
  });
}

function openCinema(row, sessions) {
  const own=sessions.filter(s=>s.cinemaId===row.id).sort((a,b)=>a.startAt.localeCompare(b.startAt)); const dialog=$('#session-dialog'); $('#session-dialog-title').textContent=row.name;
  $('#session-dialog-summary').innerHTML=`<span><strong>${row.totalShows}</strong> shows</span><span><strong>${fmt.int(row.observedCapacity)}</strong> capacity</span><span><strong>${fmt.int(row.observedUsed)}</strong> used/booked</span><span><strong>${fmt.pct(row.occupancy)}</strong> occupancy</span><span><strong>${fmt.ratio(row.performanceIndex)}</strong> performance index</span>`;

  const trajectorySelect=$('#trajectory-session-filter'); trajectorySelect.innerHTML='';
  const trajectoryRows=(activeTrajectoryData().sessions||[]).filter(r=>r.cinemaId===row.id);
  const measurableIds=new Set(trajectoryRows.map(r=>r.sessionId));
  const selectable=own.filter(s=>measurableIds.has(s.sessionId));
  if(selectable.length){
    selectable.forEach(s=>trajectorySelect.append(new Option(`${fmt.time(s.startAt)}${s.session?.auditorium?` · ${s.session.auditorium}`:''}`,s.sessionId)));
    trajectorySelect.disabled=false;
    trajectorySelect.value=selectable[0].sessionId;
    renderScreeningTrajectory(selectable[0].sessionId);
  } else {
    trajectorySelect.append(new Option('No measured screening in scope',''));
    trajectorySelect.disabled=true;
    renderScreeningTrajectory('');
  }

  const table=$('#session-table'); table.innerHTML='<thead><tr><th>Start</th><th>Hall</th><th>Source</th><th>Capacity</th><th>Used / Booked</th><th>Available</th><th>Other</th><th>Occ.</th><th>Latest Δ</th><th>Velocity</th><th>Observed</th></tr></thead>';
  const body=el('tbody'); own.forEach(s=>{ const change=currentSessionChanges()?.[s.sessionId]||{}; const tr=el('tr'); if(measurableIds.has(s.sessionId)){ tr.classList.add('is-trajectory-selectable'); tr.tabIndex=0; tr.title='Select this screening trajectory'; const choose=()=>{ trajectorySelect.value=s.sessionId; renderScreeningTrajectory(s.sessionId); }; tr.addEventListener('click',choose); tr.addEventListener('keydown',e=>{ if(e.key==='Enter'||e.key===' '){e.preventDefault();choose();} }); }
    const vals=[fmt.time(s.startAt),s.session?.auditorium||'—',s.source?.provider?.toUpperCase()||'—',fmt.int(s.seat?.capacity),fmt.int(s.seat?.used),fmt.int(s.seat?.available),fmt.int(s.seat?.otherUnavailable),isMeasured(s)?fmt.pct(s.seat.used/s.seat.capacity):'—',fmt.signed(change.usedDelta),change.seatsPerHour==null?'—':`${fmt.signed(change.seatsPerHour,1)}/hr`,fmt.datetime(s.collectedAt)]; vals.forEach(v=>tr.append(el('td',v==='—'?'na':'',v))); body.append(tr); });
  if(!own.length){ const tr=el('tr'); const td=el('td','na','No observed TIKUS! sessions in the current scope.'); td.colSpan=11; tr.append(td); body.append(tr); } table.append(body); dialog.showModal();
}
function isMeasured(s){return Boolean(s.quality?.seatMeasured&&s.seat?.capacity>0&&Number.isInteger(s.seat?.used));}

function dateLabel(date, releaseDate) { if(!date)return '—'; if(!releaseDate)return date; const d=Math.round((new Date(`${date}T00:00:00+08:00`)-new Date(`${releaseDate}T00:00:00+08:00`))/86400000)+1; return `${date} · D${d}`; }
function escapeHtml(value){return String(value).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function showError(message){ const n=$('#load-error'); n.hidden=false; n.textContent=message; }
function renderEmptyShell(){ $('#freshness span:last-child').textContent='Data unavailable'; $('#kpi-grid').innerHTML=''; }

init();
})();
