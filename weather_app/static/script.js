// ---------- Element refs ----------
const form = document.getElementById('cityForm');
const input = document.getElementById('city');
const err = document.getElementById('err');
const currentOut = document.getElementById('currentOut');
const forecastOut = document.getElementById('forecastOut');
const btnForecast = document.getElementById('btnForecast');
const btnSchedule = document.getElementById('btnSchedule');
const btnUnits = document.getElementById('btnUnits');

const bannerEl = document.getElementById('banner');

const btnCancelAll = document.getElementById('btnCancelAll');
const remTitle = document.getElementById('remTitle');
const remMsg = document.getElementById('remMsg');
const remSchedule = document.getElementById('remSchedule');

const modalEl = document.getElementById('confirmModal');
const modalCard = modalEl ? modalEl.querySelector('.modal-card') : null;
const confirmYes = document.getElementById('confirmYes');
const confirmNo  = document.getElementById('confirmNo');



// ---------- Banner helpers ----------
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
  } catch (_) {
    // best-effort only
  }
}

async function clearBannerOnClick() {
  try {
    await fetch('/api/banner/clear', { method: 'POST' });
    setBanner('');
  } catch (_) {}
}

// --- Make banner clickable to dismiss ---
if (bannerEl) {
  bannerEl.style.cursor = 'pointer';
  bannerEl.title = 'Click to dismiss';
  bannerEl.addEventListener('click', clearBannerOnClick);
}

// ---------- Disambiguation (ensure the block exists in index.html) ----------
const choices = document.getElementById('choices');
const choicesList = document.getElementById('choicesList');

// ---------- State ----------
let lastSelection = null;            // { lat, lon, name } from user choice
let units = 'F';                     // 'F' or 'C'
let recentForecast = null;           // last forecast payload: { city, lat, lon, forecast: [...] }
let recentForecastForCurrent = null; // last forecast payload specifically used to render Current card

// ---------- General helpers ----------
function showError(msg) { err.textContent = msg || ''; }
function clearError() { err.textContent = ''; }
function hideChoices() {
  if (choices) {
    choices.style.display = 'none';
    if (choicesList) choicesList.innerHTML = '';
  }
}

async function fetchJSON(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  });
  const ct = r.headers.get('content-type') || '';
  const isJSON = ct.includes('application/json');
  const data = isJSON ? await r.json() : { error: await r.text() };
  if (!r.ok) throw new Error((data && (data.error || data.detail)) || `HTTP ${r.status}`);
  return data;
}

function cToF(c) { return Math.round((c * 9/5) + 32); }

// ---------- Rendering ----------
function renderSimpleToday(cityLabel, forecastArr, u = 'F') {
  if (!Array.isArray(forecastArr) || forecastArr.length === 0) {
    return `${cityLabel}\nHigh: —\nLow: —`;
  }
  const d0 = forecastArr[0];
  const hi = (typeof d0.temp_max_c === 'number') ? (u === 'F' ? cToF(d0.temp_max_c) : Math.round(d0.temp_max_c)) : '—';
  const lo = (typeof d0.temp_min_c === 'number') ? (u === 'F' ? cToF(d0.temp_min_c) : Math.round(d0.temp_min_c)) : '—';
  const unitSym = `°${u}`;
  return `${cityLabel}\nHigh: ${hi}${unitSym}\nLow: ${lo}${unitSym}`;
}

function renderFiveDay(cityLabel, days, u='F') {
  const lines = [cityLabel];
  (days || []).forEach(d => {
    const day = d.weekday || d.date || '';   // ✅ trust server-provided weekday
    const hi = (typeof d.temp_max_c === 'number') ? (u === 'F' ? cToF(d.temp_max_c) : Math.round(d.temp_max_c)) : '—';
    const lo = (typeof d.temp_min_c === 'number') ? (u === 'F' ? cToF(d.temp_min_c) : Math.round(d.temp_min_c)) : '—';
    const unitSym = `°${u}`;
    lines.push(`${day} — High ${hi}${unitSym} / Low ${lo}${unitSym}`);
  });
  return lines.join('\n');
}


function rerenderUsingUnits() {
  if (recentForecastForCurrent) {
    currentOut.textContent = renderSimpleToday(recentForecastForCurrent.city, recentForecastForCurrent.forecast, units);
  }
  if (recentForecast) {
    forecastOut.textContent = renderFiveDay(recentForecast.city, recentForecast.forecast, units);
  }
  if (btnUnits) {
    const showNext = units === 'F' ? '°C' : '°F';
    btnUnits.textContent = `Show ${showNext}`;
    btnUnits.setAttribute('aria-pressed', units === 'C' ? 'true' : 'false');
  }
}

// ---------- Disambiguation UI ----------
function showChoices(items, nextAction) { // nextAction: 'current' | 'forecast'
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
        const j = await fetchJSON('/api/forecast', { lat, lon, city: name });
        if (nextAction === 'current') {
          recentForecastForCurrent = j;
          currentOut.textContent = renderSimpleToday(j.city, j.forecast, units);
        } else {
          recentForecast = j;
          forecastOut.textContent = renderFiveDay(j.city, j.forecast, units);
        }
      } catch (ex) {
        showError(ex.message || 'Server error');
      }
    });
  });
}

// ---------- Event handlers ----------

// Submit => "Current" card uses today's hi/lo from forecast
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const city = input.value.trim();
  if (!city) { showError('City name is required.'); return; }
  clearError();

  try {
    if (lastSelection && lastSelection.name.toLowerCase().includes(city.toLowerCase())) {
      const j = await fetchJSON('/api/forecast', { lat: lastSelection.lat, lon: lastSelection.lon, city: lastSelection.name });
      hideChoices();
      recentForecastForCurrent = j;
      currentOut.textContent = renderSimpleToday(j.city, j.forecast, units);
      return;
    }

    const j = await fetchJSON('/api/forecast', { city });
    if (j.matches) { showChoices(j.matches, 'current'); return; }

    hideChoices();
    recentForecastForCurrent = j;
    currentOut.textContent = renderSimpleToday(j.city, j.forecast, units);
  } catch (ex) {
    showError(ex.message || 'Network error. Please retry.');
  }
});

// 5-Day Forecast button
btnForecast.addEventListener('click', async () => {
  const city = input.value.trim();
  if (!city) { showError('City name is required.'); return; }
  clearError();

  try {
    if (lastSelection && lastSelection.name.toLowerCase().includes(city.toLowerCase())) {
      const j = await fetchJSON('/api/forecast', { lat: lastSelection.lat, lon: lastSelection.lon, city: lastSelection.name });
      hideChoices();
      recentForecast = j;
      forecastOut.textContent = renderFiveDay(j.city, j.forecast, units);
      return;
    }

    const j = await fetchJSON('/api/forecast', { city });
    if (j.matches) { showChoices(j.matches, 'forecast'); return; }

    hideChoices();
    recentForecast = j;
    forecastOut.textContent = renderFiveDay(j.city, j.forecast, units);
  } catch (ex) {
    showError(ex.message || 'Network error. Please retry.');
  }
});

// Schedule Daily Reminder (via URNS) using form fields
btnSchedule.addEventListener('click', async () => {
  const city = input.value.trim();
  if (!city) { showError('City name is required to schedule.'); return; }
  clearError();

  // Build label for message replacement
  const label = (lastSelection && lastSelection.name) || city;

  // Read UI fields
  const title = (remTitle?.value || 'Daily Forecast').trim();
  // Replace {city} token if present
  const msgTemplate = (remMsg?.value || 'Check forecast for {city}').trim();
  const msg = msgTemplate.replace('{city}', label);

  // Parse schedule select
  const schedVal = remSchedule?.value || 'cron:0 7 * * *';
  const [kind, val] = schedVal.split(':', 2);

  // Build payload for URNS
  const payload = {
    app_id: 'weather-app',
    notify: { webhook: 'http://127.0.0.1:8080/hooks/reminder' },
    payload: { title, msg }
  };

  if (kind === 'cron') {
    payload.type = 'cron';
    payload.cron = val; // e.g., "*/1 * * * *" or "0 7 * * *"
  } else if (kind === 'time') {
    payload.type = 'time';
    payload.when = val; // ISO string
  } else {
    showError('Unknown schedule type.');
    return;
  }

  try {
    const r = await fetch('http://127.0.0.1:8081/reminders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-App-Key': 'dev-key' },
      body: JSON.stringify(payload)
    });
    const ct = r.headers.get('content-type') || '';
    const data = ct.includes('application/json') ? await r.json() : { error: await r.text() };
    if (!r.ok) throw new Error(data.error || `URNS error HTTP ${r.status}`);
    alert('Scheduled! Reminder ID: ' + data.reminder_id);
  } catch (ex) {
    showError(ex.message || 'Could not reach URNS service.');
  }
});

// Confirm notification Cancel
function openConfirmModal() {
  return new Promise((resolve) => {
    if (!modalEl || !confirmYes || !confirmNo || !modalCard) {
      // Fallback: native confirm
      const ok = window.confirm('Clear all notifications? This cannot be undone.');
      resolve(ok);
      return;
    }

    // Save the element that currently has focus to restore later
    const prevFocus = document.activeElement;

    // Show modal
    modalEl.classList.add('show');
    modalEl.style.display = 'flex';

    // Handlers
    const onYes = () => { cleanup(); resolve(true); };
    const onNo  = () => { cleanup(); resolve(false); };
    const onKey = (e) => {
      if (e.key === 'Escape') { e.preventDefault(); onNo(); }
      if (e.key === 'Tab') {
        // Basic focus trap between the two buttons
        const focusables = [confirmNo, confirmYes];
        const idx = focusables.indexOf(document.activeElement);
        if (idx === -1) { focusables[0].focus(); e.preventDefault(); return; }
        if (e.shiftKey && document.activeElement === focusables[0]) { e.preventDefault(); focusables[1].focus(); }
        else if (!e.shiftKey && document.activeElement === focusables[1]) { e.preventDefault(); focusables[0].focus(); }
      }
    };

    function cleanup() {
      modalEl.classList.remove('show');
      modalEl.style.display = 'none';
      confirmYes.removeEventListener('click', onYes);
      confirmNo.removeEventListener('click', onNo);
      document.removeEventListener('keydown', onKey);
      if (prevFocus && typeof prevFocus.focus === 'function') prevFocus.focus();
    }

    // Wire up events
    confirmYes.addEventListener('click', onYes);
    confirmNo.addEventListener('click', onNo);
    document.addEventListener('keydown', onKey);

    // Move focus into dialog
    modalCard.focus();
    confirmNo.focus();
  });
}


// Cancel all reminders (dev helper)
btnCancelAll.addEventListener('click', async () => {
  clearError();

  // Ask for explicit confirmation (IH-friendly)
  const confirmed = await openConfirmModal();
  if (!confirmed) return;

  try {
    const r = await fetch('http://127.0.0.1:8081/reminders', {
      method: 'DELETE',
      headers: { 'X-App-Key': 'dev-key' }
    });
    if (!r.ok) {
      const t = await r.text();
      throw new Error(`URNS delete-all failed: ${t || r.status}`);
    }
    // Success: give a subtle inline cue (avoid extra blocking alert)
    setBanner('All notifications were cleared.');
    setTimeout(() => setBanner(''), 5000);
  } catch (ex) {
    showError(ex.message || 'Could not cancel reminders.');
  }
});




// Units toggle
if (btnUnits) {
  btnUnits.addEventListener('click', () => {
    units = (units === 'F') ? 'C' : 'F';
    rerenderUsingUnits();
  });
  // Initialize button label on load
  rerenderUsingUnits();
}

// ---------- Start banner polling (after everything is wired) ----------
document.addEventListener('DOMContentLoaded', () => {
  refreshBanner();
  setInterval(refreshBanner, 15000); // every 15 seconds
});
