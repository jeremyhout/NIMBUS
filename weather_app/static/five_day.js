// ----- Refs -----
const form = document.getElementById('cityForm');
const input = document.getElementById('city');
const err = document.getElementById('err');
const btnUnits = document.getElementById('btnUnits');

const choices = document.getElementById('choices');
const choicesList = document.getElementById('choicesList');

const cityHeader = document.getElementById('cityHeader');
const cityLabel = document.getElementById('cityLabel');
const btnFavAdd = document.getElementById('btnFavAdd');

const fiveStrip = document.getElementById('fiveStrip');

const bannerEl = document.getElementById('banner');

// Favorites container for this page
const favList5 = document.getElementById('favList5'); // ensure this exists in five_day.html

// ----- State -----
let units = 'F';
let lastSelection = null;    // { lat, lon, name }
let recentForecast = null;   // { city, lat, lon, forecast: [...] }

// ===== Banner =====
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
  try { const r = await fetch('/api/banner'); const j = await r.json(); setBanner(j.banner || ''); } catch {}
}
async function clearBannerOnClick() { try { await fetch('/api/banner/clear', { method: 'POST' }); setBanner(''); } catch {} }
if (bannerEl) { bannerEl.addEventListener('click', clearBannerOnClick); refreshBanner(); }

// ===== Helpers =====
function showError(m){ err.textContent = m || ''; }
function clearError(){ err.textContent=''; }
function hideChoices(){ if (choices){ choices.style.display='none'; choicesList.innerHTML=''; } }

function cToF(c){ return Math.round((c*9/5)+32); }
function unitSym(){ return `°${units}`; }

async function fetchJSON(url, body){
  const r = await fetch(url, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body)
  });
  const ct = r.headers.get('content-type') || '';
  const data = ct.includes('application/json') ? await r.json() : { error: await r.text() };
  if (!r.ok) throw new Error((data && (data.error || data.detail)) || `HTTP ${r.status}`);
  return data;
}

// --- 5-day strip renderer into any target element ---
function renderFiveStripInto(targetEl, days, u='F'){
  if (!targetEl) return;
  targetEl.innerHTML = '';
  if (!Array.isArray(days) || !days.length){
    targetEl.textContent = 'No forecast data.';
    return;
  }
  const count = Math.min(5, days.length);
  for (let i=0; i<count; i++){
    const d = days[i];
    const hiC = (typeof d.temp_max_c === 'number') ? d.temp_max_c : null;
    const loC = (typeof d.temp_min_c === 'number') ? d.temp_min_c : null;
    const hi = hiC==null ? '—' : (u==='F' ? cToF(hiC) : Math.round(hiC));
    const lo = loC==null ? '—' : (u==='F' ? cToF(loC) : Math.round(loC));

    const col = document.createElement('div');
    col.style.minWidth = '120px';
    col.style.textAlign = 'center';
    col.style.display = 'flex';
    col.style.flexDirection = 'column';
    col.style.alignItems = 'center';
    col.style.justifyContent = 'center';
    col.style.gap = '6px';

    const title = document.createElement('div');
    title.textContent = d.weekday ? d.weekday : (d.date || 'Day');

    const hiEl = document.createElement('div');
    hiEl.textContent = `High: ${hi}${unitSym()}`;
    hiEl.style.fontWeight = '600';

    const loEl = document.createElement('div');
    loEl.textContent = `Low: ${lo}${unitSym()}`;

    col.appendChild(title);
    col.appendChild(hiEl);
    col.appendChild(loEl);
    targetEl.appendChild(col);
  }
}

// --- Favorites preview (5-day) ---
async function renderFavPreview() { 
  // Load from server if logged in (one-time per page load)
  if (isLoggedIn() && getFavs().length === 0) {
    await loadFavoritesFromServer();
  }
  const box = document.getElementById('favList'); // IMPORTANT: five_day.html must have <div id="favList">
  if (!box) return;
  box.innerHTML = '';

  const list = getFavs();
  if (!list.length){
    box.innerHTML = '<div style="color:#666;">No favorites yet. Search a city and click ＋ to save it.</div>';
    return;
  }

  list.forEach(async (f) => {
    // Title line (no outer card)
    const title = document.createElement('div');
    title.textContent = f.name;
    title.style.fontWeight = '600';
    title.style.marginTop = '.75rem';
    box.appendChild(title);

    // 5-day strip container (bordered, same look as main)
    const strip = document.createElement('div');
    strip.style.display = 'flex';
    strip.style.gap = '12px';
    strip.style.overflowX = 'auto';
    strip.style.padding = '.75rem';
    strip.style.border = '1px solid #eee';
    strip.style.background = '#f9f9f9';
    strip.style.marginTop = '.5rem';
    strip.style.boxSizing = 'border-box';
    box.appendChild(strip);

    // Spacer between entries
    const spacer = document.createElement('div');
    spacer.style.height = '.5rem';
    box.appendChild(spacer);

    try {
      const fore = await fetchJSON('/api/forecast', { lat: f.lat, lon: f.lon, city: f.name });
      renderFiveStripInto(strip, fore.forecast, units);
    } catch (e){
      strip.textContent = `Failed to load: ${e.message || 'error'}`;
      strip.style.color = '#b00020';
    }
  });
}


// ---- Persist last selected city only for this browser tab/session ----
const CURRENT_KEY = 'currentSelection';

function saveCurrentSelection(sel) {
  try { sessionStorage.setItem(CURRENT_KEY, JSON.stringify(sel)); } catch {}
}

function getCurrentSelection() {
  try { return JSON.parse(sessionStorage.getItem(CURRENT_KEY) || 'null'); } catch { return null; }
}


// // Favorites (localStorage) — reuse the same key as Home
// function getFavs(){ try{ return JSON.parse(localStorage.getItem('favorites')||'[]'); }catch{ return []; } }
// function saveFavs(list){ try{ localStorage.setItem('favorites', JSON.stringify(list)); }catch{} }
// function addFav(item){
//   const list = getFavs();
//   if (!list.some(f => f.name===item.name && f.lat===item.lat && f.lon===item.lon)){
//     list.push(item); saveFavs(list);
//   }
// }

// ===== 5-Day Rendering (main area) =====
function renderFiveStrip(days, u='F'){
  if (!fiveStrip) return;
  fiveStrip.innerHTML = '';
  if (!Array.isArray(days) || !days.length){
    fiveStrip.textContent = 'No forecast data.';
    return;
  }
  const count = Math.min(5, days.length);
  for (let i=0; i<count; i++){
    const d = days[i] || {};
    const hiC = (typeof d.temp_max_c === 'number') ? d.temp_max_c : null;
    const loC = (typeof d.temp_min_c === 'number') ? d.temp_min_c : null;
    const hi = hiC==null ? '—' : (u==='F' ? cToF(hiC) : Math.round(hiC));
    const lo = loC==null ? '—' : (u==='F' ? cToF(loC) : Math.round(loC));

    const col = document.createElement('div');
    col.style.minWidth = '120px';
    col.style.textAlign = 'center';
    col.style.display = 'flex';
    col.style.flexDirection = 'column';
    col.style.alignItems = 'center';
    col.style.justifyContent = 'center';
    col.style.gap = '6px';

    const title = document.createElement('div');
    title.textContent = d.weekday ? d.weekday : (d.date || 'Day');

    const hiEl = document.createElement('div');
    hiEl.textContent = `High: ${hi}${unitSym()}`;
    hiEl.style.fontWeight = '600';

    const loEl = document.createElement('div');
    loEl.textContent = `Low: ${lo}${unitSym()}`;

    col.appendChild(title);
    col.appendChild(hiEl);
    col.appendChild(loEl);
    fiveStrip.appendChild(col);
  }
}

function renderIntoPage(fore){
  if (cityHeader){ cityHeader.style.display = 'inline'; }
  
  // Add timezone to city label if available
  if (cityLabel) {
    let displayText = fore.city;
    if (fore.timezone) {
      displayText += ` (${fore.timezone})`;
    }
    cityLabel.textContent = displayText;
  }
  
  renderFiveStrip(fore.forecast, units);
  recentForecast = fore;
}

// ===== Disambiguation =====
function showChoices(items){
  if (!choices || !choicesList) return;
  choicesList.innerHTML = '';
  items.forEach(m => {
    const li = document.createElement('li');
    const label = [m.name, m.admin1, m.country].filter(Boolean).join(', ');
    li.innerHTML = `<button type="button"
       data-lat="${m.lat}" data-lon="${m.lon}" data-name="${label}"
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
      try{
        const fore = await fetchJSON('/api/forecast', { lat, lon, city: name });
        renderIntoPage(fore);

        // remember city across pages
        saveCurrentSelection({ name, lat, lon });
        input.value = name;

      }catch(ex){
        showError(ex.message || 'Server error');
      }
    });
  });
}

// ===== Events (Search / Units / Add Favorite) =====
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const city = input.value.trim();
  if (!city){ showError('City name is required.'); return; }
  clearError();

  try {
    if (lastSelection && lastSelection.name.toLowerCase().includes(city.toLowerCase())){
      const fore = await fetchJSON('/api/forecast', { lat:lastSelection.lat, lon:lastSelection.lon, city:lastSelection.name });
      renderIntoPage(fore);

      saveCurrentSelection({ name: lastSelection.name, lat: lastSelection.lat, lon: lastSelection.lon });
      input.value = lastSelection.name;

      return;
    }

    const foreAttempt = await fetchJSON('/api/forecast', { city });
    if (foreAttempt.matches){ showChoices(foreAttempt.matches); return; }
    renderIntoPage(foreAttempt);
    saveCurrentSelection({ name: foreAttempt.city, lat: foreAttempt.lat, lon: foreAttempt.lon });
    input.value = foreAttempt.city;

  } catch (ex){
    showError(ex.message || 'Network error. Please retry.');
  }
});

if (btnUnits){
  btnUnits.addEventListener('click', () => {
    units = (units === 'F') ? 'C' : 'F';
    btnUnits.textContent = `Show ${units === 'F' ? '°C' : '°F'}`;
    if (recentForecast){ renderFiveStrip(recentForecast.forecast, units); }
    renderFavPreview();   // NEW: re-render favorite cards in new units
    try{ localStorage.setItem('units', units); }catch{}
  });
}

// Add to favorites (with confirmation)
if (btnFavAdd){
  btnFavAdd.addEventListener('click', () => {
    if (!recentForecast){ showError('Search a city first.'); return; }

    const name = recentForecast.city;
    const ok = window.confirm(`Are you sure you want to add "${name}" to favorites?`);
    if (!ok) return;

    addFav({ name, lat: recentForecast.lat, lon: recentForecast.lon });
    renderFavPreview();   // NEW: immediately refresh the favorites list
    showError(''); // clear
  });
}


// ===== Favorites section for the 5-day page =====
function makeDayCol(weekday, hiText, loText) {
  const col = document.createElement('div');
  col.style.minWidth = '96px';
  col.style.textAlign = 'center';
  col.style.display = 'flex';
  col.style.flexDirection = 'column';
  col.style.alignItems = 'center';
  col.style.justifyContent = 'center';
  col.style.gap = '6px';

  const top = document.createElement('div');
  top.textContent = weekday || '';
  top.style.fontWeight = '600';

  const mid = document.createElement('div');
  mid.textContent = `High: ${hiText}`;

  const bot = document.createElement('div');
  bot.textContent = `Low: ${loText}`;

  col.appendChild(top);
  col.appendChild(mid);
  col.appendChild(bot);
  return col;
}

function renderFiveDayStripInto(targetEl, days, u='F', maxDays=5) {
  if (!targetEl) return;
  targetEl.innerHTML = '';
  if (!Array.isArray(days) || !days.length) {
    targetEl.textContent = 'No forecast data.';
    return;
  }
  const len = Math.min(maxDays, days.length);
  for (let i = 0; i < len; i++) {
    const d = days[i] || {};
    const weekday = d.weekday || (d.date || '');
    const hiC = (typeof d.temp_max_c === 'number') ? d.temp_max_c : null;
    const loC = (typeof d.temp_min_c === 'number') ? d.temp_min_c : null;
    const hi = hiC == null ? '—' : (u === 'F' ? cToF(hiC) : Math.round(hiC));
    const lo = loC == null ? '—' : (u === 'F' ? cToF(loC) : Math.round(loC));
    targetEl.appendChild(makeDayCol(weekday, `${hi}${unitSym()}`, `${lo}${unitSym()}`));
  }
}

async function renderFavPreview5() {  // ✅ async function
  const box = document.getElementById('favList5');
  if (!box) return;
  const list = getFavs();
  box.innerHTML = '';
  
  if (!list.length) {
    box.innerHTML = '<div style="color:#666;">No favorites yet. Save a city on Home (＋) and it will show here.</div>';
    return;
  }
  
  // ✅ Load all forecasts in parallel (much faster!)
  for (const f of list) {
    // wrapper (no outer card; match main layout)
    const wrap = document.createElement('div');
    wrap.style.width = '100%';
    
    // Title line
    const title = document.createElement('div');
    title.className = 'fav-title';
    title.style.fontWeight = '600';
    title.style.marginTop = '.75rem';
    title.textContent = f.name;
    wrap.appendChild(title);
    
    // Five-day strip block (use same look as .strip)
    const strip = document.createElement('div');
    strip.className = 'strip';
    wrap.appendChild(strip);
    
    box.appendChild(wrap);
    
    // Load forecast asynchronously (don't block the loop)
    (async () => {
      try {
        const fore = await fetchJSON('/api/forecast', { lat: f.lat, lon: f.lon, city: f.name });
        renderFiveDayStripInto(strip, fore.forecast, units, 5);
      } catch (e) {
        strip.textContent = `Failed to load: ${e.message || 'error'}`;
        strip.style.color = '#b00020';
      }
    })();
  }
}

// ===== Init =====
(function initStart(){
  // One-time migration: ensure old localStorage value doesn't revive last session
  try { localStorage.removeItem('currentSelection'); } catch {}

  // Default blank UI on first open
  cityHeader.style.display = 'none';
  fiveStrip.textContent = 'Search for a location to see the 5-day forecast.';

  try {
    const savedUnits = localStorage.getItem('units');
    if (savedUnits === 'C' || savedUnits === 'F'){
      units = savedUnits;
      if (btnUnits) btnUnits.textContent = `Show ${units === 'F' ? '°C' : '°F'}`;
    }
  } catch {}
  renderFavPreview5();

    // NEW: Auto-restore last selected city -> immediately show 5-day
  const cur = getCurrentSelection();
  if (cur && typeof cur.lat === 'number' && typeof cur.lon === 'number') {
    input.value = cur.name || '';
    (async () => {
      try {
        const fore = await fetchJSON('/api/forecast', { lat: cur.lat, lon: cur.lon, city: cur.name });
        renderIntoPage(fore);
      } catch (e) {
        // ignore restore errors
      }
    })();
  }

  renderFavPreview(); 

})();



// Helper function to generate location ID (same as home.js)
function generateLocationId(location) {
  const name = (location.name || '').toLowerCase().replace(/\s+/g, '_');
  return name.replace(/[^a-z0-9_]/g, '');
}

// Helper function to track location selection
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
    console.log('Location tracked:', location.name);
  } catch (e) {
    console.warn('Failed to track location:', e);
  }
}

// Initialize autocomplete for Five-Day page
function initializeFiveDayAutocomplete() {
  if (typeof LocationAutocomplete === 'undefined') {
    console.warn('LocationAutocomplete not loaded on five-day page');
    return;
  }
  
  console.log('Initializing LocationAutocomplete on five-day page...');
  
  const autocomplete = new LocationAutocomplete(input, {
    onSelect: async (location) => {
      console.log('Five-day autocomplete selected:', location);
      
      // Store selection
      lastSelection = {
        lat: location.lat,
        lon: location.lon,
        name: location.display_name
      };
      
      // Hide any disambiguation choices
      hideChoices();
      clearError();
      
      try {
        // Fetch 5-day forecast
        const fore = await fetchJSON('/api/forecast', { 
          lat: location.lat, 
          lon: location.lon, 
          city: location.display_name 
        });
        
        // Render the forecast
        renderIntoPage(fore);
        
        // Save for cross-page persistence
        saveCurrentSelection({ 
          name: location.display_name, 
          lat: location.lat, 
          lon: location.lon 
        });
        
        // Update input to show full name
        input.value = location.display_name;
        
        // Track this selection
        await trackLocationSelection({
          lat: location.lat,
          lon: location.lon,
          name: location.display_name
        });
        
      } catch (ex) {
        showError(ex.message || 'Failed to fetch forecast');
      }
    },
    minChars: 3,
    maxSuggestions: 4,
    showGeocoding: true
  });
  
  console.log('Five-day LocationAutocomplete initialized!');
}

// Call initialization when page loads
// Wrap in a small delay to ensure DOM is ready
setTimeout(initializeFiveDayAutocomplete, 100);