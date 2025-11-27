// ---------- Element refs ----------
const form = document.getElementById('cityForm');
const input = document.getElementById('city');
const err = document.getElementById('err');
const btnEdit = document.getElementById('btnEdit');

const choices = document.getElementById('choices');
const choicesList = document.getElementById('choicesList');

const favList = document.getElementById('favList');

const bannerEl = document.getElementById('banner');

// ---------- State ----------
let editMode = false;
let units = (localStorage.getItem('units') === 'C') ? 'C' : 'F';

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
  try { await fetch('/api/banner/clear', { method: 'POST' }); setBanner(''); } catch {}
}
if (bannerEl) {
  bannerEl.addEventListener('click', clearBannerOnClick);
  refreshBanner();
}

// ---------- Helpers ----------
function showError(m){ err.textContent = m || ''; }
function clearError(){ err.textContent = ''; }
function hideChoices(){ if (choices) { choices.style.display = 'none'; choicesList.innerHTML = ''; } }

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


// // Remove favorite (saves both locally and to server)
// function removeFavByIndex(idx) {
//   const list = getFavs();
//   if (idx >= 0 && idx < list.length) {
//     list.splice(idx, 1);
//     saveFavs(list);
//     saveFavoritesToServer(list); // Sync to server
//   }
// }

// ---------- Render ----------
function miniTodayText(days){
  if (!Array.isArray(days) || !days.length) return 'High: —\nLow: —';
  const d0 = days[0];
  const hiC = typeof d0.temp_max_c === 'number' ? d0.temp_max_c : null;
  const loC = typeof d0.temp_min_c === 'number' ? d0.temp_min_c : null;
  const hi = hiC == null ? '—' : (units === 'F' ? cToF(hiC) : Math.round(hiC));
  const lo = loC == null ? '—' : (units === 'F' ? cToF(loC) : Math.round(loC));
  return `High: ${hi}${unitSym()}\nLow: ${lo}${unitSym()}`;
}

async function renderFavList() {
  console.log('[favorites.js] getFavs() returns:', getFavs());
  favList.innerHTML = '';
  const list = getFavs();
  
  if (!list.length) {
    const msg = isLoggedIn() 
      ? 'No favorites yet. Use the search above to add one.'
      : 'No favorites yet. Login to save favorites across devices!';
    favList.innerHTML = `<div style="color:#666;">${msg}</div>`;
    return;
  }

  // Fetch small previews (today's hi/lo)
  const previews = await Promise.all(list.map(async (f) => {
    try {
      const fore = await fetchJSON('/api/forecast', { lat: f.lat, lon: f.lon, city: f.name });
      return { ok: true, data: fore };
    } catch (e) {
      return { ok: false, err: e.message || 'error' };
    }
  }));

  // Render cards
  list.forEach((f, idx) => {
    const card = document.createElement('div');
    card.style.border = '1px solid #eee';
    card.style.background = '#f9f9f9';
    card.style.padding = '.75rem';
    card.style.position = 'relative';
    card.style.display = 'flex';
    card.style.flexDirection = 'column';
    card.style.gap = '.4rem';

    // Name
    const nameEl = document.createElement('div');
    nameEl.textContent = f.name;
    nameEl.style.fontWeight = '600';
    card.appendChild(nameEl);

    // Preview
    const prevEl = document.createElement('pre');
    prevEl.style.whiteSpace = 'pre-wrap';
    if (previews[idx].ok) {
      prevEl.textContent = miniTodayText(previews[idx].data.forecast);
    } else {
      prevEl.textContent = `Preview failed: ${previews[idx].err}`;
      prevEl.style.color = '#b00020';
    }
    card.appendChild(prevEl);

    // "-" remove button (visible only in edit mode)
    const rm = document.createElement('button');
    rm.textContent = '−';
    rm.setAttribute('aria-label', `Remove ${f.name}`);
    rm.style.position = 'absolute';
    rm.style.top = '6px';
    rm.style.right = '6px';
    rm.style.display = editMode ? 'inline-block' : 'none';
    rm.addEventListener('click', () => {
      removeFav(idx);
      renderFavList();
    });
    card.appendChild(rm);

    favList.appendChild(card);
  });
}

// ---------- Disambiguation ----------
function showChoices(items){
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
      addFav({ name, lat, lon });
      hideChoices();
      input.value = '';
      renderFavList();
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
    const res = await fetchJSON('/api/forecast', { city });
    if (res.matches) {
      showChoices(res.matches);
      return;
    }
    // Single direct match → add immediately
    addFav({ name: res.city, lat: res.lat, lon: res.lon });
    input.value = '';
    renderFavList();
  } catch (ex) {
    showError(ex.message || 'Network error. Please retry.');
  }
});

btnEdit.addEventListener('click', () => {
  editMode = !editMode;
  if (editMode) {
    alert('Select Locations to Delete');
  }
  // Re-render to toggle "-" visibility
  renderFavList();
});

// ---------- Init ----------
renderFavList();



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

// Initialize autocomplete for Favorites page
function initializeFavoritesAutocomplete() {
  if (typeof LocationAutocomplete === 'undefined') {
    console.warn('LocationAutocomplete not loaded on favorites page');
    return;
  }
  
  console.log('Initializing LocationAutocomplete on favorites page...');
  
  const autocomplete = new LocationAutocomplete(input, {
    onSelect: async (location) => {
      console.log('Favorites autocomplete selected:', location);
      
      // Hide any disambiguation choices
      hideChoices();
      clearError();
      
      try {
        // Add to favorites immediately
        const added = addFav({ 
          name: location.display_name, 
          lat: location.lat, 
          lon: location.lon 
        });
        
        if (added) {
          // Clear the input
          input.value = '';
          
          // Re-render favorites list to show the new one
          renderFavList();
          
          // Track this selection
          await trackLocationSelection({
            lat: location.lat,
            lon: location.lon,
            name: location.display_name
          });
          
          // Show success message briefly
          showError(''); // clear any errors
          console.log('Added to favorites:', location.display_name);
          
        } else {
          // Already in favorites
          showError('This location is already in your favorites');
          setTimeout(() => showError(''), 3000);
        }
        
      } catch (ex) {
        showError(ex.message || 'Failed to add favorite');
      }
    },
    minChars: 3,
    maxSuggestions: 4,
    showGeocoding: true
  });
  
  console.log('Favorites LocationAutocomplete initialized!');
}

// Call initialization when page loads
// Wrap in a small delay to ensure DOM is ready
setTimeout(initializeFavoritesAutocomplete, 100);