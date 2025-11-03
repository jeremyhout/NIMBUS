// ===== settings.js =====

// ---- Config for URNS ----
const URNS_BASE = 'http://127.0.0.1:8081';
const APP_KEY   = 'dev-key';
const APP_ID    = 'weather-app';

// ---- Refs ----
const bannerEl = document.getElementById('banner');
const btnUnits = document.getElementById('btnUnits');

const btnTestEveryMinute = document.getElementById('btnTestEveryMinute');
const dtOne   = document.getElementById('dtOne');
const msgOne  = document.getElementById('msgOne');
const btnOneTime = document.getElementById('btnOneTime');

const btnList = document.getElementById('btnList');
const btnClearAll = document.getElementById('btnClearAll');
const rowsRems = document.getElementById('rowsRems');

// ---- Units state ----
let units = 'F';

// ---- Banner helpers ----
function setBanner(text) {
  if (!bannerEl) return;
  if (text && text.trim()) {
    bannerEl.textContent = text;
    bannerEl.style.display = 'block';
  } else {
    bannerEl.textContent = '';
    bannerEl.style.display = 'none';
  }
}
async function refreshBanner() {
  try {
    const r = await fetch('/api/banner');
    const j = await r.json();
    setBanner(j.banner || '');
  } catch {}
}
async function clearBannerOnClick() {
  try {
    await fetch('/api/banner/clear', { method: 'POST' });
    setBanner('');
  } catch {}
}
if (bannerEl) { bannerEl.addEventListener('click', clearBannerOnClick); refreshBanner(); }

// ---- Shared helpers ----
function toast(msg){ alert(msg); }

async function urnsGET(path, params = {}) {
  const url = new URL(path, URNS_BASE);
  Object.entries(params).forEach(([k,v]) => { if (v != null) url.searchParams.set(k, v); });
  const r = await fetch(url.toString(), { headers: { 'X-App-Key': APP_KEY } });
  if (!r.ok) throw new Error(`URNS HTTP ${r.status}`);
  return r.json();
}

async function urnsPOST(path, body) {
  const r = await fetch(`${URNS_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-App-Key': APP_KEY
    },
    body: JSON.stringify(body)
  });
  const ct = r.headers.get('content-type') || '';
  const data = ct.includes('application/json') ? await r.json() : { error: await r.text() };
  if (!r.ok) throw new Error(data.error || `URNS HTTP ${r.status}`);
  return data;
}

async function urnsDELETE(path) {
  const r = await fetch(`${URNS_BASE}${path}`, {
    method: 'DELETE',
    headers: { 'X-App-Key': APP_KEY }
  });
  if (!r.ok) throw new Error(`URNS HTTP ${r.status}`);
  return r.json();
}

// ---- Units init & toggle ----
(function initUnits(){
  try {
    const saved = localStorage.getItem('units');
    if (saved === 'C' || saved === 'F') units = saved;
  } catch {}
  if (btnUnits) btnUnits.textContent = `Show ${units === 'F' ? '°C' : '°F'}`;
})();
if (btnUnits) {
  btnUnits.addEventListener('click', () => {
    units = (units === 'F') ? 'C' : 'F';
    btnUnits.textContent = `Show ${units === 'F' ? '°C' : '°F'}`;
    try { localStorage.setItem('units', units); } catch {}
    // no re-render needed here, this page is for settings
  });
}

// ---- Render reminders table ----
function renderRows(items) {
  rowsRems.innerHTML = '';
  if (!items || !items.length) {
    rowsRems.innerHTML = `<tr><td colspan="5" class="muted">No reminders scheduled.</td></tr>`;
    return;
  }
  for (const it of items) {
    const tr = document.createElement('tr');

    const tdId = document.createElement('td');
    tdId.textContent = it.reminder_id;

    const tdType = document.createElement('td');
    tdType.textContent = it.type;

    const tdStatus = document.createElement('td');
    tdStatus.textContent = it.status + (it.last_error ? ' ⚠︎' : '');

    const tdNext = document.createElement('td');
    tdNext.textContent = it.next_run_time || '';

    const tdAct = document.createElement('td');
    const delBtn = document.createElement('button');
    delBtn.textContent = 'Delete';
    delBtn.className = 'btn btn-outline';
    delBtn.addEventListener('click', async () => {
      const sure = confirm('Delete this reminder?');
      if (!sure) return;
      try {
        await urnsDELETE(`/reminders/${encodeURIComponent(it.reminder_id)}`);
        toast('Deleted.');
        await loadList();
      } catch (e) {
        toast(e.message || 'Delete failed.');
      }
    });
    tdAct.appendChild(delBtn);

    tr.appendChild(tdId);
    tr.appendChild(tdType);
    tr.appendChild(tdStatus);
    tr.appendChild(tdNext);
    tr.appendChild(tdAct);
    rowsRems.appendChild(tr);
  }
}

// ---- List loader ----
async function loadList() {
  try {
    // filter by app_id so you only see your app’s reminders
    const data = await urnsGET('/reminders', { app_id: APP_ID });
    renderRows(data);
  } catch (e) {
    rowsRems.innerHTML = `<tr><td colspan="5" class="muted">Failed to load reminders: ${e.message || 'error'}</td></tr>`;
  }
}

// ---- Actions ----

// Test: every minute
if (btnTestEveryMinute) {
  btnTestEveryMinute.addEventListener('click', async () => {
    try {
      const body = {
        app_id: APP_ID,
        type: 'cron',
        cron: '*/1 * * * *', // every minute
        notify: { webhook: 'http://127.0.0.1:8080/hooks/reminder' },
        payload: { title: 'Test Reminder', msg: 'This fires every minute for testing.' }
      };
      const out = await urnsPOST('/reminders', body);
      toast(`Scheduled test: ${out.reminder_id}`);
      await loadList();
    } catch (e) {
      toast(e.message || 'Schedule failed.');
    }
  });
}

// One-time reminder at specific date/time (local → UTC ISO)
if (btnOneTime) {
  btnOneTime.addEventListener('click', async () => {
    const val = dtOne.value; // "YYYY-MM-DDTHH:MM"
    if (!val) { toast('Pick a date/time first.'); return; }
    const iso = new Date(val).toISOString();
    const message = (msgOne.value || 'One-time reminder');

    try {
      const body = {
        app_id: APP_ID,
        type: 'time',
        when: iso, // UTC ISO
        notify: { webhook: 'http://127.0.0.1:8080/hooks/reminder' },
        payload: { title: 'One-time Reminder', msg: message }
      };
      const out = await urnsPOST('/reminders', body);
      toast(`Scheduled one-time: ${out.reminder_id}`);
      await loadList();
    } catch (e) {
      toast(e.message || 'Schedule failed.');
    }
  });
}

// List
if (btnList) btnList.addEventListener('click', loadList);

// Clear all (with confirmation)
if (btnClearAll) {
  btnClearAll.addEventListener('click', async () => {
    const ok = confirm('Clear ALL reminders for ALL apps? This cannot be undone.');
    if (!ok) return;
    try {
      await urnsDELETE('/reminders');
      toast('All reminders cleared.');
      await loadList();
    } catch (e) {
      toast(e.message || 'Clear failed.');
    }
  });
}

// ---- Init ----
loadList();
