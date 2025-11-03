// ---------- Element refs ----------
const form = document.getElementById('cityForm');
const input = document.getElementById('city');
const err = document.getElementById('err');
const btnUnits = document.getElementById('btnUnits');

const choices = document.getElementById('choices');
const choicesList = document.getElementById('choicesList');

const cityHeader = document.getElementById('cityHeader');
const cityLabel = document.getElementById('cityLabel');
const btnFavAdd = document.getElementById('btnFavAdd');

const currentOut = document.getElementById('currentOut');
const hourlyStrip = document.getElementById('hourlyStrip');

const bannerEl = document.getElementById('banner');

let units = 'F';
let lastSelection = null; // { lat, lon, name }

// Cache last results for unit re-render
let recentForecast = null; // { city, lat, lon, forecast: [...] }
let recentHourly = null;   // { city, lat, lon, hourly: [...] }

// ---------- Banner ----------
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
if (bannerEl) {
  bannerEl.addEventListener('click', clearBannerOnClick);
  refreshBanner();
}

// ---------- Helpers ----------
function showError(msg) { err.textContent = msg || ''; }
function clearError() { err.textContent = ''; }
function hideChoices() { if (choices) { choices.style.display = 'none'; choicesList.innerHTML = ''; } }

function cToF(c){ return Math.round((c * 9/5) + 32); }
function unitSym(){ return `°${units}`; }

async function fetchJSON(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  });
  const ct = r.headers.get('content-type') || '';
  const data = ct.includes('application/json') ? await r.json() : { error: await r.text() };
  if (!r.ok) throw new Error((data && (data.error || data.detail)) || `HTTP ${r.status}`);
  return data;
}

// ---- Persist last selected city only for this browser tab/session ----
const CURRENT_KEY = 'currentSelection';

function saveCurrentSelection(sel) {
  try { sessionStorage.setItem(CURRENT_KEY, JSON.stringify(sel)); } catch {}
}

function getCurrentSelection() {
  try { return JSON.parse(sessionStorage.getItem(CURRENT_KEY) || 'null'); } catch { return null; }
}


// Favorites (localStorage)
function getFavs() { try { return JSON.parse(localStorage.getItem('favorites') || '[]'); } catch { return []; } }
function saveFavs(list) { try { localStorage.setItem('favorites', JSON.stringify(list)); } catch {} }
function addFav(item) {
  const list = getFavs();
  if (!list.some(f => f.name === item.name && f.lat === item.lat && f.lon === item.lon)) {
    list.push(item);
    saveFavs(list);
  }
}
function renderFavPreview() {
  const list = getFavs();
  const box = document.getElementById('favList');
  if (!box) return;
  box.innerHTML = '';

  if (!list.length) {
    box.innerHTML = '<div style="color:#666;">No favorites yet. Search a city and click ＋ to save it.</div>';
    return;
  }

  list.forEach(async (f) => {
    // wrapper so each favorite is a pair of blocks (no nested card)
    const wrap = document.createElement('div');
    wrap.style.width = '100%';        // fill the same <main> width
    wrap.style.display = 'block';

    // Title (matches city header style—no border)
    const title = document.createElement('div');
    title.className = 'fav-title';    // if you added CSS; otherwise keep the two lines below
    title.style.fontWeight = title.style.fontWeight || '600';
    title.style.marginTop = title.style.marginTop || '.75rem';
    title.textContent = f.name;
    wrap.appendChild(title);

    // Today block — SAME look as #currentOut
    const todayEl = document.createElement('pre');
    todayEl.className = 'block';      // uses .block CSS if present
    if (!todayEl.className) {
      todayEl.style.whiteSpace = 'pre-wrap';
      todayEl.style.marginTop = '.5rem';
      todayEl.style.background = '#f9f9f9';
      todayEl.style.padding = '.75rem';
      todayEl.style.border = '1px solid #eee';
    }
    todayEl.textContent = 'Loading...';
    wrap.appendChild(todayEl);

    // Hourly strip — SAME look as #hourlyStrip
    const strip = document.createElement('div');
    strip.className = 'strip';        // uses .strip CSS if present
    if (!strip.className) {
      strip.style.display = 'flex';
      strip.style.gap = '12px';
      strip.style.overflowX = 'auto';
      strip.style.padding = '.75rem';
      strip.style.border = '1px solid #eee';
      strip.style.background = '#f9f9f9';
      strip.style.marginTop = '.5rem';
    }
    wrap.appendChild(strip);

    box.appendChild(wrap);

    // Fetch + render
    try {
      const [fore, hour] = await Promise.all([
        fetchJSON('/api/forecast', { lat: f.lat, lon: f.lon, city: f.name }),
        fetchJSON('/api/hourly',   { lat: f.lat, lon: f.lon, city: f.name }),
      ]);

      const d0 = (fore.forecast && fore.forecast[0]) || {};
      const hiC = (typeof d0.temp_max_c === 'number') ? d0.temp_max_c : null;
      const loC = (typeof d0.temp_min_c === 'number') ? d0.temp_min_c : null;
      const hi = hiC == null ? '—' : (units === 'F' ? cToF(hiC) : Math.round(hiC));
      const lo = loC == null ? '—' : (units === 'F' ? cToF(loC) : Math.round(loC));
      todayEl.textContent = `High: ${hi}${unitSym()}\nLow: ${lo}${unitSym()}`;

      if (typeof renderHourlyStripInto === 'function') {
        renderHourlyStripInto(strip, hour.hourly, units, 24);
      } else {
        // fallback build
        strip.innerHTML = '';
        const nowTemp = (typeof hour.hourly[0]?.temp_c === 'number')
          ? (units === 'F' ? cToF(hour.hourly[0].temp_c) : Math.round(hour.hourly[0].temp_c))
          : '—';
        strip.appendChild(makeHourCol('Now', `${nowTemp}${unitSym()}`));
        for (let i = 1; i < Math.min(24, hour.hourly.length); i++) {
          const label = hour.hourly[i].hour || hour.hourly[i].time;
          const t = (typeof hour.hourly[i].temp_c === 'number')
            ? (units === 'F' ? cToF(hour.hourly[i].temp_c) : Math.round(hour.hourly[i].temp_c))
            : '—';
          strip.appendChild(makeHourCol(label, `${t}${unitSym()}`));
        }
      }
    } catch (e) {
      todayEl.textContent = `Failed to load: ${e.message || 'error'}`;
      todayEl.style.color = '#b00020';
      strip.textContent = '';
    }
  });
}


// ---------- Rendering ----------
function renderSimpleToday(_cityLabel, forecastArr, u='F') {
  // Use day-0 of the forecast as "today"
  if (!Array.isArray(forecastArr) || forecastArr.length === 0) {
    return `High: —\nLow: —`;
  }
  const d0 = forecastArr[0];
  const hiC = (typeof d0.temp_max_c === 'number') ? d0.temp_max_c : null;
  const loC = (typeof d0.temp_min_c === 'number') ? d0.temp_min_c : null;
  const hi = hiC == null ? '—' : (u === 'F' ? cToF(hiC) : Math.round(hiC));
  const lo = loC == null ? '—' : (u === 'F' ? cToF(loC) : Math.round(loC));
  return `High: ${hi}${unitSym()}\nLow: ${lo}${unitSym()}`;
}

// For favorites preview cards (text-only)
function renderHourlyInlineText(hours, u='F', maxCols=10) {
  if (!Array.isArray(hours) || hours.length === 0) return 'No hourly data.';
  const cols = Math.min(maxCols, hours.length);
  const header = ['Now'];
  const temps  = [(typeof hours[0].temp_c === 'number') ? (u === 'F' ? cToF(hours[0].temp_c) : Math.round(hours[0].temp_c)) : '—'];
  for (let i = 1; i < cols; i++) {
    header.push(hours[i].hour || hours[i].time);
    const t = (typeof hours[i].temp_c === 'number') ? (u === 'F' ? cToF(hours[i].temp_c) : Math.round(hours[i].temp_c)) : '—';
    temps.push(t);
  }
  const line1 = header.join('  ');
  const line2 = temps.map(v => `${v}${unitSym()}`).join('  ');
  return `${line1}\n${line2}`;
}

// DOM strip (centered columns, horizontally scrollable)
function renderHourlyStrip(hours, u='F', maxCols=24) {
  if (!hourlyStrip) return;
  hourlyStrip.innerHTML = '';
  if (!Array.isArray(hours) || !hours.length) {
    hourlyStrip.textContent = 'No hourly data.';
    return;
  }
  const cols = Math.min(maxCols, hours.length);  

  // Build "Now" column first
  const nowTemp = (typeof hours[0].temp_c === 'number') ? (u === 'F' ? cToF(hours[0].temp_c) : Math.round(hours[0].temp_c)) : '—';
  hourlyStrip.appendChild(makeHourCol('Now', `${nowTemp}${unitSym()}`));

  // Then subsequent hours
  for (let i = 1; i < cols; i++) {
    const label = hours[i].hour || hours[i].time;
    const t = (typeof hours[i].temp_c === 'number') ? (u === 'F' ? cToF(hours[i].temp_c) : Math.round(hours[i].temp_c)) : '—';
    hourlyStrip.appendChild(makeHourCol(label, `${t}${unitSym()}`));
  }
}

function renderHourlyStripInto(targetEl, hours, u='F', maxCols=24) {
  if (!targetEl) return;
  targetEl.innerHTML = '';
  if (!Array.isArray(hours) || !hours.length) {
    targetEl.textContent = 'No hourly data.';
    return;
  }
  const cols = Math.min(maxCols, hours.length);

  // "Now"
  const nowTemp = (typeof hours[0].temp_c === 'number') ? (u === 'F' ? cToF(hours[0].temp_c) : Math.round(hours[0].temp_c)) : '—';
  targetEl.appendChild(makeHourCol('Now', `${nowTemp}${unitSym()}`));

  for (let i = 1; i < cols; i++) {
    const label = hours[i].hour || hours[i].time;
    const t = (typeof hours[i].temp_c === 'number') ? (u === 'F' ? cToF(hours[i].temp_c) : Math.round(hours[i].temp_c)) : '—';
    targetEl.appendChild(makeHourCol(label, `${t}${unitSym()}`));
  }
}


function makeHourCol(top, bottom) {
  const col = document.createElement('div');
  col.style.minWidth = '64px';
  col.style.textAlign = 'center';
  col.style.display = 'flex';
  col.style.flexDirection = 'column';
  col.style.alignItems = 'center';
  col.style.justifyContent = 'center';
  col.style.gap = '6px';

  const t = document.createElement('div');
  t.textContent = top;

  const b = document.createElement('div');
  b.textContent = bottom;
  b.style.fontWeight = '600';

  col.appendChild(t);
  col.appendChild(b);
  return col;
}

function renderIntoMain(fore, hour) {
  cityHeader.style.display = 'inline';
  cityLabel.textContent = fore.city;

  // Render simple today (hi/lo)
  currentOut.textContent = renderSimpleToday(fore.city, fore.forecast, units);

  // Render hourly strip beneath
  renderHourlyStrip(hour.hourly, units);

  // Cache
  recentForecast = fore;
  recentHourly = hour;
}

// ---------- Disambiguation UI ----------
function showChoices(items) {
  if (!choices || !choicesList) return;
  choicesList.innerHTML = '';
  items.forEach(m => {
    const li = document.createElement('li');
    const label = [m.name, m.admin1, m.country].filter(Boolean).join(', ');
    li.innerHTML = `<button type="button"
       data-lat="${m.lat}"
       data-lon="${m.lon}"
       data-name="${label}"
       style="margin:.25rem 0;">${label}</button>`;
    choicesList.appendChild(li);
  });
  choices.style.display = 'block';

  choicesList.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', async () => {
      const lat = parseFloat(btn.dataset.lat);
      const lon = parseFloat(btn.dataset.lon);
      const name = btn.dataset.name;
      lastSelection = { lat, lon, name };
      hideChoices();
      clearError();
      try {
        const [fore, hour] = await Promise.all([
          fetchJSON('/api/forecast', { lat, lon, city: name }),
          fetchJSON('/api/hourly',   { lat, lon, city: name }),
        ]);
        renderIntoMain(fore, hour);

        // NEW: remember selected city across pages
        saveCurrentSelection({ name, lat, lon });
        input.value = name;

      } catch (ex) {
        showError(ex.message || 'Server error');
      }
    });
  });
}

// ---------- Events ----------
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const city = input.value.trim();
  if (!city) { showError('City name is required.'); return; }
  clearError();

  try {
    if (lastSelection && lastSelection.name.toLowerCase().includes(city.toLowerCase())) {
      const [fore, hour] = await Promise.all([
        fetchJSON('/api/forecast', { lat: lastSelection.lat, lon: lastSelection.lon, city: lastSelection.name }),
        fetchJSON('/api/hourly',   { lat: lastSelection.lat, lon: lastSelection.lon, city: lastSelection.name }),
      ]);
      renderIntoMain(fore, hour);

      // remember selection
      saveCurrentSelection({ name: lastSelection.name, lat: lastSelection.lat, lon: lastSelection.lon });
      input.value = lastSelection.name;

      return;
    }

    const foreAttempt = await fetchJSON('/api/forecast', { city });
    if (foreAttempt.matches) { showChoices(foreAttempt.matches); return; }

    const [fore, hour] = await Promise.all([
      Promise.resolve(foreAttempt),
      fetchJSON('/api/hourly', { lat: foreAttempt.lat, lon: foreAttempt.lon, city: foreAttempt.city }),
    ]);
    renderIntoMain(fore, hour);
    // remember selection
    saveCurrentSelection({ name: foreAttempt.city, lat: foreAttempt.lat, lon: foreAttempt.lon });
    input.value = foreAttempt.city;

  } catch (ex) {
    showError(ex.message || 'Network error. Please retry.');
  }
});

// Units toggle re-renders both boxes
if (btnUnits) {
  btnUnits.addEventListener('click', () => {
    units = (units === 'F') ? 'C' : 'F';
    btnUnits.textContent = `Show ${units === 'F' ? '°C' : '°F'}`;

    if (recentForecast && recentHourly) {
      currentOut.textContent = renderSimpleToday(recentForecast.city, recentForecast.forecast, units);
      renderHourlyStrip(recentHourly.hourly, units);
    }
    renderFavPreview();
    try { localStorage.setItem('units', units); } catch {}
  });
}

// Add to favorites (with confirmation)
if (btnFavAdd) {
  btnFavAdd.addEventListener('click', () => {
    if (!recentForecast) { showError('Search a city first.'); return; }

    const name = recentForecast.city;
    const ok = window.confirm(`Are you sure you want to add "${name}" to favorites?`);
    if (!ok) return;

    addFav({ name, lat: recentForecast.lat, lon: recentForecast.lon });
    renderFavPreview();
    showError('');
  });
}


// Initial load: restore units, favorites, banner
(function initStart(){
  // One-time migration: ensure old localStorage value doesn't revive last session
  try { localStorage.removeItem('currentSelection'); } catch {}

  // Default blank UI on first open
  cityHeader.style.display = 'none';
  currentOut.textContent = 'Search for a location to see the forecast.';
  hourlyStrip.textContent = '';

  try {
    const savedUnits = localStorage.getItem('units');
    if (savedUnits === 'C' || savedUnits === 'F') {
      units = savedUnits;
      btnUnits.textContent = `Show ${units === 'F' ? '°C' : '°F'}`;
    }
  } catch {}
  renderFavPreview();

    // NEW: Auto-restore last selection if present
  const cur = getCurrentSelection();
  if (cur && typeof cur.lat === 'number' && typeof cur.lon === 'number') {
    input.value = cur.name || '';
    (async () => {
      try {
        const [fore, hour] = await Promise.all([
          fetchJSON('/api/forecast', { lat: cur.lat, lon: cur.lon, city: cur.name }),
          fetchJSON('/api/hourly',   { lat: cur.lat, lon: cur.lon, city: cur.name }),
        ]);
        renderIntoMain(fore, hour);
      } catch (e) {
        // ignore restore errors
      }
    })();
  }


})();
