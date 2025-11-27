// weather_app/static/home_with_autocomplete.js
// Updated home.js that integrates location search autocomplete

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
let lastSelection = null;
let recentForecast = null;
let recentHourly = null;

// ---------- NEW: Initialize autocomplete ----------
let autocomplete = null;

function initializeAutocomplete() {
  if (typeof LocationAutocomplete === 'undefined') {
    console.warn('LocationAutocomplete not loaded');
    return;
  }
  
  autocomplete = new LocationAutocomplete(input, {
    onSelect: async (location) => {
      console.log('Autocomplete selected:', location);
      
      // Track the selection (already done by autocomplete)
      // Now fetch weather for this location
      lastSelection = {
        lat: location.lat,
        lon: location.lon,
        name: location.display_name
      };
      
      try {
        clearError();
        const [fore, hour] = await Promise.all([
          fetchJSON('/api/forecast', { 
            lat: location.lat, 
            lon: location.lon, 
            city: location.display_name 
          }),
          fetchJSON('/api/hourly', { 
            lat: location.lat, 
            lon: location.lon, 
            city: location.display_name 
          }),
        ]);
        
        renderIntoMain(fore, hour);
        saveCurrentSelection({ 
          name: location.display_name, 
          lat: location.lat, 
          lon: location.lon 
        });
        
      } catch (ex) {
        showError(ex.message || 'Failed to fetch weather');
      }
    },
    minChars: 3,
    maxSuggestions: 4,
    showGeocoding: true  // Fall back to geocoding if needed
  });
}

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
function hideChoices() { 
  if (choices) { 
    choices.style.display = 'none'; 
    choicesList.innerHTML = ''; 
  } 
}

function cToF(c) { return Math.round((c * 9/5) + 32); }
function unitSym() { return `°${units}`; }

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

// ---- Persist last selected city ----
const CURRENT_KEY = 'currentSelection';

function saveCurrentSelection(sel) {
  try { sessionStorage.setItem(CURRENT_KEY, JSON.stringify(sel)); } catch {}
}

function getCurrentSelection() {
  try { return JSON.parse(sessionStorage.getItem(CURRENT_KEY) || 'null'); } catch { return null; }
}

// ---- Track location selection with microservice ----
async function trackLocationSelection(location) {
  try {
    await fetch('/api/location-search/track', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        location_id: generateLocationId(location),
        display_name: location.name,
        lat: location.lat,
        lon: location.lon
      })
    });
  } catch (e) {
    console.warn('Failed to track location:', e);
  }
}

function generateLocationId(location) {
  // Simple ID generation (matching frontend autocomplete)
  const name = (location.name || '').toLowerCase().replace(/\s+/g, '_');
  return name.replace(/[^a-z0-9_]/g, '');
}

// ---------- Rendering ----------
function renderSimpleToday(_cityLabel, forecastArr, u='F') {
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

function renderHourlyStrip(hours, u='F', maxCols=24) {
  if (!hourlyStrip) return;
  hourlyStrip.innerHTML = '';
  if (!Array.isArray(hours) || !hours.length) {
    hourlyStrip.textContent = 'No hourly data.';
    return;
  }
  const cols = Math.min(maxCols, hours.length);

  const nowTemp = (typeof hours[0].temp_c === 'number') ? (u === 'F' ? cToF(hours[0].temp_c) : Math.round(hours[0].temp_c)) : '—';
  hourlyStrip.appendChild(makeHourCol('Now', `${nowTemp}${unitSym()}`));

  for (let i = 1; i < cols; i++) {
    const label = hours[i].hour || hours[i].time;
    const t = (typeof hours[i].temp_c === 'number') ? (u === 'F' ? cToF(hours[i].temp_c) : Math.round(hours[i].temp_c)) : '—';
    hourlyStrip.appendChild(makeHourCol(label, `${t}${unitSym()}`));
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

  currentOut.textContent = renderSimpleToday(fore.city, fore.forecast, units);
  renderHourlyStrip(hour.hourly, units);

  recentForecast = fore;
  recentHourly = hour;
}

// ---------- Disambiguation UI (fallback if autocomplete not used) ----------
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
      
      // Track selection
      await trackLocationSelection({ lat, lon, name });
      
      try {
        const [fore, hour] = await Promise.all([
          fetchJSON('/api/forecast', { lat, lon, city: name }),
          fetchJSON('/api/hourly', { lat, lon, city: name }),
        ]);
        renderIntoMain(fore, hour);
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
    // Check if we have a cached selection
    if (lastSelection && lastSelection.name.toLowerCase().includes(city.toLowerCase())) {
      const [fore, hour] = await Promise.all([
        fetchJSON('/api/forecast', { lat: lastSelection.lat, lon: lastSelection.lon, city: lastSelection.name }),
        fetchJSON('/api/hourly', { lat: lastSelection.lat, lon: lastSelection.lon, city: lastSelection.name }),
      ]);
      renderIntoMain(fore, hour);
      saveCurrentSelection({ name: lastSelection.name, lat: lastSelection.lat, lon: lastSelection.lon });
      input.value = lastSelection.name;
      
      // Track this selection
      await trackLocationSelection(lastSelection);
      return;
    }

    // Otherwise do a normal search
    const foreAttempt = await fetchJSON('/api/forecast', { city });
    if (foreAttempt.matches) { 
      showChoices(foreAttempt.matches); 
      return; 
    }

    const [fore, hour] = await Promise.all([
      Promise.resolve(foreAttempt),
      fetchJSON('/api/hourly', { lat: foreAttempt.lat, lon: foreAttempt.lon, city: foreAttempt.city }),
    ]);
    renderIntoMain(fore, hour);
    saveCurrentSelection({ name: foreAttempt.city, lat: foreAttempt.lat, lon: foreAttempt.lon });
    input.value = foreAttempt.city;
    
    // Track this selection
    await trackLocationSelection({ lat: fore.lat, lon: fore.lon, name: fore.city });
    
  } catch (ex) {
    showError(ex.message || 'Network error. Please retry.');
  }
});

// Units toggle
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

// Add to favorites
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
    const wrap = document.createElement('div');
    wrap.style.width = '100%';
    wrap.style.display = 'block';

    const title = document.createElement('div');
    title.className = 'fav-title';
    title.style.fontWeight = title.style.fontWeight || '600';
    title.style.marginTop = title.style.marginTop || '.75rem';
    title.textContent = f.name;
    wrap.appendChild(title);

    const todayEl = document.createElement('pre');
    todayEl.className = 'block';
    if (!todayEl.className) {
      todayEl.style.whiteSpace = 'pre-wrap';
      todayEl.style.marginTop = '.5rem';
      todayEl.style.background = '#f9f9f9';
      todayEl.style.padding = '.75rem';
      todayEl.style.border = '1px solid #eee';
    }
    todayEl.textContent = 'Loading...';
    wrap.appendChild(todayEl);

    const strip = document.createElement('div');
    strip.className = 'strip';
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

    try {
      const [fore, hour] = await Promise.all([
        fetchJSON('/api/forecast', { lat: f.lat, lon: f.lon, city: f.name }),
        fetchJSON('/api/hourly', { lat: f.lat, lon: f.lon, city: f.name }),
      ]);

      const d0 = (fore.forecast && fore.forecast[0]) || {};
      const hiC = (typeof d0.temp_max_c === 'number') ? d0.temp_max_c : null;
      const loC = (typeof d0.temp_min_c === 'number') ? d0.temp_min_c : null;
      const hi = hiC == null ? '—' : (units === 'F' ? cToF(hiC) : Math.round(hiC));
      const lo = loC == null ? '—' : (units === 'F' ? cToF(loC) : Math.round(loC));
      todayEl.textContent = `High: ${hi}${unitSym()}\nLow: ${lo}${unitSym()}`;

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
    } catch (e) {
      todayEl.textContent = `Failed to load: ${e.message || 'error'}`;
      todayEl.style.color = '#b00020';
      strip.textContent = '';
    }
  });
}

// Initial load
(function initStart() {
  try { localStorage.removeItem('currentSelection'); } catch {}

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
  
  // Initialize autocomplete
  initializeAutocomplete();
  
  renderFavPreview();

  const cur = getCurrentSelection();
  if (cur && typeof cur.lat === 'number' && typeof cur.lon === 'number') {
    input.value = cur.name || '';
    (async () => {
      try {
        const [fore, hour] = await Promise.all([
          fetchJSON('/api/forecast', { lat: cur.lat, lon: cur.lon, city: cur.name }),
          fetchJSON('/api/hourly', { lat: cur.lat, lon: cur.lon, city: cur.name }),
        ]);
        renderIntoMain(fore, hour);
      } catch (e) {
        // ignore restore errors
      }
    })();
  }
})();

// Option 1: Quick Debugging (Add to bottom of home.js)
console.log('🔍 Debug: Checking LocationAutocomplete...');
if (typeof LocationAutocomplete === 'undefined') {
    console.error('❌ Error: LocationAutocomplete class is NOT loaded. Check your script tags in home.html');
} else {
    console.log('✅ Success: LocationAutocomplete class is loaded!');
}