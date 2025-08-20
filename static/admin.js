/**
 * Admin panel JavaScript functionality
 */

// API base URL
const API_BASE = '/api/admin';

// Get auth token
function getAuthToken() {
    return localStorage.getItem('adminToken');
}

// Create authenticated fetch request
async function authenticatedFetch(url, options = {}) {
    const token = getAuthToken();
    if (!token) {
        window.location.href = '/admin/login';
        return;
    }
    
    const authOptions = {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    };
    
    const response = await fetch(url, authOptions);
    
    if (response.status === 401) {
        localStorage.removeItem('adminToken');
        window.location.href = '/admin/login';
        return;
    }
    
    return response;
}

// Show notification
function showNotification(message, type = 'success') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// Show/hide sections
function showSection(sectionName) {
    // Hide all sections
    const sections = ['dashboard', 'licenses', 'create-license', 'active-licenses', 'subscriptions'];
    sections.forEach(section => {
        const element = document.getElementById(`${section}-section`);
        if (element) {
            element.style.display = 'none';
        }
    });
    
    // Show selected section
    const selectedSection = document.getElementById(`${sectionName}-section`);
    if (selectedSection) {
        selectedSection.style.display = 'block';
    }
    
    // Update navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    const activeLink = document.querySelector(`a[href="#${sectionName}"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }
    
    // Load section-specific data
    if (sectionName === 'dashboard') {
        loadDashboard();
    } else if (sectionName === 'licenses') {
        loadLicenses();
    } else if (sectionName === 'active-licenses') {
        loadActiveLicenses();
    } else if (sectionName === 'subscriptions') {
        loadSubscriptions();
    }
}

// Load dashboard data
async function loadDashboard() {
    try {
        const response = await authenticatedFetch(`${API_BASE}/dashboard`);
        if (!response) return;
        
        const stats = await response.json();
        displayStats(stats);
    } catch (error) {
        showNotification('Failed to load dashboard stats', 'danger');
        console.error('Error loading dashboard:', error);
    }
}

// Display dashboard stats
function displayStats(stats) {
    const container = document.getElementById('stats-container');
    if (!container) return;
    
    container.innerHTML = `
        <div class="col-md-3">
            <div class="stat-card">
                <h3>${stats.total_users}</h3>
                <p><i class="fas fa-users"></i> Total Users</p>
            </div>
        </div>
        <div class="col-md-3">
            <div class="stat-card success">
                <h3>${stats.active_licenses}</h3>
                <p><i class="fas fa-key"></i> Active Licenses</p>
            </div>
        </div>
        <div class="col-md-3">
            <div class="stat-card warning">
                <h3>${stats.active_subscriptions}</h3>
                <p><i class="fas fa-credit-card"></i> Active Subscriptions</p>
            </div>
        </div>
        <div class="col-md-3">
            <div class="stat-card info">
                <h3>$${stats.monthly_revenue.toFixed(2)}</h3>
                <p><i class="fas fa-dollar-sign"></i> Monthly Revenue</p>
            </div>
        </div>
    `;
}

// Load active licenses
async function loadActiveLicenses() {
    try {
        const response = await authenticatedFetch(`${API_BASE}/active-licenses`);
        if (!response) return;
        
        const data = await response.json();
        displayActiveLicenses(data);
    } catch (error) {
        showNotification('Failed to load active licenses', 'danger');
        console.error('Error loading active licenses:', error);
    }
}

// Display active licenses
function displayActiveLicenses(data) {
    // Update active count
    const activeCountElement = document.getElementById('active-count');
    if (activeCountElement) {
        activeCountElement.textContent = data.total_active;
    }
    
    // Update last updated time
    const lastUpdatedElement = document.getElementById('last-updated');
    if (lastUpdatedElement) {
        const updateTime = new Date(data.last_updated);
        lastUpdatedElement.textContent = updateTime.toLocaleString();
    }
    
    // Update table
    const tbody = document.getElementById('active-licenses-tbody');
    if (!tbody) return;
    
    if (data.licenses.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">No active licenses found</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.licenses.map(license => `
        <tr>
            <td>${license.user_email}</td>
            <td><code class="license-key">${license.license_key}</code></td>
            <td>
                ${formatDate(license.last_validated)}
                <br><small class="text-muted">${getTimeAgo(license.last_validated)}</small>
            </td>
            <td>
                <span class="badge bg-primary">${license.validation_count}</span>
            </td>
            <td>
                ${license.extension_version || 'Unknown'}
            </td>
            <td>
                <small>${license.device_fingerprint ? license.device_fingerprint.substring(0, 10) + '...' : 'N/A'}</small>
            </td>
            <td>
                <small>${license.last_ip || 'Unknown'}</small>
            </td>
            <td>
                <span class="badge bg-success">${license.subscription_status}</span>
                <br><small class="text-muted">Expires: ${formatDate(license.subscription_expires)}</small>
            </td>
        </tr>
    `).join('');
}

// Get time ago helper
function getTimeAgo(dateString) {
    const now = new Date();
    const date = new Date(dateString);
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
}

// Load licenses
async function loadLicenses() {
    try {
        const response = await authenticatedFetch(`${API_BASE}/licenses`);
        if (!response) return;
        
        const licenses = await response.json();
        displayLicenses(licenses);
    } catch (error) {
        showNotification('Failed to load licenses', 'danger');
        console.error('Error loading licenses:', error);
    }
}

// Display licenses table
function displayLicenses(licenses) {
    const tbody = document.getElementById('licenses-tbody');
    if (!tbody) return;
    
    if (licenses.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">No licenses found</td></tr>';
        return;
    }
    
    tbody.innerHTML = licenses.map(license => `
        <tr>
            <td>${license.id}</td>
            <td><code class="license-key">${license.license_key}</code></td>
            <td>${license.user_email}</td>
            <td>
                <span class="badge ${getStatusBadgeClass(license)} status-badge">
                    ${getStatusText(license)}
                </span>
            </td>
            <td>${formatDate(license.created_at)}</td>
            <td>${license.last_validated ? formatDate(license.last_validated) : 'Never'}</td>
            <td>
                ${license.subscription_status ? 
                    `<span class="badge bg-info">${license.subscription_status}</span>` : 
                    '<span class="badge bg-secondary">None</span>'
                }
            </td>
            <td>
                ${generateActionButtons(license)}
            </td>
        </tr>
    `).join('');
}

// Get status badge class
function getStatusBadgeClass(license) {
    if (!license.is_active) return 'bg-danger';
    if (license.is_suspended) return 'bg-warning';
    return 'bg-success';
}

// Get status text
function getStatusText(license) {
    if (!license.is_active) return 'Inactive';
    if (license.is_suspended) return 'Suspended';
    return 'Active';
}

// Generate action buttons
function generateActionButtons(license) {
    const buttons = [];
    
    if (license.is_suspended) {
        buttons.push(`
            <button class="btn btn-sm btn-success me-1" 
                    onclick="activateLicense(${license.id})" 
                    title="Activate License">
                <i class="fas fa-play"></i>
            </button>
        `);
    } else if (license.is_active) {
        buttons.push(`
            <button class="btn btn-sm btn-warning me-1" 
                    onclick="suspendLicense(${license.id})" 
                    title="Suspend License">
                <i class="fas fa-pause"></i>
            </button>
        `);
    }
    
    buttons.push(`
        <button class="btn btn-sm btn-info me-1" 
                onclick="rotateLicenseKey(${license.id})" 
                title="Rotate License Key">
            <i class="fas fa-sync"></i>
        </button>
    `);
    
    return buttons.join('');
}

// Format date
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Format date for display (shorter format)
function formatDisplayDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

// Get expiration status badge class
function getExpirationStatusBadge(expirationStatus, daysUntilExpiry) {
    if (expirationStatus === 'expired') {
        return '<span class="badge bg-danger">EXPIRED</span>';
    } else if (expirationStatus === 'expires_soon') {
        return '<span class="badge bg-warning">EXPIRES SOON</span>';
    } else if (expirationStatus === 'active') {
        return '<span class="badge bg-success">ACTIVE</span>';
    } else {
        return '<span class="badge bg-secondary">UNKNOWN</span>';
    }
}

// Format days until expiry display
function formatDaysUntilExpiry(daysUntilExpiry) {
    if (daysUntilExpiry === null || daysUntilExpiry === undefined) {
        return 'N/A';
    }
    
    if (daysUntilExpiry < 0) {
        return `<span class="text-danger">EXPIRED ${Math.abs(daysUntilExpiry)} days ago</span>`;
    } else if (daysUntilExpiry === 0) {
        return '<span class="text-warning">EXPIRES TODAY</span>';
    } else if (daysUntilExpiry <= 7) {
        return `<span class="text-warning">${daysUntilExpiry} days</span>`;
    } else {
        return `<span class="text-success">${daysUntilExpiry} days</span>`;
    }
}

// Format trial status
function formatTrialStatus(isTrial, trialEnd) {
    if (isTrial) {
        if (trialEnd) {
            const trialEndDate = new Date(trialEnd);
            const now = new Date();
            const daysLeft = Math.ceil((trialEndDate - now) / (1000 * 60 * 60 * 24));
            
            if (daysLeft > 0) {
                return `<span class="badge bg-info">TRIAL (${daysLeft}d left)</span>`;
            } else {
                return '<span class="badge bg-warning">TRIAL ENDED</span>';
            }
        } else {
            return '<span class="badge bg-info">TRIAL</span>';
        }
    } else {
        return '<span class="badge bg-light text-dark">NO</span>';
    }
}

// Format billing cycle
function formatBillingCycle(billingCycle) {
    if (!billingCycle) return 'monthly';
    return billingCycle.charAt(0).toUpperCase() + billingCycle.slice(1);
}

// Suspend license
async function suspendLicense(licenseId) {
    if (!confirm('Are you sure you want to suspend this license?')) return;
    
    try {
        const response = await authenticatedFetch(`${API_BASE}/licenses/${licenseId}/suspend`, {
            method: 'POST'
        });
        
        if (!response) return;
        
        const result = await response.json();
        if (result.success) {
            showNotification('License suspended successfully');
            loadLicenses();
        } else {
            showNotification('Failed to suspend license', 'danger');
        }
    } catch (error) {
        showNotification('Failed to suspend license', 'danger');
        console.error('Error suspending license:', error);
    }
}

// Activate license
async function activateLicense(licenseId) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/licenses/${licenseId}/activate`, {
            method: 'POST'
        });
        
        if (!response) return;
        
        const result = await response.json();
        if (result.success) {
            showNotification('License activated successfully');
            loadLicenses();
        } else {
            showNotification('Failed to activate license', 'danger');
        }
    } catch (error) {
        showNotification('Failed to activate license', 'danger');
        console.error('Error activating license:', error);
    }
}

// Rotate license key
async function rotateLicenseKey(licenseId) {
    if (!confirm('Are you sure you want to rotate this license key? The old key will become invalid.')) return;
    
    try {
        const response = await authenticatedFetch(`${API_BASE}/licenses/${licenseId}/rotate`, {
            method: 'POST'
        });
        
        if (!response) return;
        
        const result = await response.json();
        if (result.success) {
            showNotification('License key rotated successfully');
            
            // Show new license key in modal
            document.getElementById('generated-license-key').textContent = result.new_license_key;
            const modal = new bootstrap.Modal(document.getElementById('licenseKeyModal'));
            modal.show();
            
            loadLicenses();
        } else {
            showNotification('Failed to rotate license key', 'danger');
        }
    } catch (error) {
        showNotification('Failed to rotate license key', 'danger');
        console.error('Error rotating license key:', error);
    }
}

// Create license form handler
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('create-license-form');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = document.getElementById('user-email').value;
            const submitButton = e.target.querySelector('button[type="submit"]');
            
            // Show loading state
            const originalText = submitButton.innerHTML;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
            submitButton.disabled = true;
            
            try {
                const formData = new FormData();
                formData.append('email', email);
                
                const response = await fetch(`${API_BASE}/licenses`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${getAuthToken()}`
                    },
                    body: formData
                });
                
                if (!response) return;
                
                const result = await response.json();
                if (result.success) {
                    showNotification(`License created for ${email}`);
                    
                    // Show license key in modal
                    document.getElementById('generated-license-key').textContent = result.license_key;
                    const modal = new bootstrap.Modal(document.getElementById('licenseKeyModal'));
                    modal.show();
                    
                    // Reset form
                    form.reset();
                } else {
                    showNotification('Failed to create license', 'danger');
                }
            } catch (error) {
                showNotification('Failed to create license', 'danger');
                console.error('Error creating license:', error);
            } finally {
                // Reset button
                submitButton.innerHTML = originalText;
                submitButton.disabled = false;
            }
        });
    }
});

// Copy license key to clipboard
function copyLicenseKey() {
    const licenseKeyElement = document.getElementById('generated-license-key');
    if (!licenseKeyElement) return;
    
    navigator.clipboard.writeText(licenseKeyElement.textContent).then(function() {
        showNotification('License key copied to clipboard');
    }, function() {
        showNotification('Failed to copy license key', 'warning');
    });
}

// Refresh dashboard
function refreshDashboard() {
    loadDashboard();
    showNotification('Dashboard refreshed');
}

// Logout
function logout() {
    if (confirm('Are you sure you want to logout?')) {
        localStorage.removeItem('adminToken');
        window.location.href = '/admin/login';
    }
}

// Load subscriptions
async function loadSubscriptions() {
    try {
        const response = await authenticatedFetch(`${API_BASE}/subscriptions`);
        if (!response) return;
        
        const subscriptions = await response.json();
        displaySubscriptions(subscriptions);
        
        // Attach event listener to subscription form after section is loaded
        attachSubscriptionFormListener();
    } catch (error) {
        showNotification('Failed to load subscriptions', 'danger');
        console.error('Error loading subscriptions:', error);
    }
}

// Attach event listener to subscription form
function attachSubscriptionFormListener() {
    const subscriptionForm = document.getElementById('create-subscription-form');
    if (subscriptionForm) {
        // Remove existing event listener to prevent duplicates
        subscriptionForm.removeEventListener('submit', handleSubscriptionFormSubmit);
        // Add new event listener
        subscriptionForm.addEventListener('submit', handleSubscriptionFormSubmit);
    }
}

// Display subscriptions table
function displaySubscriptions(subscriptions) {
    const tbody = document.getElementById('subscriptions-tbody');
    if (!tbody) return;
    
    if (subscriptions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="11" class="text-center">No subscriptions found</td></tr>';
        return;
    }
    
    tbody.innerHTML = subscriptions.map(subscription => `
        <tr>
            <td>${subscription.id}</td>
            <td>${subscription.user_email}</td>
            <td><span class="badge bg-primary">${subscription.plan_name}</span></td>
            <td>${formatBillingCycle(subscription.billing_cycle)}</td>
            <td>
                <span class="badge ${getSubscriptionStatusBadgeClass(subscription.status)}">
                    ${subscription.status}
                </span>
            </td>
            <td>
                ${formatDisplayDate(subscription.current_period_end)}
                <br><small class="text-muted">${getExpirationStatusBadge(subscription.expiration_status, subscription.days_until_expiry)}</small>
            </td>
            <td>
                ${subscription.end_time ? formatDisplayDate(subscription.end_time) : '<span class="text-muted">Not Set</span>'}
            </td>
            <td>
                ${formatDaysUntilExpiry(subscription.days_until_expiry)}
            </td>
            <td>
                ${formatTrialStatus(subscription.is_trial, subscription.trial_end)}
            </td>
            <td>${formatDate(subscription.created_at)}</td>
            <td>
                <button class="btn btn-sm btn-info me-1" 
                        onclick="editSubscription(${subscription.id})" 
                        title="Edit Subscription">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger" 
                        onclick="deleteSubscription(${subscription.id})" 
                        title="Delete Subscription">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// Get subscription status badge class
function getSubscriptionStatusBadgeClass(status) {
    switch (status.toLowerCase()) {
        case 'active': return 'bg-success';
        case 'expired': return 'bg-danger';
        case 'cancelled': return 'bg-secondary';
        case 'pending': return 'bg-warning';
        default: return 'bg-secondary';
    }
}

// Handle subscription form submission (using event delegation)
function handleSubscriptionFormSubmit(e) {
    e.preventDefault();
    
    // Check if all required form elements exist
    const emailField = document.getElementById('subscription-email');
    const planField = document.getElementById('plan-name');
    const amountField = document.getElementById('amount');
    const statusField = document.getElementById('status');
    
    if (!emailField || !planField || !amountField || !statusField) {
        showNotification('Form fields not found. Please try again.', 'danger');
        return;
    }
    
    const formData = {
        user_email: emailField.value,
        plan_name: planField.value,
        amount: parseFloat(amountField.value),
        status: statusField.value
    };
    
    const submitButton = e.target.querySelector('button[type="submit"]');
    
    // Show loading state
    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
    submitButton.disabled = true;
    
    // Create subscription
    createSubscription(formData, submitButton, originalText);
}

// Create subscription function
async function createSubscription(formData, submitButton, originalText) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/subscriptions`, {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        
        if (!response) return;
        
        const result = await response.json();
        if (result.success) {
            showNotification(`Subscription created for ${formData.user_email}`);
            const form = document.getElementById('create-subscription-form');
            if (form) form.reset();
            loadSubscriptions();
        } else {
            showNotification(result.error || 'Failed to create subscription', 'danger');
        }
    } catch (error) {
        showNotification('Failed to create subscription', 'danger');
        console.error('Error creating subscription:', error);
    } finally {
        // Reset button
        if (submitButton) {
            submitButton.innerHTML = originalText;
            submitButton.disabled = false;
        }
    }
}

// Edit subscription
async function editSubscription(subscriptionId) {
    // Get current subscription data
    try {
        const response = await authenticatedFetch(`${API_BASE}/subscriptions/${subscriptionId}`);
        if (!response) return;
        
        const subscription = await response.json();
        
        // Show edit modal with current data
        showEditSubscriptionModal(subscription);
        
    } catch (error) {
        showNotification('Failed to load subscription details', 'danger');
        console.error('Error loading subscription:', error);
    }
}

// Show edit subscription modal
function showEditSubscriptionModal(subscription) {
    // Create modal HTML if it doesn't exist
    let modal = document.getElementById('editSubscriptionModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.innerHTML = `
            <div class="modal fade" id="editSubscriptionModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Edit Subscription</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="edit-subscription-form">
                                <input type="hidden" id="edit-subscription-id">
                                <div class="mb-3">
                                    <label for="edit-subscription-email" class="form-label">User Email</label>
                                    <input type="email" class="form-control" id="edit-subscription-email" required>
                                </div>
                                <div class="mb-3">
                                    <label for="edit-plan-name" class="form-label">Plan Name</label>
                                    <select class="form-select" id="edit-plan-name" required>
                                        <option value="basic">Basic Plan</option>
                                        <option value="premium">Premium Plan</option>
                                        <option value="enterprise">Enterprise Plan</option>
                                    </select>
                                </div>
                                <div class="mb-3">
                                    <label for="edit-amount" class="form-label">Amount ($)</label>
                                    <input type="number" class="form-control" id="edit-amount" step="0.01" required>
                                </div>
                                <div class="mb-3">
                                    <label for="edit-status" class="form-label">Status</label>
                                    <select class="form-select" id="edit-status" required>
                                        <option value="active">Active</option>
                                        <option value="trialing">Trialing</option>
                                        <option value="past_due">Past Due</option>
                                        <option value="canceled">Canceled</option>
                                        <option value="unpaid">Unpaid</option>
                                        <option value="ended">Ended</option>
                                    </select>
                                </div>
                                <div class="mb-3">
                                    <label for="edit-period-end" class="form-label">Period End Date</label>
                                    <input type="datetime-local" class="form-control" id="edit-period-end">
                                    <div class="form-text">Set when the subscription period ends (expiration date)</div>
                                </div>
                                <div class="mb-3">
                                    <label for="edit-trial-end" class="form-label">Trial End Date (Optional)</label>
                                    <input type="datetime-local" class="form-control" id="edit-trial-end">
                                    <div class="form-text">Set trial expiration date if applicable</div>
                                </div>
                                <div class="mb-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="edit-cancel-at-period-end">
                                        <label class="form-check-label" for="edit-cancel-at-period-end">
                                            Cancel at period end
                                        </label>
                                    </div>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" onclick="updateSubscription()">Update Subscription</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    // Populate form with current subscription data
    document.getElementById('edit-subscription-id').value = subscription.id;
    document.getElementById('edit-subscription-email').value = subscription.user_email;
    document.getElementById('edit-plan-name').value = subscription.plan_name;
    document.getElementById('edit-amount').value = subscription.amount;
    document.getElementById('edit-status').value = subscription.status;
    
    // Format and populate date fields
    if (subscription.current_period_end) {
        const periodEndDate = new Date(subscription.current_period_end);
        document.getElementById('edit-period-end').value = periodEndDate.toISOString().slice(0, 16);
    }
    
    if (subscription.trial_end) {
        const trialEndDate = new Date(subscription.trial_end);
        document.getElementById('edit-trial-end').value = trialEndDate.toISOString().slice(0, 16);
    }
    
    // Set cancel at period end checkbox
    document.getElementById('edit-cancel-at-period-end').checked = subscription.cancel_at_period_end || false;
    
    // Show modal
    const bootstrapModal = new bootstrap.Modal(modal.querySelector('.modal'));
    bootstrapModal.show();
}

// Update subscription
async function updateSubscription() {
    const subscriptionId = document.getElementById('edit-subscription-id').value;
    
    // Get date values and convert to ISO strings if they exist
    const periodEndValue = document.getElementById('edit-period-end').value;
    const trialEndValue = document.getElementById('edit-trial-end').value;
    
    const formData = {
        user_email: document.getElementById('edit-subscription-email').value,
        plan_name: document.getElementById('edit-plan-name').value,
        amount: parseFloat(document.getElementById('edit-amount').value),
        status: document.getElementById('edit-status').value,
        current_period_end: periodEndValue ? new Date(periodEndValue).toISOString() : null,
        trial_end: trialEndValue ? new Date(trialEndValue).toISOString() : null,
        cancel_at_period_end: document.getElementById('edit-cancel-at-period-end').checked
    };
    
    try {
        const response = await authenticatedFetch(`${API_BASE}/subscriptions/${subscriptionId}`, {
            method: 'PUT',
            body: JSON.stringify(formData)
        });
        
        if (!response) return;
        
        const result = await response.json();
        if (result.success) {
            showNotification('Subscription updated successfully');
            
            // Hide modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('editSubscriptionModal'));
            modal.hide();
            
            loadSubscriptions();
        } else {
            showNotification(result.error || 'Failed to update subscription', 'danger');
        }
    } catch (error) {
        showNotification('Failed to update subscription', 'danger');
        console.error('Error updating subscription:', error);
    }
}

// Delete subscription
async function deleteSubscription(subscriptionId) {
    if (!confirm('Are you sure you want to delete this subscription? This action cannot be undone.')) return;
    
    try {
        const response = await authenticatedFetch(`${API_BASE}/subscriptions/${subscriptionId}`, {
            method: 'DELETE'
        });
        
        if (!response) return;
        
        const result = await response.json();
        if (result.success) {
            showNotification('Subscription deleted successfully');
            loadSubscriptions();
        } else {
            showNotification('Failed to delete subscription', 'danger');
        }
    } catch (error) {
        showNotification('Failed to delete subscription', 'danger');
        console.error('Error deleting subscription:', error);
    }
}

// Auto-refresh dashboard every 5 minutes
setInterval(function() {
    if (document.getElementById('dashboard-section').style.display !== 'none') {
        loadDashboard();
    }
}, 300000);
