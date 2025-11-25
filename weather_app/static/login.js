// Login form
document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;
  const errorEl = document.getElementById('loginError');
  
  errorEl.textContent = '';
  
  if (!username || !password) {
    errorEl.textContent = 'Please enter username and password';
    return;
  }
  
  try {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        username_or_email: username,
        password: password
      })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Login failed');
    }
    
    console.log('Login successful:', data);
    
    // Store session token AND user data
    localStorage.setItem('session_token', data.session_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    
    // ✅ LOAD FAVORITES FROM SERVER (ONE TIME)
    try {
      const prefResp = await fetch('/api/auth/preferences', {
        credentials: 'include'
      });
      if (prefResp.ok) {
        const prefData = await prefResp.json();
        const serverFavs = prefData.favorites || [];
        
        // Save to user-specific localStorage key
        const key = `favorites_${data.user.username}`;
        localStorage.setItem(key, JSON.stringify(serverFavs));
        console.log('Loaded favorites from server:', serverFavs.length);
      }
    } catch (e) {
      console.error('Could not load favorites:', e);
    }
    
    // Redirect to home page
    window.location.href = '/';
    
  } catch (error) {
    console.error('Login error:', error);
    errorEl.textContent = error.message;
  }
});