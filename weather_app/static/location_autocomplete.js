// weather_app/static/location_autocomplete.js
/**
 * Location search autocomplete with personalized suggestions.
 * 
 * Features:
 * - Shows personalized suggestions as user types (min 3 chars)
 * - Falls back to geocoding for non-personalized results
 * - Tracks selections for future personalization
 * - Keyboard navigation (↑↓ Enter Esc)
 * - Sub-1-second response time
 * 
 * Usage:
 *   const autocomplete = new LocationAutocomplete(inputElement, {
 *     onSelect: (location) => {
 *       // Handle location selection
 *       console.log('Selected:', location);
 *     },
 *     minChars: 3,
 *     maxSuggestions: 4
 *   });
 */

class LocationAutocomplete {
  constructor(inputElement, options = {}) {
    this.input = inputElement;
    this.options = {
      onSelect: options.onSelect || (() => {}),
      minChars: options.minChars || 3,
      maxSuggestions: options.maxSuggestions || 4,
      debounceMs: options.debounceMs || 300,
      showGeocoding: options.showGeocoding !== false  // true by default
    };
    
    this.debounceTimer = null;
    this.selectedIndex = -1;
    this.currentSuggestions = [];
    
    // Create dropdown
    this.dropdown = this.createDropdown();
    this.setupInput();
  }
  
  setupInput() {
    // Make parent relative for absolute positioning
    const parent = this.input.parentElement;
    if (window.getComputedStyle(parent).position === 'static') {
      parent.style.position = 'relative';
    }
    parent.appendChild(this.dropdown);
    
    // Event listeners
    this.input.addEventListener('input', (e) => this.handleInput(e));
    this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
    this.input.addEventListener('blur', () => this.handleBlur());
    this.input.addEventListener('focus', () => this.handleFocus());
  }
  
  createDropdown() {
    const el = document.createElement('div');
    el.className = 'location-autocomplete-dropdown';
    el.style.cssText = `
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      background: white;
      border: 1px solid #ddd;
      border-top: none;
      max-height: 320px;
      overflow-y: auto;
      z-index: 1000;
      display: none;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    `;
    return el;
  }
  
  handleInput(e) {
    const query = e.target.value.trim();
    
    clearTimeout(this.debounceTimer);
    
    if (query.length < this.options.minChars) {
      this.hideDropdown();
      return;
    }
    
    // Debounce the search
    this.debounceTimer = setTimeout(() => {
      this.fetchSuggestions(query);
    }, this.options.debounceMs);
  }
  
  async fetchSuggestions(query) {
    const startTime = Date.now();
    
    try {
      // First, try personalized suggestions
      const personalizedSuggestions = await this.fetchPersonalizedSuggestions(query);
      
      // If we have enough personalized suggestions, use them
      if (personalizedSuggestions.length >= this.options.maxSuggestions) {
        this.renderSuggestions(personalizedSuggestions);
        return;
      }
      
      // Otherwise, supplement with geocoding
      if (this.options.showGeocoding) {
        const geocodingSuggestions = await this.fetchGeocodingSuggestions(query);
        
        // Merge and deduplicate
        const merged = this.mergeSuggestions(
          personalizedSuggestions,
          geocodingSuggestions,
          this.options.maxSuggestions
        );
        
        this.renderSuggestions(merged);
      } else {
        this.renderSuggestions(personalizedSuggestions);
      }
      
      const elapsed = Date.now() - startTime;
      console.log(`[Autocomplete] Query "${query}" took ${elapsed}ms`);
      
    } catch (error) {
      console.error('Error fetching suggestions:', error);
      this.hideDropdown();
    }
  }
  
  async fetchPersonalizedSuggestions(query) {
    try {
      const response = await fetch('/api/location-search/suggestions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          query: query,
          limit: this.options.maxSuggestions
        })
      });
      
      if (!response.ok) {
        return [];
      }
      
      const data = await response.json();
      return (data.suggestions || []).map(s => ({
        location_id: s.location_id,
        display_name: s.display_name,
        lat: s.lat,
        lon: s.lon,
        source: s.source,
        search_count: s.search_count
      }));
      
    } catch (error) {
      console.warn('Personalized suggestions failed:', error);
      return [];
    }
  }
  
  async fetchGeocodingSuggestions(query) {
    try {
      const url = 'https://geocoding-api.open-meteo.com/v1/search';
      const params = new URLSearchParams({
        name: query,
        count: this.options.maxSuggestions
      });
      
      const response = await fetch(`${url}?${params}`);
      if (!response.ok) return [];
      
      const data = await response.json();
      const results = data.results || [];
      
      return results.map(r => ({
        location_id: this.generateLocationId(r),
        display_name: this.formatDisplayName(r),
        lat: r.latitude,
        lon: r.longitude,
        source: 'standard',
        admin1: r.admin1,
        country: r.country
      }));
      
    } catch (error) {
      console.warn('Geocoding suggestions failed:', error);
      return [];
    }
  }
  
  generateLocationId(geocodeResult) {
    // Create a stable ID from the location
    const name = (geocodeResult.name || '').toLowerCase().replace(/\s+/g, '_');
    const country = (geocodeResult.country_code || '').toLowerCase();
    const admin = (geocodeResult.admin1 || '').toLowerCase().replace(/\s+/g, '_');
    return `${name}_${admin}_${country}`;
  }
  
  formatDisplayName(geocodeResult) {
    // Format: "City, State/Region, Country"
    const parts = [
      geocodeResult.name,
      geocodeResult.admin1,
      geocodeResult.country
    ].filter(Boolean);
    return parts.join(', ');
  }
  
  mergeSuggestions(personalized, geocoding, limit) {
    // Deduplicate by location_id
    const seen = new Set();
    const merged = [];
    
    // Add personalized first (higher priority)
    for (const item of personalized) {
      if (!seen.has(item.location_id)) {
        seen.add(item.location_id);
        merged.push(item);
      }
    }
    
    // Add geocoding to fill up to limit
    for (const item of geocoding) {
      if (merged.length >= limit) break;
      if (!seen.has(item.location_id)) {
        seen.add(item.location_id);
        merged.push(item);
      }
    }
    
    return merged.slice(0, limit);
  }
  
  renderSuggestions(suggestions) {
    this.dropdown.innerHTML = '';
    this.selectedIndex = -1;
    this.currentSuggestions = suggestions;
    
    if (suggestions.length === 0) {
      this.hideDropdown();
      return;
    }
    
    suggestions.forEach((suggestion, index) => {
      const item = this.createSuggestionItem(suggestion, index);
      this.dropdown.appendChild(item);
    });
    
    this.showDropdown();
  }
  
  createSuggestionItem(suggestion, index) {
    const item = document.createElement('div');
    item.className = 'location-autocomplete-item';
    item.style.cssText = `
      padding: 0.75rem;
      cursor: pointer;
      border-bottom: 1px solid #eee;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: background 0.1s;
    `;
    
    // Display name
    const nameEl = document.createElement('span');
    nameEl.textContent = suggestion.display_name;
    nameEl.style.flex = '1';
    item.appendChild(nameEl);
    
    // Badge for personalized results
    if (suggestion.source === 'frequent' || suggestion.source === 'recent') {
      const badge = document.createElement('span');
      badge.style.cssText = `
        font-size: 0.75rem;
        color: #666;
        background: #f0f0f0;
        padding: 2px 6px;
        border-radius: 3px;
        margin-left: 8px;
      `;
      
      if (suggestion.source === 'frequent') {
        badge.textContent = '⭐ Frequent';
        badge.title = `Searched ${suggestion.search_count} times`;
      } else {
        badge.textContent = '🕐 Recent';
      }
      
      item.appendChild(badge);
    }
    
    // Event handlers
    item.addEventListener('mouseenter', () => {
      this.selectedIndex = index;
      this.highlightSelected();
    });
    
    item.addEventListener('mousedown', (e) => {
      e.preventDefault(); // Prevent input blur
      this.selectSuggestion(suggestion);
    });
    
    return item;
  }
  
  handleKeydown(e) {
    const items = this.dropdown.children;
    
    if (items.length === 0) return;
    
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this.selectedIndex = Math.min(this.selectedIndex + 1, items.length - 1);
      this.highlightSelected();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
      this.highlightSelected();
    } else if (e.key === 'Enter' && this.selectedIndex >= 0) {
      e.preventDefault();
      const suggestion = this.currentSuggestions[this.selectedIndex];
      if (suggestion) {
        this.selectSuggestion(suggestion);
      }
    } else if (e.key === 'Escape') {
      this.hideDropdown();
    }
  }
  
  highlightSelected() {
    const items = this.dropdown.children;
    for (let i = 0; i < items.length; i++) {
      if (i === this.selectedIndex) {
        items[i].style.background = '#e8f4ff';
      } else {
        items[i].style.background = 'white';
      }
    }
    
    // Scroll into view
    if (items[this.selectedIndex]) {
      items[this.selectedIndex].scrollIntoView({ block: 'nearest' });
    }
  }
  
  async selectSuggestion(suggestion) {
    // Track the selection
    await this.trackSelection(suggestion);
    
    // Update input
    this.input.value = suggestion.display_name;
    
    // Hide dropdown
    this.hideDropdown();
    
    // Trigger callback
    this.options.onSelect(suggestion);
  }
  
  async trackSelection(suggestion) {
    try {
      await fetch('/api/location-search/track', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          location_id: suggestion.location_id,
          display_name: suggestion.display_name,
          lat: suggestion.lat,
          lon: suggestion.lon
        })
      });
    } catch (error) {
      // Tracking failure shouldn't break the app
      console.warn('Failed to track selection:', error);
    }
  }
  
  handleBlur() {
    // Delay to allow click events on dropdown
    setTimeout(() => this.hideDropdown(), 200);
  }
  
  handleFocus() {
    // Show dropdown if we have cached suggestions
    if (this.currentSuggestions.length > 0) {
      this.showDropdown();
    }
  }
  
  showDropdown() {
    this.dropdown.style.display = 'block';
  }
  
  hideDropdown() {
    this.dropdown.style.display = 'none';
  }
  
  destroy() {
    // Cleanup
    this.dropdown.remove();
    clearTimeout(this.debounceTimer);
  }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = LocationAutocomplete;
}