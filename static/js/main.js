/**
 * FitBuddy Authentication, Progress Tracking, Community Feed, Stripe Billing & PWA Controller
 */

const TOKEN_KEY = 'fitbuddy_access_token';
const USER_KEY = 'fitbuddy_user';

function getAuthToken() {
    try {
        return localStorage.getItem(TOKEN_KEY);
    } catch (e) {
        return null;
    }
}

function getStoredUser() {
    try {
        const u = localStorage.getItem(USER_KEY);
        return u ? JSON.parse(u) : null;
    } catch (e) {
        return null;
    }
}

function setAuthSession(token, user) {
    try {
        if (token) localStorage.setItem(TOKEN_KEY, token);
        if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch (e) {
        console.error('Failed to write to localStorage:', e);
    }
}

function clearAuthSession() {
    try {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
    } catch (e) {
        console.error('Failed to clear localStorage:', e);
    }
}

async function authFetch(url, options = {}) {
    const token = getAuthToken();
    const headers = options.headers ? { ...options.headers } : {};

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(url, { ...options, headers });

        if (response.status === 401) {
            clearAuthSession();
            updateNavAuthState();
            if (window.location.pathname === '/dashboard') {
                const loading = document.getElementById('dashboard-loading');
                const unauth = document.getElementById('dashboard-unauth');
                const main = document.getElementById('dashboard-main');
                if (loading) loading.style.display = 'none';
                if (main) main.style.display = 'none';
                if (unauth) unauth.style.display = 'block';
            }
        }

        return response;
    } catch (networkError) {
        console.error(`Network or fetch error on ${url}:`, networkError);
        throw networkError;
    }
}

function updateNavAuthState() {
    const token = getAuthToken();
    const guestNav = document.getElementById('nav-guest');
    const authNav = document.getElementById('nav-authenticated');
    const userDisplay = document.getElementById('nav-username-display');
    const dashLink = document.getElementById('nav-dashboard-link');
    const tierBadge = document.getElementById('nav-tier-badge');
    const upgradeBtn = document.getElementById('upgradeProBtn');

    if (token) {
        const user = getStoredUser();
        if (guestNav) guestNav.style.display = 'none';
        if (authNav) authNav.style.display = 'flex';
        if (dashLink) dashLink.style.display = 'inline-block';
        if (userDisplay) {
            userDisplay.textContent = user ? `👤 ${user.username || user.user_id}` : '👤 Athlete';
        }
        if (user && user.tier === 'pro') {
            if (tierBadge) {
                tierBadge.style.display = 'inline-block';
                tierBadge.textContent = '⭐ PRO';
            }
            if (upgradeBtn) upgradeBtn.style.display = 'none';
        } else {
            if (tierBadge) tierBadge.style.display = 'none';
            if (upgradeBtn) upgradeBtn.style.display = 'inline-block';
        }
    } else {
        if (guestNav) guestNav.style.display = 'flex';
        if (authNav) authNav.style.display = 'none';
        if (dashLink) dashLink.style.display = 'none';
        if (tierBadge) tierBadge.style.display = 'none';
        if (upgradeBtn) upgradeBtn.style.display = 'none';
    }
}

async function updateStreakStats() {
    try {
        const res = await authFetch('/api/users/streak');
        if (res && res.ok) {
            const data = await res.json();
            const currEl = document.getElementById('streak-current');
            const longEl = document.getElementById('streak-longest');
            const compEl = document.getElementById('streak-completed');
            const rateEl = document.getElementById('streak-rate');
            const todayBadge = document.getElementById('streak-today-badge');

            if (currEl) currEl.textContent = data.current_streak ?? 0;
            if (longEl) longEl.textContent = data.longest_streak ?? 0;
            if (compEl) compEl.textContent = data.total_completed ?? 0;
            if (rateEl) rateEl.textContent = `${data.completion_rate ?? 0}%`;

            if (todayBadge) {
                if (data.active_today) {
                    todayBadge.className = 'badge badge-success';
                    todayBadge.textContent = 'Active Today 🎉';
                } else {
                    todayBadge.className = 'badge badge-warning';
                    todayBadge.textContent = 'Pending Today';
                }
            }
        }
    } catch (err) {
        console.warn('Could not refresh streak stats:', err);
    }
}

async function loadDashboardData() {
    const loadingDiv = document.getElementById('dashboard-loading');
    const unauthDiv = document.getElementById('dashboard-unauth');
    const mainDiv = document.getElementById('dashboard-main');

    if (!loadingDiv || !mainDiv) return;

    const token = getAuthToken();
    if (!token) {
        if (loadingDiv) loadingDiv.style.display = 'none';
        if (mainDiv) mainDiv.style.display = 'none';
        if (unauthDiv) unauthDiv.style.display = 'block';
        return;
    }

    try {
        const userRes = await authFetch('/api/auth/me');
        if (!userRes || !userRes.ok) {
            throw new Error('Failed to load profile');
        }
        const user = await userRes.json();
        setAuthSession(token, user);
        updateNavAuthState();

        const nameEl = document.getElementById('dash-username');
        const emailEl = document.getElementById('dash-email');
        const goalEl = document.getElementById('dash-goal');
        const intensityEl = document.getElementById('dash-intensity');
        const metricsEl = document.getElementById('dash-metrics');
        const countEl = document.getElementById('dash-plan-count');

        if (nameEl) nameEl.textContent = user.username || user.user_id || 'Athlete';
        if (emailEl) emailEl.textContent = user.email || 'N/A';
        if (goalEl) goalEl.textContent = user.goal || 'General Fitness';
        if (intensityEl) intensityEl.textContent = user.intensity || 'Medium';
        if (metricsEl) metricsEl.textContent = `${user.age || '--'} yrs / ${user.weight || '--'} kg`;

        await updateStreakStats();

        const plansRes = await authFetch('/api/plans');
        if (!plansRes || !plansRes.ok) {
            throw new Error('Failed to load saved plans');
        }
        const plans = await plansRes.json();

        if (countEl) countEl.textContent = Array.isArray(plans) ? plans.length : 0;

        const tableBody = document.getElementById('plans-table-body');
        const tableContainer = document.getElementById('plans-table-container');
        const noPlansMsg = document.getElementById('no-plans-msg');

        if (tableBody) {
            tableBody.innerHTML = '';
            if (!Array.isArray(plans) || plans.length === 0) {
                if (tableContainer) tableContainer.style.display = 'none';
                if (noPlansMsg) noPlansMsg.style.display = 'block';
            } else {
                if (tableContainer) tableContainer.style.display = 'block';
                if (noPlansMsg) noPlansMsg.style.display = 'none';

                plans.forEach((plan) => {
                    const row = document.createElement('tr');
                    const createdDate = new Date(plan.created_at).toLocaleString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    });

                    const isRevised = !!plan.updated_plan;
                    const planText = isRevised ? plan.updated_plan : plan.original_plan;
                    const statusBadge = isRevised 
                        ? `<span class="badge badge-warning">Revised</span>` 
                        : `<span class="badge badge-success">Original</span>`;

                    const completedDays = new Set((plan.workout_logs || []).map(l => l.day_number));
                    let dayChipsHtml = '<div class="day-track-grid">';
                    for (let day = 1; day <= 7; day++) {
                        const isDone = completedDays.has(day);
                        dayChipsHtml += `
                            <button type="button" 
                                    class="day-chip ${isDone ? 'completed' : ''}" 
                                    data-plan-id="${plan.id}" 
                                    data-day="${day}" 
                                    title="Click to toggle Day ${day} completion">
                                D${day}
                            </button>
                        `;
                    }
                    dayChipsHtml += '</div>';

                    const shareBtnText = plan.is_public ? '🌐 Public' : '🔒 Private';
                    const shareBtnClass = plan.is_public ? 'badge badge-success' : 'badge badge-warning';

                    row.innerHTML = `
                        <td><strong>#${plan.id}</strong></td>
                        <td style="color: var(--text-muted); font-size: 0.85rem;">${createdDate}</td>
                        <td>
                            ${statusBadge}<br/>
                            <button class="toggle-public-btn ${shareBtnClass}" data-id="${plan.id}" style="border: none; cursor: pointer; margin-top: 0.35rem;" title="Click to toggle public sharing">
                                ${shareBtnText}
                            </button>
                        </td>
                        <td>${dayChipsHtml}</td>
                        <td>
                            <details>
                                <summary style="color: var(--primary); font-weight: 600; font-size: 0.88rem; cursor: pointer;">
                                    View 7-Day Workout
                                </summary>
                                <div style="margin-top: 0.5rem; padding: 0.75rem; background: #f8fafc; border-radius: 6px; font-size: 0.82rem; max-height: 220px; overflow-y: auto; white-space: pre-wrap; border: 1px solid var(--border);">
                                    ${planText}
                                </div>
                            </details>
                        </td>
                        <td>
                            ${plan.nutrition_tip ? `
                                <details>
                                    <summary style="color: #059669; font-weight: 600; font-size: 0.88rem; cursor: pointer;">
                                        View Nutrition
                                    </summary>
                                    <div style="margin-top: 0.5rem; padding: 0.75rem; background: #ecfdf5; border-radius: 6px; font-size: 0.82rem; max-height: 180px; overflow-y: auto; white-space: pre-wrap; border: 1px solid #a7f3d0; color: #064e3b;">
                                        ${plan.nutrition_tip}
                                    </div>
                                </details>
                            ` : '<span style="color: var(--text-muted); font-size: 0.85rem;">None</span>'}
                        </td>
                        <td style="text-align: right; white-space: nowrap;">
                            <a href="/api/plans/${plan.id}/pdf" class="btn-secondary" style="padding: 0.35rem 0.65rem; font-size: 0.8rem; margin-right: 0.35rem; display: inline-flex;" title="Download PDF">
                                📄 PDF
                            </a>
                            <a href="/feedback/${plan.user_id}" class="btn-secondary" style="padding: 0.35rem 0.65rem; font-size: 0.8rem; margin-right: 0.35rem; display: inline-flex;" title="Revise plan">
                                ✏️ Revise
                            </a>
                            <button class="btn-secondary delete-plan-btn" data-id="${plan.id}" style="padding: 0.35rem 0.65rem; font-size: 0.8rem; color: var(--danger); border-color: #fecaca; display: inline-flex;" title="Delete plan">
                                🗑️
                            </button>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });

                document.querySelectorAll('.toggle-public-btn').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        e.preventDefault();
                        const pId = btn.getAttribute('data-id');
                        try {
                            const pubRes = await authFetch(`/api/plans/${pId}/toggle-public`, { method: 'POST' });
                            if (pubRes && pubRes.ok) {
                                await loadDashboardData();
                            }
                        } catch (err) {
                            console.error('Public toggle error:', err);
                        }
                    });
                });

                document.querySelectorAll('.day-chip').forEach(chip => {
                    chip.addEventListener('click', async (e) => {
                        e.preventDefault();
                        const pId = chip.getAttribute('data-plan-id');
                        const dayNum = chip.getAttribute('data-day');
                        chip.style.opacity = '0.5';

                        try {
                            const toggleRes = await authFetch(`/api/plans/${pId}/toggle-day/${dayNum}`, {
                                method: 'POST'
                            });
                            if (toggleRes && toggleRes.ok) {
                                const toggleData = await toggleRes.json();
                                if (toggleData.completed) {
                                    chip.classList.add('completed');
                                } else {
                                    chip.classList.remove('completed');
                                }
                                await updateStreakStats();
                            }
                        } catch (err) {
                            console.error('Toggle error:', err);
                        } finally {
                            chip.style.opacity = '1';
                        }
                    });
                });

                document.querySelectorAll('.delete-plan-btn').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        e.preventDefault();
                        const planId = btn.getAttribute('data-id');
                        if (confirm(`Are you sure you want to delete Plan #${planId}? This action cannot be undone.`)) {
                            btn.disabled = true;
                            btn.textContent = '...';
                            try {
                                const delRes = await authFetch(`/api/plans/${planId}`, {
                                    method: 'DELETE'
                                });
                                if (delRes && delRes.ok) {
                                    await loadDashboardData();
                                }
                            } catch (err) {
                                alert('Error deleting plan: ' + err.message);
                            }
                        }
                    });
                });
            }
        }

        if (loadingDiv) loadingDiv.style.display = 'none';
        if (unauthDiv) unauthDiv.style.display = 'none';
        if (mainDiv) mainDiv.style.display = 'block';

    } catch (err) {
        console.error('Dashboard load error:', err);
        if (loadingDiv) loadingDiv.style.display = 'none';
        if (unauthDiv) unauthDiv.style.display = 'block';
    }
}

/**
 * Loads Community Feed & Global Streak Leaderboard on /community
 */
async function loadCommunityPage() {
    const feedContainer = document.getElementById('community-feed-container');
    const feedLoading = document.getElementById('community-loading');
    const noPlansMsg = document.getElementById('no-community-plans');
    const lbTableWrap = document.getElementById('leaderboard-table-wrap');
    const lbLoading = document.getElementById('leaderboard-loading');
    const lbTbody = document.getElementById('leaderboard-tbody');

    if (!feedContainer) return;

    try {
        // 1. Fetch Leaderboard
        const lbRes = await fetch('/api/community/leaderboard');
        if (lbRes.ok) {
            const leaderboard = await lbRes.json();
            if (lbTbody) {
                lbTbody.innerHTML = '';
                leaderboard.forEach(entry => {
                    const row = document.createElement('tr');
                    const medal = entry.rank === 1 ? '🥇' : (entry.rank === 2 ? '🥈' : (entry.rank === 3 ? '🥉' : `#${entry.rank}`));
                    const proBadge = entry.tier === 'pro' ? '<span class="badge badge-warning" style="font-size: 0.65rem;">PRO</span>' : '';
                    row.innerHTML = `
                        <td><strong>${medal}</strong></td>
                        <td><strong>${entry.username}</strong> ${proBadge}</td>
                        <td style="color: var(--primary); font-weight: 700;">🔥 ${entry.current_streak}d</td>
                        <td>${entry.total_completed}</td>
                        <td>${entry.completion_rate}%</td>
                    `;
                    lbTbody.appendChild(row);
                });
                if (lbLoading) lbLoading.style.display = 'none';
                if (lbTableWrap) lbTableWrap.style.display = 'block';
            }
        }

        // 2. Fetch Public Plans
        const token = getAuthToken();
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        const plansRes = await fetch('/api/community/plans', { headers });

        if (plansRes.ok) {
            const plans = await plansRes.json();
            feedContainer.innerHTML = '';
            if (feedLoading) feedLoading.style.display = 'none';

            if (plans.length === 0) {
                if (noPlansMsg) noPlansMsg.style.display = 'block';
            } else {
                if (noPlansMsg) noPlansMsg.style.display = 'none';

                plans.forEach(plan => {
                    const card = document.createElement('div');
                    card.className = 'card';
                    card.style.padding = '1.5rem';

                    const planText = plan.updated_plan || plan.original_plan;
                    const proBadge = plan.author_tier === 'pro' ? '<span class="badge badge-warning">PRO</span>' : '';

                    card.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem;">
                            <div>
                                <h3 style="font-size: 1.15rem; color: var(--dark);">
                                    👤 ${plan.author_username} ${proBadge}
                                </h3>
                                <span style="font-size: 0.8rem; color: var(--text-muted);">${new Date(plan.created_at).toLocaleDateString()} • Goal: <strong>${plan.goal}</strong> (${plan.intensity})</span>
                            </div>
                            <button class="btn-secondary like-plan-btn" data-id="${plan.id}" style="padding: 0.35rem 0.75rem; font-size: 0.85rem; border-color: #cbd5e1;">
                                <span>${plan.is_liked_by_me ? '❤️' : '🤍'}</span> <strong class="like-count">${plan.like_count}</strong> Likes
                            </button>
                        </div>
                        <div class="plan-container" style="max-height: 220px; overflow-y: auto; font-size: 0.88rem; background: #fafafa;">${planText}</div>
                    `;
                    feedContainer.appendChild(card);
                });

                document.querySelectorAll('.like-plan-btn').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        e.preventDefault();
                        const token = getAuthToken();
                        if (!token) {
                            alert('Please login to like community plans.');
                            window.location.href = '/login';
                            return;
                        }
                        const pId = btn.getAttribute('data-id');
                        try {
                            const likeRes = await authFetch(`/api/plans/${pId}/like`, { method: 'POST' });
                            if (likeRes.ok) {
                                const data = await likeRes.json();
                                btn.querySelector('.like-count').textContent = data.like_count;
                                btn.querySelector('span').textContent = data.liked ? '❤️' : '🤍';
                            }
                        } catch (err) {
                            console.error('Like error:', err);
                        }
                    });
                });
            }
        }

    } catch (err) {
        console.error('Community page load error:', err);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    updateNavAuthState();

    if (window.location.pathname === '/dashboard') {
        await loadDashboardData();
        const refreshBtn = document.getElementById('refreshPlansBtn');
        if (refreshBtn) refreshBtn.addEventListener('click', () => loadDashboardData());
    }

    if (window.location.pathname === '/community') {
        await loadCommunityPage();
        const refreshCommBtn = document.getElementById('refreshCommunityBtn');
        if (refreshCommBtn) refreshCommBtn.addEventListener('click', () => loadCommunityPage());
    }

    // Stripe Go Pro Button Trigger
    const upgradeProBtn = document.getElementById('upgradeProBtn');
    if (upgradeProBtn) {
        upgradeProBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            upgradeProBtn.disabled = true;
            upgradeProBtn.textContent = 'Redirecting...';
            try {
                const res = await authFetch('/api/billing/create-checkout-session', { method: 'POST' });
                if (res.ok) {
                    const data = await res.json();
                    window.location.href = data.checkout_url;
                } else {
                    alert('Unable to start checkout session.');
                    upgradeProBtn.disabled = false;
                    upgradeProBtn.textContent = '⭐ Go Pro';
                }
            } catch (err) {
                alert('Stripe billing error: ' + err.message);
                upgradeProBtn.disabled = false;
                upgradeProBtn.textContent = '⭐ Go Pro';
            }
        });
    }

    const token = getAuthToken();
    if (token) {
        try {
            const meRes = await authFetch('/api/auth/me');
            if (meRes && meRes.ok) {
                const userData = await meRes.json();
                setAuthSession(token, userData);
                updateNavAuthState();

                const usernameInput = document.getElementById('username');
                const userIdInput = document.getElementById('user_id');
                const ageInput = document.getElementById('age');
                const weightInput = document.getElementById('weight');
                const goalInput = document.getElementById('goal');
                const intensityInput = document.getElementById('intensity');

                if (usernameInput && !usernameInput.value && userData.username) usernameInput.value = userData.username;
                if (userIdInput && !userIdInput.value && (userData.username || userData.user_id)) userIdInput.value = userData.username || userData.user_id;
                if (ageInput && !ageInput.value && userData.age) ageInput.value = userData.age;
                if (weightInput && !weightInput.value && userData.weight) weightInput.value = userData.weight;
                if (goalInput && userData.goal) goalInput.value = userData.goal;
                if (intensityInput && userData.intensity) intensityInput.value = userData.intensity;
            }
        } catch (err) {
            console.warn('Background auth sync skipped:', err);
        }
    }

    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            clearAuthSession();
            updateNavAuthState();
            window.location.href = '/login';
        });
    }

    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorDiv = document.getElementById('login-error');
            const successDiv = document.getElementById('login-success');
            const submitBtn = document.getElementById('loginBtn');

            if (errorDiv) errorDiv.style.display = 'none';
            if (successDiv) successDiv.style.display = 'none';

            const usernameOrEmail = document.getElementById('username_or_email').value.trim();
            const password = document.getElementById('password').value;

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = 'Signing In...';
            }

            try {
                const response = await fetch('/api/auth/login-json', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username_or_email: usernameOrEmail,
                        password: password
                    })
                });

                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.detail || 'Login failed.');
                }

                setAuthSession(data.access_token, data.user);
                updateNavAuthState();

                if (successDiv) {
                    successDiv.textContent = 'Login successful! Redirecting...';
                    successDiv.style.display = 'block';
                }

                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 700);

            } catch (err) {
                if (errorDiv) {
                    errorDiv.textContent = err.message;
                    errorDiv.style.display = 'block';
                }
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = 'Sign In to FitBuddy';
                }
            }
        });
    }

    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorDiv = document.getElementById('register-error');
            const successDiv = document.getElementById('register-success');
            const submitBtn = document.getElementById('registerBtn');

            if (errorDiv) errorDiv.style.display = 'none';
            if (successDiv) successDiv.style.display = 'none';

            const payload = {
                username: document.getElementById('reg_username').value.trim(),
                email: document.getElementById('reg_email').value.trim(),
                password: document.getElementById('reg_password').value,
                age: parseInt(document.getElementById('reg_age').value, 10),
                weight: parseFloat(document.getElementById('reg_weight').value),
                goal: document.getElementById('reg_goal').value,
                intensity: document.getElementById('reg_intensity').value
            };

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = 'Creating Account...';
            }

            try {
                const regRes = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const regData = await regRes.json();
                if (!regRes.ok) {
                    throw new Error(typeof regData.detail === 'string' ? regData.detail : 'Registration failed.');
                }

                const loginRes = await fetch('/api/auth/login-json', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username_or_email: payload.username,
                        password: payload.password
                    })
                });

                if (loginRes.ok) {
                    const loginData = await loginRes.json();
                    setAuthSession(loginData.access_token, loginData.user);
                    updateNavAuthState();
                }

                if (successDiv) {
                    successDiv.textContent = 'Account created successfully! Redirecting...';
                    successDiv.style.display = 'block';
                }

                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 800);

            } catch (err) {
                if (errorDiv) {
                    errorDiv.textContent = err.message;
                    errorDiv.style.display = 'block';
                }
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = 'Create Free FitBuddy Account';
                }
            }
        });
    }
});
