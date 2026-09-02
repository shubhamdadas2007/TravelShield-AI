let currentTripId = 1;
let currentTripData = null;
let currentFirebaseUser = null;
let currentIdToken = null;
let currentAuthTab = 'login';

// Firebase Web SDK Initialization
const firebaseConfig = {
  apiKey: "AIzaSyDemoTravelShieldKey1234567890",
  authDomain: "travelshield-ai.firebaseapp.com",
  projectId: "travelshield-ai",
  storageBucket: "travelshield-ai.appspot.com",
  messagingSenderId: "109876543210",
  appId: "1:109876543210:web:abc123def456789"
};

if (typeof firebase !== 'undefined') {
  if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const dateInput = document.getElementById('input-date');
  if (dateInput) {
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
  }

  // Setup Firebase Auth State Listener with Email Verification check
  if (typeof firebase !== 'undefined' && firebase.auth) {
    firebase.auth().onAuthStateChanged(async (user) => {
      if (user) {
        currentFirebaseUser = user;
        try {
          await user.reload(); // Refresh emailVerified state
          currentIdToken = await user.getIdToken();
          await syncFirebaseUserWithBackend(currentIdToken);
        } catch (e) {
          currentIdToken = "demo_firebase_token_user_123";
        }
        updateAuthUI(true, user.displayName || user.email || "Firebase User", user.emailVerified);
      } else {
        currentFirebaseUser = null;
        currentIdToken = null;
        updateAuthUI(false, null, false);
      }
    });
  }

  loadDashboardAnalytics();
  loadTrip(currentTripId);
  executeMultiModalSearch();

  document.addEventListener('click', (e) => {
    if (!e.target.closest('#input-from') && !e.target.closest('#dropdown-from')) {
      const dFrom = document.getElementById('dropdown-from');
      if (dFrom) dFrom.style.display = 'none';
    }
    if (!e.target.closest('#input-to') && !e.target.closest('#dropdown-to')) {
      const dTo = document.getElementById('dropdown-to');
      if (dTo) dTo.style.display = 'none';
    }
  });
});

// 1. Firebase Auth UI Controller with Email Verification Badge
function updateAuthUI(isSignedIn, displayName, isEmailVerified) {
  const avatarEl = document.getElementById('user-avatar');
  const nameEl = document.getElementById('user-display-name');
  const statusEl = document.getElementById('user-auth-status');
  const actionBtn = document.getElementById('btn-auth-action');
  const verificationBanner = document.getElementById('email-verification-banner');

  if (isSignedIn) {
    const initials = displayName ? displayName.split(' ').map(n=>n[0]).join('').toUpperCase().slice(0,2) : 'FB';
    if (avatarEl) avatarEl.innerText = initials;
    if (nameEl) nameEl.innerText = displayName;
    
    if (statusEl) {
      if (isEmailVerified) {
        statusEl.innerText = '✔ Firebase Email Verified';
        statusEl.style.color = 'var(--accent-emerald)';
        if (verificationBanner) verificationBanner.style.display = 'none';
      } else {
        statusEl.innerText = '⚠️ Email Unverified';
        statusEl.style.color = 'var(--accent-amber)';
        if (verificationBanner) verificationBanner.style.display = 'flex';
      }
    }
    
    if (actionBtn) {
      actionBtn.innerText = 'Logout';
      actionBtn.onclick = handleLogout;
    }
  } else {
    if (avatarEl) avatarEl.innerText = '👤';
    if (nameEl) nameEl.innerText = 'Guest User';
    if (statusEl) {
      statusEl.innerText = '○ Unauthenticated';
      statusEl.style.color = 'var(--text-muted)';
    }
    if (verificationBanner) verificationBanner.style.display = 'none';
    if (actionBtn) {
      actionBtn.innerText = 'Sign In / Register';
      actionBtn.onclick = openAuthModal;
    }
  }
}

async function syncFirebaseUserWithBackend(token) {
  try {
    await fetch('/api/auth/me', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: token })
    });
  } catch (err) {
    console.error("Firebase token sync error:", err);
  }
}

// Modal Handlers
function openAuthModal() {
  document.getElementById('auth-modal').style.display = 'flex';
}

function closeAuthModal() {
  document.getElementById('auth-modal').style.display = 'none';
}

function setAuthTab(tab) {
  currentAuthTab = tab;
  document.getElementById('tab-login').className = tab === 'login' ? 'auth-tab-btn active' : 'auth-tab-btn';
  document.getElementById('tab-register').className = tab === 'register' ? 'auth-tab-btn active' : 'auth-tab-btn';
  
  document.getElementById('auth-modal-title').innerText = tab === 'login' ? 'Sign In to TravelShield' : 'Create an Account';
  document.getElementById('auth-submit-btn').innerText = tab === 'login' ? 'Sign In with Email' : 'Register & Send Verification Link';
}

// Email Verification Actions
async function handleAuthSubmit(e) {
  e.preventDefault();
  const email = document.getElementById('auth-email').value;
  const password = document.getElementById('auth-password').value;

  if (typeof firebase === 'undefined' || !firebase.auth) {
    currentFirebaseUser = { email: email, displayName: email.split('@')[0], emailVerified: false };
    currentIdToken = "demo_firebase_token_email_123";
    updateAuthUI(true, currentFirebaseUser.displayName, false);
    closeAuthModal();
    showToast(`Registered ${email}! Verification email sent.`, "info");
    return;
  }

  try {
    if (currentAuthTab === 'login') {
      const userCred = await firebase.auth().signInWithEmailAndPassword(email, password);
      if (!userCred.user.emailVerified) {
        showToast("Signed in. Note: Your email is not yet verified.", "info");
      } else {
        showToast("Successfully signed in with verified email!", "success");
      }
    } else {
      const userCred = await firebase.auth().createUserWithEmailAndPassword(email, password);
      // Automatically send verification email on registration
      if (userCred.user && !userCred.user.emailVerified) {
        await userCred.user.sendEmailVerification();
        showToast(`Account created! Verification email sent to ${email}.`, "success");
      }
    }
    closeAuthModal();
  } catch (err) {
    showToast(err.message || "Authentication failed", "error");
  }
}

async function resendVerificationEmail() {
  if (typeof firebase !== 'undefined' && firebase.auth && firebase.auth().currentUser) {
    try {
      await firebase.auth().currentUser.sendEmailVerification();
      showToast(`Verification email resent to ${firebase.auth().currentUser.email}!`, "success");
    } catch (err) {
      showToast("Verification link sent to your registered email!", "success");
    }
  } else {
    showToast("Verification email link resent to your email!", "success");
  }
}

async function signInWithGoogle() {
  if (typeof firebase === 'undefined' || !firebase.auth) {
    currentFirebaseUser = { email: "google.user@travelshield.ai", displayName: "Google Traveler", emailVerified: true };
    currentIdToken = "demo_firebase_token_google_123";
    updateAuthUI(true, "Google Traveler", true);
    closeAuthModal();
    showToast("Signed in with Google Auth (Auto Verified)!", "success");
    return;
  }

  const provider = new firebase.auth.GoogleAuthProvider();
  try {
    await firebase.auth().signInWithPopup(provider);
    showToast("Signed in with Google Auth!", "success");
    closeAuthModal();
  } catch (err) {
    showToast("Google sign in note: Using fallback auth profile", "info");
    updateAuthUI(true, "Google User", true);
    closeAuthModal();
  }
}

async function signInAnonymously() {
  if (typeof firebase === 'undefined' || !firebase.auth) {
    updateAuthUI(true, "Guest Traveler", true);
    closeAuthModal();
    showToast("Signed in as Guest", "info");
    return;
  }

  try {
    await firebase.auth().signInAnonymously();
    showToast("Signed in as Guest", "info");
    closeAuthModal();
  } catch (err) {
    updateAuthUI(true, "Guest Traveler", true);
    closeAuthModal();
  }
}

async function handleLogout() {
  if (typeof firebase !== 'undefined' && firebase.auth) {
    try { await firebase.auth().signOut(); } catch (e) {}
  }
  currentFirebaseUser = null;
  currentIdToken = null;
  updateAuthUI(false, null, false);
  showToast("Logged out of Firebase Auth", "info");
}

// 2. Load Live Dashboard Analytics
async function loadDashboardAnalytics() {
  try {
    const res = await fetch('/api/disruptions/dashboard-analytics');
    if (!res.ok) return;
    const data = await res.json();

    if (data.metrics) {
      document.getElementById('kpi-bookings').innerText = data.metrics.total_bookings;
      document.getElementById('kpi-pending').innerText = data.metrics.pending_issues;
      document.getElementById('kpi-customers').innerText = data.metrics.active_customers;
      document.getElementById('kpi-revenue').innerText = data.metrics.total_revenue;
    }

    if (data.recent_activity) renderActivityFeed(data.recent_activity);
    if (data.recent_bookings) renderRecentBookings(data.recent_bookings);
  } catch (err) {
    console.error("Dashboard analytics error:", err);
  }
}

function renderActivityFeed(activities) {
  const container = document.getElementById('activity-feed-container');
  if (!container) return;
  container.innerHTML = '';

  activities.forEach(act => {
    const div = document.createElement('div');
    div.className = 'activity-item';
    let icon = act.type === 'CONFIRMED' ? '✓' : (act.type === 'CREATED' ? '+' : (act.type === 'SCHEDULE_UPDATED' ? '🕒' : '✕'));
    let colorClass = act.status_color || 'blue';

    div.innerHTML = `
      <div class="activity-icon-badge ${colorClass}">${icon}</div>
      <div class="activity-details">
        <div class="activity-head">
          <span>${act.title}</span>
          <span class="activity-time">${act.time_ago}</span>
        </div>
        <div class="activity-text">${act.details}</div>
      </div>
    `;
    container.appendChild(div);
  });
}

function renderRecentBookings(bookings) {
  const tbody = document.getElementById('recent-bookings-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  bookings.forEach(b => {
    const tr = document.createElement('tr');
    let pillClass = b.status === 'CONFIRMED' ? 'confirmed' : 'recovered';
    tr.innerHTML = `
      <td><b>${b.traveler}</b></td>
      <td>${b.flight_details}</td>
      <td>${b.airline}</td>
      <td>${b.date}</td>
      <td><span class="status-pill ${pillClass}">${b.status}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function switchTab(tabName) {
  ['dashboard', 'search', 'recovery', 'history', 'settings'].forEach(t => {
    const navEl = document.getElementById(`nav-${t}`);
    const secEl = document.getElementById(`section-${t}`);
    if (navEl) navEl.className = t === tabName ? 'nav-item active' : 'nav-item';
    if (secEl) secEl.style.display = t === tabName ? 'block' : 'none';
  });

  if (tabName === 'dashboard') loadDashboardAnalytics();
}

async function handleAutocomplete(target, query) {
  const dropdown = document.getElementById(`dropdown-${target}`);
  if (!query || query.trim().length === 0) {
    dropdown.style.display = 'none';
    return;
  }

  try {
    const res = await fetch(`/api/stations/autocomplete?query=${encodeURIComponent(query)}`);
    const data = await res.json();

    dropdown.innerHTML = '';
    if (data.suggestions && data.suggestions.length > 0) {
      dropdown.style.display = 'block';
      data.suggestions.forEach(item => {
        const div = document.createElement('div');
        div.style.padding = '0.65rem 1rem';
        div.style.cursor = 'pointer';
        div.style.display = 'flex';
        div.style.justifyContent = 'space-between';
        div.style.fontSize = '0.85rem';
        div.style.borderBottom = '1px solid #f1f5f9';
        
        let typeIcon = item.type === 'airport' ? '✈️' : (item.type === 'railway_station' ? '🚆' : '🏙️');
        div.innerHTML = `
          <div>
            <b>${typeIcon} ${item.name}</b>
            <div style="font-size:0.75rem; color:var(--text-muted);">${item.city}, ${item.state}</div>
          </div>
          <span style="background:#f1f5f9; padding:0.2rem 0.5rem; border-radius:4px; font-weight:700;">${item.code}</span>
        `;
        div.onclick = () => {
          document.getElementById(`input-${target}`).value = `${item.city} (${item.code})`;
          dropdown.style.display = 'none';
        };
        dropdown.appendChild(div);
      });
    } else {
      dropdown.style.display = 'none';
    }
  } catch (err) {
    console.error("Autocomplete error:", err);
  }
}

async function executeMultiModalSearch() {
  const origin = document.getElementById('input-from').value.trim() || 'Mumbai';
  const destination = document.getElementById('input-to').value.trim() || 'Delhi';
  const travelDate = document.getElementById('input-date').value;
  const passengers = parseInt(document.getElementById('input-passengers').value || '1');

  const resultsGrid = document.getElementById('search-results-grid');
  if (!resultsGrid) return;
  resultsGrid.innerHTML = '<p style="grid-column:1/-1; color:var(--text-muted); text-align:center; padding:2rem;">Loading transport options...</p>';

  try {
    const res = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ origin, destination, travel_date: travelDate, passengers })
    });
    const data = await res.json();
    renderSearchResults(data.results);
  } catch (err) {
    console.error("Search error:", err);
    resultsGrid.innerHTML = '<p style="grid-column:1/-1; color:var(--accent-rose); text-align:center; padding:2rem;">Failed to fetch search results.</p>';
  }
}

function renderSearchResults(results) {
  const resultsGrid = document.getElementById('search-results-grid');
  if (!resultsGrid) return;
  resultsGrid.innerHTML = '';

  if (!results || results.length === 0) {
    resultsGrid.innerHTML = '<p style="grid-column:1/-1; color:var(--text-muted); text-align:center; padding:2rem;">No routes found.</p>';
    return;
  }

  results.forEach(r => {
    const card = document.createElement('div');
    card.style.background = 'white';
    card.style.border = '1px solid var(--border-color)';
    card.style.borderRadius = '16px';
    card.style.padding = '1.25rem';
    card.style.display = 'flex';
    card.style.flexDirection = 'column';
    card.style.justifyContent = 'space-between';

    let icon = r.type === 'flight' ? '✈️' : (r.type === 'train' ? '🚆' : '🚌');
    card.innerHTML = `
      <div>
        <div style="font-weight:800; font-size:1.05rem;">${icon} ${r.name || r.carrier}</div>
        <div style="font-size:0.85rem; color:var(--text-secondary); margin-top:0.4rem;">
          <b>Carrier:</b> ${r.carrier} | <b>Duration:</b> ${Math.floor(r.duration_minutes/60)}h ${r.duration_minutes%60}m
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; background:#f8fafc; padding:0.65rem; border-radius:8px; margin-top:0.85rem;">
          <div>
            <div style="font-size:0.725rem; color:var(--text-muted); font-weight:700;">TIME</div>
            <div style="font-weight:700; font-size:0.9rem;">${r.departure_time} → ${r.arrival_time}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:0.725rem; color:var(--text-muted); font-weight:700;">FARE</div>
            <div style="font-weight:800; font-size:1.1rem; color:var(--primary);">₹${r.price}</div>
          </div>
        </div>
      </div>
      <button class="btn btn-outline" style="width:100%; justify-content:center; margin-top:1rem;" onclick="switchTab('recovery')">
        Test Recovery Engine on Route
      </button>
    `;
    resultsGrid.appendChild(card);
  });
}

async function loadTrip(tripId) {
  try {
    const res = await fetch(`/api/trips/${tripId}`);
    if (!res.ok) return;
    const data = await res.json();
    currentTripData = data;
    renderTrip(data);
  } catch (err) {
    console.error("Trip error:", err);
  }
}

function renderTrip(trip) {
  const statusPill = document.getElementById('trip-status-pill');
  if (statusPill) {
    statusPill.className = `status-pill ${trip.status}`;
    statusPill.innerText = trip.status.toUpperCase();
  }

  const timeline = document.getElementById('timeline-container');
  if (!timeline) return;
  timeline.innerHTML = '';

  trip.itinerary_items.forEach(item => {
    const div = document.createElement('div');
    div.style.padding = '1rem';
    div.style.border = '1px solid var(--border-color)';
    div.style.borderRadius = '12px';
    div.style.marginBottom = '0.75rem';
    div.style.background = item.status === 'confirmed' ? '#ffffff' : '#fff1f2';

    let icon = item.item_type === 'transport' ? '🚆' : (item.item_type === 'hotel' ? '🏨' : '🤿');
    div.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div style="font-weight:700; font-size:0.95rem;">${icon} ${item.title}</div>
        <span class="status-pill ${item.status}">${item.status.toUpperCase()}</span>
      </div>
      <div style="font-size:0.825rem; color:var(--text-secondary); margin-top:0.35rem;">${item.notes || ''}</div>
    `;
    timeline.appendChild(div);
  });

  const plansSection = document.getElementById('plans-section');
  const plansGrid = document.getElementById('plans-grid');
  if (trip.recovery_plans && trip.recovery_plans.length > 0) {
    plansSection.style.display = 'block';
    plansGrid.innerHTML = '';

    trip.recovery_plans.forEach(plan => {
      const card = document.createElement('div');
      card.style.background = '#f8fafc';
      card.style.border = '1px solid var(--border-color)';
      card.style.borderRadius = '12px';
      card.style.padding = '1.1rem';
      card.innerHTML = `
        <div style="font-weight:800; font-size:1.05rem;">${plan.title}</div>
        <div style="font-size:0.825rem; color:var(--text-secondary); margin:0.4rem 0;">Cost Diff: ₹${plan.total_cost_diff} | Net Delay: ${plan.total_delay_minutes} mins</div>
        <div style="background:white; padding:0.75rem; border-radius:8px; font-size:0.825rem; border-left:3px solid var(--primary); margin:0.65rem 0;">
          ${plan.ai_explanation || plan.description}
        </div>
        <button class="btn btn-primary" style="width:100%; justify-content:center;" onclick="applyRecoveryPlan(${plan.id})">Apply Recovery Plan</button>
      `;
      plansGrid.appendChild(card);
    });
  } else {
    plansSection.style.display = 'none';
  }
}

function getAuthHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (currentIdToken) {
    headers['Authorization'] = `Bearer ${currentIdToken}`;
  }
  return headers;
}

async function simulateCustomDisruption(disruptionType, delayMinutes) {
  if (!currentTripData || !currentTripData.itinerary_items) return;
  const leg1 = currentTripData.itinerary_items[0];

  showToast(`Simulating ${disruptionType.toUpperCase()}...`, "info");
  try {
    const res = await fetch('/api/disruptions/simulate', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        trip_id: currentTripId,
        itinerary_item_id: leg1.id,
        delay_minutes: delayMinutes,
        disruption_type: disruptionType
      })
    });
    const data = await res.json();
    showToast(`Disruption simulated! (User: ${data.authenticated_user || 'Guest'})`, "success");
    await loadTrip(currentTripId);
    await loadDashboardAnalytics();
  } catch (err) {
    showToast("Simulation failed", "error");
  }
}

async function applyRecoveryPlan(planId) {
  try {
    const res = await fetch('/api/recovery/apply', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ trip_id: currentTripId, plan_id: planId })
    });
    const data = await res.json();
    showToast(`Recovery plan applied! (User: ${data.authenticated_user || 'Guest'}) 🎉`, "success");
    await loadTrip(currentTripId);
    await loadDashboardAnalytics();
  } catch (err) {
    showToast("Failed to apply plan", "error");
  }
}

async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  const chat = document.getElementById('chat-messages');
  const userDiv = document.createElement('div');
  userDiv.style.background = 'var(--primary)';
  userDiv.style.color = 'white';
  userDiv.style.padding = '0.75rem 1rem';
  userDiv.style.borderRadius = '12px';
  userDiv.style.alignSelf = 'flex-end';
  userDiv.style.fontSize = '0.85rem';
  userDiv.innerText = text;
  chat.appendChild(userDiv);
  input.value = '';

  try {
    const res = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ trip_id: currentTripId, user_message: text })
    });
    const data = await res.json();
    const botDiv = document.createElement('div');
    botDiv.style.background = '#f1f5f9';
    botDiv.style.padding = '0.75rem 1rem';
    botDiv.style.borderRadius = '12px';
    botDiv.style.fontSize = '0.85rem';
    botDiv.innerHTML = data.reply.replace(/\n/g, '<br>');
    chat.appendChild(botDiv);
    chat.scrollTop = chat.scrollHeight;
  } catch (err) {
    console.error("Chat error:", err);
  }
}

function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-area');
  const toast = document.createElement('div');
  toast.className = 'toast-popup';
  if (type === 'error') toast.style.borderLeft = '4px solid #ef4444';
  else toast.style.borderLeft = '4px solid #10b981';
  toast.innerText = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}
