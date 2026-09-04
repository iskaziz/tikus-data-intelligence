(() => {
const { loadBootstrap, loadDateProduct, loadTrendProducts, aggregate, cinemaRows, exhibitorRows, filterSessions, occupancyDistribution, scopedCinemas, fmt } = window.TIKUS_DI;

const state = {
  bootstrap: null,
  product: null,
  trendProducts: [],
  scope: { date: null, time: 'all', exhibitor: 'all', state: 'all', observation: 'latest' },
  search: '',
  sort: { key: 'observedUsed', direction: 'desc' },
  visibleColumns: new Set(['rank','cinema','shows','showShare','capacity','used','occupancy','avgUsed','primeShows','primeOccupancy','performanceIndex','usedDelta']),
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
    render();
  });

  const exhib = $('#exhibitor-filter');
  exhibitors.exhibitors.forEach(e => exhib.append(new Option(e.name, e.id)));
  exhib.addEventListener('change', () => { state.scope.exhibitor = exhib.value; render(); });

  const states = [...new Set(cinemas.cinemas.map(c => c.state))].sort();
  const stateSelect = $('#state-filter');
  states.forEach(name => stateSelect.append(new Option(name, name)));
  stateSelect.addEventListener('change', () => { state.scope.state = stateSelect.value; render(); });

  $('#time-filter').addEventListener('change', e => { state.scope.time = e.target.value; render(); });
  $('#observation-filter').addEventListener('change', e => { state.scope.observation = e.target.value; render(); });
  $('#cinema-search').addEventListener('input', e => { state.search = e.target.value.toLowerCase().trim(); renderTable(); });
  $('#reset-filters').addEventListener('click', () => {
    state.scope.time='all'; state.scope.exhibitor='all'; state.scope.state='all'; state.scope.observation='latest'; state.search='';
    $('#time-filter').value='all'; $('#exhibitor-filter').value='all'; $('#state-filter').value='all'; $('#observation-filter').value='latest'; $('#cinema-search').value='';
    render();
  });
  setupColumnMenu();
  $('#column-toggle').addEventListener('click', () => {
    const menu=$('#column-menu'); const open=menu.hidden; menu.hidden=!open; $('#column-toggle').setAttribute('aria-expanded', String(open));
  });
  $('#session-dialog .dialog-close').addEventListener('click', () => $('#session-dialog').close());
  $('#session-dialog').addEventListener('click', e => { if (e.target === $('#session-dialog')) $('#session-dialog').close(); });
}

function setupColumnMenu() {
  const menu=$('#column-menu'); menu.innerHTML='';
  columns.filter(c => !['rank','cinema'].includes(c.id)).forEach(col => {
    const label=el('label'); const input=document.createElement('input'); input.type='checkbox'; input.checked=state.visibleColumns.has(col.id);
    input.addEventListener('change', () => { input.checked ? state.visibleColumns.add(col.id) : state.visibleColumns.delete(col.id); renderTable(); });
    label.append(input, document.createTextNode(col.label)); menu.append(label);
  });
}

function currentSessions() {
  const base = state.scope.observation === 'final' ? (state.product.finalPreShowSessions || []) : (state.product.sessions || []);
  return filterSessions(base, state.scope, state.bootstrap.cinemas.cinemas, state.bootstrap.methodology);
}

function render() {
  if (!state.bootstrap || !state.product) return;
  const sessions = currentSessions();
  const scoped = scopedCinemas(state.bootstrap.cinemas.cinemas, state.scope);
  const metrics = aggregate(sessions, state.bootstrap.methodology);
  renderFreshness(); renderScope(metrics, scoped); renderKpis(metrics, scoped.length); renderTable(); renderExhibitors(sessions); renderDistribution(sessions); renderTrend(); renderGeography(sessions); renderQuality();
}

function renderFreshness() {
  const node=$('#freshness'); const dot=node.querySelector('.status-dot');
  const when=state.product.observationWindow?.lastCollectedAt;
  dot.classList.toggle('is-live', Boolean(when));
  node.querySelector('span:last-child').textContent = when ? `Last observed ${fmt.datetime(when)} MYT` : 'No session observations stored yet';
}

function renderScope(metrics, scoped) {
  const parts=[];
  if(state.scope.exhibitor!=='all') parts.push(state.bootstrap.exhibitors.exhibitors.find(e=>e.id===state.scope.exhibitor)?.name);
  if(state.scope.state!=='all') parts.push(state.scope.state);
  if(state.scope.time!=='all') parts.push($('#time-filter').selectedOptions[0].textContent);
  $('#scope-label').textContent = `${parts.length ? parts.join(' · ') : 'Tracked network'} · ${scoped.length} cinema${scoped.length===1?'':'s'}`;
  $('#coverage-note').textContent = metrics.totalShows ? `Seat measurement coverage ${metrics.seatMeasuredSessions}/${metrics.totalShows} sessions · ${fmt.pct(metrics.seatCoverage)}` : 'No observed TIKUS! sessions in this scope.';
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
  let rows=cinemaRows(sessions, state.bootstrap.cinemas.cinemas, state.scope, state.bootstrap.methodology, state.product.sessionChanges || {});
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

function renderTrend() {
  const table=$('#day-trend'); table.innerHTML='<thead><tr><th>Day</th><th>Shows</th><th>Locations</th><th>Capacity</th><th>Used</th><th>Occ.</th><th>Prime Occ.</th><th>Coverage</th></tr></thead>';
  const body=el('tbody'); const release=state.bootstrap.index.releaseDate;
  state.trendProducts.forEach((p,i)=>{ const s=p.finalPreShowSummary?.totalShows ? p.finalPreShowSummary : p.summary; const dayNum=release?Math.round((new Date(`${p.showDate}T00:00:00+08:00`)-new Date(`${release}T00:00:00+08:00`))/86400000)+1:i+1; const label=`D${dayNum} · ${p.showDate.slice(5)}`; const tr=el('tr'); [label,fmt.int(s.totalShows),fmt.int(s.locationsWithConfirmedShows),fmt.int(s.observedCapacity),fmt.int(s.observedUsed),fmt.pct(s.occupancy),fmt.pct(s.primeTimeOccupancy),fmt.pct(s.seatCoverage)].forEach(v=>tr.append(el('td',v==='—'?'na':'',v))); body.append(tr); });
  if(!state.trendProducts.length){ const tr=el('tr'); const td=el('td','na','Historical day products appear after observations are collected.'); td.colSpan=8; tr.append(td); body.append(tr); } table.append(body);
}

function renderGeography(sessions) {
  const root=$('#geo-map'); root.innerHTML=''; const counts={}; sessions.forEach(s=>{ const c=state.bootstrap.cinemas.cinemas.find(x=>x.id===s.cinemaId); if(c) counts[c.state]=(counts[c.state]||0)+1; });
  for(const [region,label] of [['pen','PENINSULAR'],['borneo','BORNEO']]) { const box=el('div','geo-region'); box.dataset.label=label; Object.entries(geoPositions).filter(([,p])=>p[0]===region).forEach(([stateName,p])=>{ const b=el('button','geo-button',p[3]); b.type='button'; b.style.left=`${p[1]}%`; b.style.top=`${p[2]}%`; b.dataset.count=String(counts[stateName]||0); b.title=`${stateName}: ${counts[stateName]||0} scoped shows`; if(state.scope.state===stateName)b.classList.add('is-active'); const count=el('span',null,String(counts[stateName]||0)); b.append(count); b.addEventListener('click',()=>{ state.scope.state=state.scope.state===stateName?'all':stateName; $('#state-filter').value=state.scope.state; render(); }); box.append(b); }); root.append(box); }
}

function renderQuality() {
  const root=$('#quality-grid'); root.innerHTML=''; const statuses=state.bootstrap.status.latestRun?.sourceStatuses || {};
  const exs=state.bootstrap.exhibitors.exhibitors; exs.forEach(ex=>{ const s=statuses[ex.id] || {status:'not-collected',snapshots:0}; const item=el('div','quality-item'); const cls=s.status==='error'?'quality-status error':'quality-status'; item.innerHTML=`<strong>${escapeHtml(ex.name)}</strong><span class="${cls}">${escapeHtml(s.status)}</span><span>${fmt.int(s.snapshots||0)} snapshots${s.seatMeasured!=null?` · ${s.seatMeasured} seat-measured`:''}</span><span>${escapeHtml(ex.seatDataCapability)}</span>`; root.append(item); });
}

function openCinema(row, sessions) {
  const own=sessions.filter(s=>s.cinemaId===row.id).sort((a,b)=>a.startAt.localeCompare(b.startAt)); const dialog=$('#session-dialog'); $('#session-dialog-title').textContent=row.name;
  $('#session-dialog-summary').innerHTML=`<span><strong>${row.totalShows}</strong> shows</span><span><strong>${fmt.int(row.observedCapacity)}</strong> capacity</span><span><strong>${fmt.int(row.observedUsed)}</strong> used/booked</span><span><strong>${fmt.pct(row.occupancy)}</strong> occupancy</span><span><strong>${fmt.ratio(row.performanceIndex)}</strong> performance index</span>`;
  const table=$('#session-table'); table.innerHTML='<thead><tr><th>Start</th><th>Hall</th><th>Source</th><th>Capacity</th><th>Used / Booked</th><th>Available</th><th>Other</th><th>Occ.</th><th>Latest Δ</th><th>Velocity</th><th>Observed</th></tr></thead>';
  const body=el('tbody'); own.forEach(s=>{ const change=state.product.sessionChanges?.[s.sessionId]||{}; const tr=el('tr'); const vals=[fmt.time(s.startAt),s.session?.auditorium||'—',s.source?.provider?.toUpperCase()||'—',fmt.int(s.seat?.capacity),fmt.int(s.seat?.used),fmt.int(s.seat?.available),fmt.int(s.seat?.otherUnavailable),isMeasured(s)?fmt.pct(s.seat.used/s.seat.capacity):'—',fmt.signed(change.usedDelta),change.seatsPerHour==null?'—':`${fmt.signed(change.seatsPerHour,1)}/hr`,fmt.datetime(s.collectedAt)]; vals.forEach(v=>tr.append(el('td',v==='—'?'na':'',v))); body.append(tr); });
  if(!own.length){ const tr=el('tr'); const td=el('td','na','No observed TIKUS! sessions in the current scope.'); td.colSpan=11; tr.append(td); body.append(tr); } table.append(body); dialog.showModal();
}
function isMeasured(s){return Boolean(s.quality?.seatMeasured&&s.seat?.capacity>0&&Number.isInteger(s.seat?.used));}

function dateLabel(date, releaseDate) { if(!date)return '—'; if(!releaseDate)return date; const d=Math.round((new Date(`${date}T00:00:00+08:00`)-new Date(`${releaseDate}T00:00:00+08:00`))/86400000)+1; return `${date} · D${d}`; }
function escapeHtml(value){return String(value).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function showError(message){ const n=$('#load-error'); n.hidden=false; n.textContent=message; }
function renderEmptyShell(){ $('#freshness span:last-child').textContent='Data unavailable'; $('#kpi-grid').innerHTML=''; }

init();
})();
