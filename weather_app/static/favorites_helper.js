/**
 * Shared Favorites Helper - SIMPLE VERSION
 * Place this in: weather_app/static/favorites_helper.js
 * Include it BEFORE home.js, five_day.js, and favorites.js
 */

// Check if user is logged in
function isLoggedIn() {
  return !!localStorage.getItem('session_token');
}

// Get current username
function getCurrentUsername() {
  try {
    const userStr = localStorage.getItem('user');
    if (!userStr) return null;
    const user = JSON.parse(userStr);
    return user.username;
  } catch {
    return null;
  }
}

// Get favorites from localStorage (per-user key)
function getFavs() {
  try {
    const username = getCurrentUsername();
    const key = username ? `favorites_${username}` : 'favorites';
    const data = localStorage.getItem(key);
    console.log('[getFavs DEBUG] username:', username);
    console.log('[getFavs DEBUG] key:', key);
    console.log('[getFavs DEBUG] raw data:', data);
    const parsed = JSON.parse(data || '[]');
    console.log('[getFavs DEBUG] parsed:', parsed);
    return parsed;
  } catch (e) {
    console.error('[getFavs ERROR]:', e);
    return [];
  }
}

// Save favorites to localStorage (per-user key)
function saveFavs(list) {
  try {
    const username = getCurrentUsername();
    const key = username ? `favorites_${username}` : 'favorites';
    localStorage.setItem(key, JSON.stringify(list));
  } catch {}
}

// Save favorites to server
async function saveFavoritesToServer(list) {
  if (!isLoggedIn()) {
    return;
  }
  
  try {
    const response = await fetch('/api/auth/preferences', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({ favorites: list })
    });
    
    if (response.ok) {
      console.log('Favorites synced to server');
    }
  } catch (e) {
    console.error('Error syncing favorites:', e);
  }
}

// Add favorite (saves both locally and to server)
function addFav(item) {
  const list = getFavs();
  if (!list.some(f => f.name === item.name && f.lat === item.lat && f.lon === item.lon)) {
    list.push(item);
    saveFavs(list);
    saveFavoritesToServer(list);
    return true;
  }
  return false;
}

// Remove favorite (saves both locally and to server)
function removeFav(idx) {
  const list = getFavs();
  if (idx >= 0 && idx < list.length) {
    list.splice(idx, 1);
    saveFavs(list);
    saveFavoritesToServer(list);
  }
}