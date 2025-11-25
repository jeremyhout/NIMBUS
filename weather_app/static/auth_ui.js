/**
 * Auth UI Helper - Shows login/logout state across all pages
 * Add this to weather_app/static/auth_ui.js
 * Then include it in all your HTML pages after the navbar
 */

// Check login state and update UI
function updateAuthUI() {
  const token = localStorage.getItem('session_token');
  const userStr = localStorage.getItem('user');
  
  // Find the auth link (assumes you have an element with id="authLink")
  const authLink = document.getElementById('authLink');
  const userDisplay = document.getElementById('userDisplay');
  
  if (!authLink) return; // No auth link on this page
  
  if (token && userStr) {
    try {
      const user = JSON.parse(userStr);
      const username = user.username || 'User';
      
      // Show username
      if (userDisplay) {
        userDisplay.textContent = `Hello, ${username}`;
        userDisplay.style.marginRight = '0.5rem';
      }
      
      // Change link to Logout
      authLink.textContent = 'Logout';
      authLink.href = '#';
      authLink.onclick = async (e) => {
        e.preventDefault();
        await handleLogout();
      };
      
    } catch (e) {
      console.error('Error parsing user data:', e);
      clearAuthState();
    }
  } else {
    // Not logged in
    if (userDisplay) {
      userDisplay.textContent = '';
    }
    
    authLink.textContent = 'Login';
    authLink.href = '/login';
    authLink.onclick = null;
  }
}

// Handle logout
async function handleLogout() {
  const token = localStorage.getItem('session_token');
  
  try {
    // Call logout endpoint
    const response = await fetch('/api/auth/logout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include' // Include cookies
    });
    
    // Clear local storage regardless of server response
    clearAuthState();
    
    // Redirect to login page
    window.location.href = '/login';
    
  } catch (e) {
    console.error('Logout error:', e);
    // Still clear local state even if server call fails
    clearAuthState();
    window.location.href = '/login';
  }
}

// Clear authentication state
function clearAuthState() {
  localStorage.removeItem('session_token');
  localStorage.removeItem('user');
  
  // Clear ALL favorites keys
  localStorage.removeItem('favorites');
  
  // Clear user-specific favorites (get username from stored user data first)
  try {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      const user = JSON.parse(userStr);
      if (user.username) {
        localStorage.removeItem(`favorites_${user.username}`);
      }
    }
  } catch (e) {
    // Ignore errors
  }
}

// Verify session is still valid with server
async function verifySession() {
  const token = localStorage.getItem('session_token');
  if (!token) return false;
  
  try {
    const response = await fetch('/api/auth/me', {
      credentials: 'include'
    });
    
    if (!response.ok) {
      // Session expired or invalid
      clearAuthState();
      return false;
    }
    
    const data = await response.json();
    // Update stored user data
    localStorage.setItem('user', JSON.stringify(data.user));
    return true;
    
  } catch (e) {
    console.error('Session verification error:', e);
    return false;
  }
}

// Run on page load
document.addEventListener('DOMContentLoaded', () => {
  updateAuthUI();
  verifySession().then(valid => {
    if (!valid && localStorage.getItem('session_token')) {
      // Had a token but it's invalid - update UI
      updateAuthUI();
    }
  });
});