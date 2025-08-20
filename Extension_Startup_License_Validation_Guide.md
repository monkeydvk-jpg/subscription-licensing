# Extension Startup License Validation Guide

This guide shows how to implement license key storage and validation when your browser extension loads.

## Overview

When a browser extension starts up, it needs to:
1. Check if a license key is stored
2. If found, validate it with the API
3. Handle the validation result appropriately
4. Enable/disable extension features based on license status

## Implementation Examples

### Chrome Extension (Manifest V3)

#### Background Service Worker (`background.js`)

```javascript
// License management service
class LicenseManager {
    constructor() {
        this.apiBaseUrl = 'https://your-license-api.com/api';
        this.licenseKey = null;
        this.isValid = false;
        this.validationCache = null;
        this.cacheExpiration = null;
    }

    // Initialize license validation on extension startup
    async initialize() {
        console.log('🔄 Initializing license validation...');
        
        try {
            // Get stored license key
            const storedKey = await this.getStoredLicenseKey();
            
            if (!storedKey) {
                console.log('❌ No license key found');
                await this.handleNoLicense();
                return false;
            }

            // Check if we have valid cached validation
            if (await this.hasCachedValidation()) {
                console.log('✅ Using cached validation');
                this.licenseKey = storedKey;
                this.isValid = true;
                await this.enableExtension();
                return true;
            }

            // Validate license with API
            const validationResult = await this.validateLicense(storedKey);
            return await this.handleValidationResult(validationResult, storedKey);

        } catch (error) {
            console.error('❌ License initialization failed:', error);
            await this.handleValidationError(error);
            return false;
        }
    }

    // Get license key from Chrome storage
    async getStoredLicenseKey() {
        try {
            const result = await chrome.storage.sync.get(['licenseKey']);
            return result.licenseKey || null;
        } catch (error) {
            console.error('Error reading license key from storage:', error);
            return null;
        }
    }

    // Store license key in Chrome storage
    async storeLicenseKey(key) {
        try {
            await chrome.storage.sync.set({ licenseKey: key });
            console.log('✅ License key stored');
        } catch (error) {
            console.error('Error storing license key:', error);
            throw error;
        }
    }

    // Remove license key from storage
    async removeLicenseKey() {
        try {
            await chrome.storage.sync.remove(['licenseKey']);
            await chrome.storage.local.remove(['licenseValidation', 'validationExpiry']);
            console.log('🗑️ License key removed');
        } catch (error) {
            console.error('Error removing license key:', error);
        }
    }

    // Check if we have valid cached validation (to avoid API calls on every startup)
    async hasCachedValidation() {
        try {
            const result = await chrome.storage.local.get(['licenseValidation', 'validationExpiry']);
            
            if (!result.licenseValidation || !result.validationExpiry) {
                return false;
            }

            const now = new Date().getTime();
            if (now > result.validationExpiry) {
                // Cache expired
                await chrome.storage.local.remove(['licenseValidation', 'validationExpiry']);
                return false;
            }

            this.validationCache = result.licenseValidation;
            return result.licenseValidation.valid === true;
        } catch (error) {
            console.error('Error checking cached validation:', error);
            return false;
        }
    }

    // Cache validation result (valid for 1 hour to reduce API calls)
    async cacheValidation(validationResult) {
        try {
            const expiry = new Date().getTime() + (60 * 60 * 1000); // 1 hour
            await chrome.storage.local.set({
                licenseValidation: validationResult,
                validationExpiry: expiry
            });
        } catch (error) {
            console.error('Error caching validation:', error);
        }
    }

    // Validate license key with API
    async validateLicense(licenseKey) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

        try {
            console.log('🔍 Validating license with API...');
            
            const response = await fetch(`${this.apiBaseUrl}/validate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    license_key: licenseKey,
                    extension_version: chrome.runtime.getManifest().version,
                    device_fingerprint: await this.generateDeviceFingerprint()
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('📄 Validation result:', result);
            
            return result;

        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                throw new Error('License validation timeout');
            }
            throw error;
        }
    }

    // Handle validation result based on error codes
    async handleValidationResult(result, licenseKey) {
        // Cache the result
        await this.cacheValidation(result);

        if (result.valid) {
            console.log('✅ License is valid');
            this.licenseKey = licenseKey;
            this.isValid = true;
            await this.enableExtension();
            return true;
        }

        // Handle specific error cases using error_code
        switch (result.error_code) {
            case 'SUSPENDED':
                await this.handleSuspendedLicense(result);
                break;
            
            case 'INVALID_KEY':
                await this.handleInvalidKey(result);
                break;
            
            case 'INACTIVE':
                await this.handleInactiveLicense(result);
                break;
            
            case 'NO_SUBSCRIPTION':
                await this.handleNoSubscription(result);
                break;
            
            case 'SUBSCRIPTION_INACTIVE':
                await this.handleInactiveSubscription(result);
                break;
            
            default:
                await this.handleGenericError(result);
        }

        return false;
    }

    // Handle suspended license
    async handleSuspendedLicense(result) {
        console.log('⚠️ License is suspended');
        this.isValid = false;
        await this.disableExtension();
        await this.showNotification({
            type: 'error',
            title: 'License Suspended',
            message: 'Your license has been suspended. Please contact support.',
            persistent: true,
            buttons: [
                { title: 'Contact Support', action: 'openSupport' }
            ]
        });
    }

    // Handle invalid license key
    async handleInvalidKey(result) {
        console.log('❌ Invalid license key');
        this.isValid = false;
        await this.removeLicenseKey();
        await this.disableExtension();
        await this.showLicensePrompt('The license key is invalid. Please enter a valid license key.');
    }

    // Handle inactive license
    async handleInactiveLicense(result) {
        console.log('💤 License is inactive');
        this.isValid = false;
        await this.disableExtension();
        await this.showNotification({
            type: 'warning',
            title: 'License Inactive',
            message: 'Your license is inactive. Please contact support to reactivate.',
            buttons: [
                { title: 'Contact Support', action: 'openSupport' }
            ]
        });
    }

    // Handle no subscription
    async handleNoSubscription(result) {
        console.log('💳 No subscription found');
        this.isValid = false;
        await this.disableExtension();
        await this.showNotification({
            type: 'info',
            title: 'Subscription Required',
            message: 'An active subscription is required to use this extension.',
            buttons: [
                { title: 'Subscribe Now', action: 'openSubscription' }
            ]
        });
    }

    // Handle inactive subscription
    async handleInactiveSubscription(result) {
        console.log('📅 Subscription is inactive:', result.subscription_status);
        this.isValid = false;
        await this.disableExtension();
        
        let message = 'Your subscription is inactive.';
        let action = 'openSubscription';
        
        switch (result.subscription_status) {
            case 'canceled':
                message = 'Your subscription has been canceled. Renew to continue using premium features.';
                break;
            case 'past_due':
                message = 'Your subscription payment is past due. Please update your payment method.';
                action = 'openPayment';
                break;
            case 'unpaid':
                message = 'Your subscription has unpaid invoices. Please resolve payment issues.';
                action = 'openBilling';
                break;
        }

        await this.showNotification({
            type: 'warning',
            title: 'Subscription Issue',
            message,
            buttons: [
                { title: 'Fix Now', action }
            ]
        });
    }

    // Handle generic errors
    async handleGenericError(result) {
        console.log('❓ Generic license error:', result.message);
        this.isValid = false;
        await this.disableExtension();
        await this.showNotification({
            type: 'error',
            title: 'License Error',
            message: result.message || 'An error occurred while validating your license.'
        });
    }

    // Handle validation network/API errors
    async handleValidationError(error) {
        console.log('🌐 Validation error:', error.message);
        
        // For network errors, we might want to allow graceful degradation
        // depending on your business requirements
        const storedKey = await this.getStoredLicenseKey();
        
        if (storedKey && await this.hasCachedValidation()) {
            // Use cached validation if available
            console.log('📱 Using cached validation due to network error');
            this.licenseKey = storedKey;
            this.isValid = true;
            await this.enableExtension();
            return;
        }

        // No cached validation available
        this.isValid = false;
        await this.disableExtension();
        await this.showNotification({
            type: 'warning',
            title: 'Connection Error',
            message: 'Unable to verify license. Please check your internet connection.',
            buttons: [
                { title: 'Retry', action: 'retryValidation' }
            ]
        });
    }

    // Handle case when no license key is stored
    async handleNoLicense() {
        console.log('🔑 No license key found');
        this.isValid = false;
        await this.disableExtension();
        await this.showLicensePrompt('Please enter your license key to activate the extension.');
    }

    // Enable extension functionality
    async enableExtension() {
        console.log('✅ Extension enabled');
        // Enable context menus, content scripts, etc.
        await this.updateExtensionState(true);
        
        // Send message to all tabs that extension is enabled
        await this.broadcastMessage('extensionEnabled', {
            licenseKey: this.maskLicenseKey(this.licenseKey),
            validUntil: this.validationCache?.expires_at
        });
    }

    // Disable extension functionality
    async disableExtension() {
        console.log('❌ Extension disabled');
        // Disable context menus, content scripts, etc.
        await this.updateExtensionState(false);
        
        // Send message to all tabs that extension is disabled
        await this.broadcastMessage('extensionDisabled', {});
    }

    // Update extension UI state
    async updateExtensionState(enabled) {
        // Update badge
        await chrome.action.setBadgeText({
            text: enabled ? '' : '!'
        });
        
        await chrome.action.setBadgeBackgroundColor({
            color: enabled ? '#4CAF50' : '#F44336'
        });

        // Update popup icon
        await chrome.action.setIcon({
            path: enabled ? 'icons/icon-active.png' : 'icons/icon-inactive.png'
        });
    }

    // Show notification to user
    async showNotification(options) {
        // Show browser notification
        await chrome.notifications.create(`license-${Date.now()}`, {
            type: 'basic',
            iconUrl: 'icons/icon-48.png',
            title: options.title,
            message: options.message
        });

        // Also store notification for popup to show
        await chrome.storage.local.set({
            lastNotification: options
        });
    }

    // Show license key input prompt
    async showLicensePrompt(message) {
        await chrome.storage.local.set({
            showLicensePrompt: true,
            licensePromptMessage: message
        });

        // Open popup or options page
        await chrome.action.openPopup();
    }

    // Broadcast message to all extension contexts
    async broadcastMessage(action, data) {
        try {
            // Send to all tabs
            const tabs = await chrome.tabs.query({});
            tabs.forEach(tab => {
                chrome.tabs.sendMessage(tab.id, { action, data }).catch(() => {
                    // Ignore errors for tabs without content scripts
                });
            });

            // Send to popup if open
            chrome.runtime.sendMessage({ action, data }).catch(() => {
                // Ignore if popup is not open
            });
        } catch (error) {
            console.error('Error broadcasting message:', error);
        }
    }

    // Generate device fingerprint for API
    async generateDeviceFingerprint() {
        // Simple fingerprint based on extension ID and user agent
        const manifest = chrome.runtime.getManifest();
        const extensionId = chrome.runtime.id;
        const userAgent = navigator.userAgent;
        
        // Create a simple hash
        const fingerprint = btoa(extensionId + userAgent + manifest.version).slice(0, 32);
        return fingerprint;
    }

    // Mask license key for logging/display
    maskLicenseKey(key) {
        if (!key || key.length < 8) return '****';
        return key.slice(0, 4) + '****' + key.slice(-4);
    }

    // Public method to manually validate license (e.g., from popup)
    async revalidateLicense() {
        const storedKey = await this.getStoredLicenseKey();
        if (!storedKey) {
            await this.handleNoLicense();
            return false;
        }

        try {
            const result = await this.validateLicense(storedKey);
            return await this.handleValidationResult(result, storedKey);
        } catch (error) {
            await this.handleValidationError(error);
            return false;
        }
    }

    // Public method to set new license key
    async setLicenseKey(key) {
        if (!key || typeof key !== 'string') {
            throw new Error('Invalid license key');
        }

        try {
            const result = await this.validateLicense(key);
            const isValid = await this.handleValidationResult(result, key);
            
            if (isValid) {
                await this.storeLicenseKey(key);
            }
            
            return isValid;
        } catch (error) {
            throw new Error(`License validation failed: ${error.message}`);
        }
    }
}

// Initialize license manager
const licenseManager = new LicenseManager();

// Extension startup
chrome.runtime.onStartup.addListener(async () => {
    console.log('🚀 Extension starting up...');
    await licenseManager.initialize();
});

chrome.runtime.onInstalled.addListener(async (details) => {
    console.log('📦 Extension installed/updated:', details.reason);
    await licenseManager.initialize();
});

// Handle messages from popup/content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'getLicenseStatus') {
        sendResponse({
            isValid: licenseManager.isValid,
            licenseKey: licenseManager.maskLicenseKey(licenseManager.licenseKey)
        });
    } else if (message.action === 'setLicenseKey') {
        licenseManager.setLicenseKey(message.key)
            .then(isValid => sendResponse({ success: true, valid: isValid }))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true; // Async response
    } else if (message.action === 'revalidateLicense') {
        licenseManager.revalidateLicense()
            .then(isValid => sendResponse({ success: true, valid: isValid }))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true; // Async response
    } else if (message.action === 'removeLicense') {
        licenseManager.removeLicenseKey()
            .then(() => {
                licenseManager.isValid = false;
                licenseManager.licenseKey = null;
                licenseManager.handleNoLicense();
                sendResponse({ success: true });
            })
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true; // Async response
    }
});

// Handle notification button clicks
chrome.notifications.onButtonClicked.addListener((notificationId, buttonIndex) => {
    // Handle notification actions
    console.log('Notification button clicked:', notificationId, buttonIndex);
});

// Export for popup/options page
self.licenseManager = licenseManager;
```

#### Popup JavaScript (`popup.js`)

```javascript
class PopupManager {
    constructor() {
        this.licenseManager = chrome.extension.getBackgroundPage().licenseManager;
    }

    async init() {
        await this.updateUI();
        this.attachEventListeners();
    }

    async updateUI() {
        const status = await this.getLicenseStatus();
        
        const statusElement = document.getElementById('license-status');
        const keyElement = document.getElementById('current-key');
        const inputSection = document.getElementById('input-section');
        const actionButtons = document.getElementById('action-buttons');

        if (status.isValid) {
            statusElement.textContent = 'Active';
            statusElement.className = 'status active';
            keyElement.textContent = status.licenseKey || 'No key';
            inputSection.style.display = 'none';
            actionButtons.innerHTML = `
                <button id="revalidate-btn" class="btn btn-secondary">Revalidate</button>
                <button id="remove-btn" class="btn btn-danger">Remove License</button>
            `;
        } else {
            statusElement.textContent = 'Inactive';
            statusElement.className = 'status inactive';
            keyElement.textContent = 'No valid license';
            inputSection.style.display = 'block';
            actionButtons.innerHTML = `
                <button id="activate-btn" class="btn btn-primary">Activate License</button>
            `;
        }

        this.attachActionListeners();
    }

    attachEventListeners() {
        const licenseInput = document.getElementById('license-input');
        
        licenseInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.activateLicense();
            }
        });
    }

    attachActionListeners() {
        document.getElementById('activate-btn')?.addEventListener('click', () => {
            this.activateLicense();
        });

        document.getElementById('revalidate-btn')?.addEventListener('click', () => {
            this.revalidateLicense();
        });

        document.getElementById('remove-btn')?.addEventListener('click', () => {
            this.removeLicense();
        });
    }

    async getLicenseStatus() {
        return new Promise((resolve) => {
            chrome.runtime.sendMessage({ action: 'getLicenseStatus' }, resolve);
        });
    }

    async activateLicense() {
        const input = document.getElementById('license-input');
        const key = input.value.trim();

        if (!key) {
            this.showMessage('Please enter a license key', 'error');
            return;
        }

        this.showLoading(true);
        
        try {
            const result = await new Promise((resolve) => {
                chrome.runtime.sendMessage({ action: 'setLicenseKey', key }, resolve);
            });

            if (result.success && result.valid) {
                this.showMessage('License activated successfully!', 'success');
                input.value = '';
                setTimeout(() => this.updateUI(), 1000);
            } else if (result.success && !result.valid) {
                this.showMessage('License key is invalid or inactive', 'error');
            } else {
                this.showMessage(result.error || 'Failed to activate license', 'error');
            }
        } catch (error) {
            this.showMessage('Error activating license: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async revalidateLicense() {
        this.showLoading(true);
        
        try {
            const result = await new Promise((resolve) => {
                chrome.runtime.sendMessage({ action: 'revalidateLicense' }, resolve);
            });

            if (result.success && result.valid) {
                this.showMessage('License validated successfully!', 'success');
            } else {
                this.showMessage('License validation failed', 'error');
            }
            
            setTimeout(() => this.updateUI(), 1000);
        } catch (error) {
            this.showMessage('Error validating license: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async removeLicense() {
        if (!confirm('Are you sure you want to remove the license key?')) {
            return;
        }

        this.showLoading(true);
        
        try {
            const result = await new Promise((resolve) => {
                chrome.runtime.sendMessage({ action: 'removeLicense' }, resolve);
            });

            if (result.success) {
                this.showMessage('License removed', 'info');
                setTimeout(() => this.updateUI(), 1000);
            } else {
                this.showMessage(result.error || 'Failed to remove license', 'error');
            }
        } catch (error) {
            this.showMessage('Error removing license: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    showMessage(text, type = 'info') {
        const messageElement = document.getElementById('message');
        messageElement.textContent = text;
        messageElement.className = `message ${type}`;
        messageElement.style.display = 'block';
        
        setTimeout(() => {
            messageElement.style.display = 'none';
        }, 5000);
    }

    showLoading(show) {
        const buttons = document.querySelectorAll('button');
        const inputs = document.querySelectorAll('input');
        
        buttons.forEach(btn => btn.disabled = show);
        inputs.forEach(input => input.disabled = show);
        
        if (show) {
            this.showMessage('Processing...', 'info');
        }
    }
}

// Initialize popup
document.addEventListener('DOMContentLoaded', () => {
    const popupManager = new PopupManager();
    popupManager.init();
});
```

#### Popup HTML (`popup.html`)

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            width: 350px;
            padding: 16px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        .header {
            text-align: center;
            margin-bottom: 16px;
        }
        
        .status {
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 16px;
        }
        
        .status.active {
            background: #e8f5e8;
            color: #2e7d2e;
        }
        
        .status.inactive {
            background: #ffeaea;
            color: #d73a49;
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        
        .info-label {
            font-weight: bold;
        }
        
        .input-section {
            margin: 16px 0;
        }
        
        .input-section input {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            margin-right: 8px;
            margin-top: 8px;
        }
        
        .btn-primary {
            background: #0366d6;
            color: white;
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .message {
            padding: 8px;
            border-radius: 4px;
            margin: 8px 0;
            display: none;
        }
        
        .message.success {
            background: #d4edda;
            color: #155724;
        }
        
        .message.error {
            background: #f8d7da;
            color: #721c24;
        }
        
        .message.info {
            background: #cce7ff;
            color: #004085;
        }
    </style>
</head>
<body>
    <div class="header">
        <h2>License Manager</h2>
    </div>
    
    <div id="license-status" class="status inactive">Checking...</div>
    
    <div class="info-row">
        <span class="info-label">Current Key:</span>
        <span id="current-key">Loading...</span>
    </div>
    
    <div id="input-section" class="input-section">
        <input type="text" id="license-input" placeholder="Enter your license key..." />
    </div>
    
    <div id="message" class="message"></div>
    
    <div id="action-buttons">
        <button id="activate-btn" class="btn btn-primary">Activate License</button>
    </div>
    
    <script src="popup.js"></script>
</body>
</html>
```

#### Manifest V3 (`manifest.json`)

```json
{
    "manifest_version": 3,
    "name": "Your Extension",
    "version": "1.0.0",
    "description": "Extension with license validation",
    
    "permissions": [
        "storage",
        "notifications",
        "activeTab"
    ],
    
    "host_permissions": [
        "https://your-license-api.com/*"
    ],
    
    "background": {
        "service_worker": "background.js"
    },
    
    "action": {
        "default_popup": "popup.html",
        "default_title": "License Manager",
        "default_icon": {
            "16": "icons/icon-16.png",
            "32": "icons/icon-32.png",
            "48": "icons/icon-48.png",
            "128": "icons/icon-128.png"
        }
    },
    
    "icons": {
        "16": "icons/icon-16.png",
        "32": "icons/icon-32.png",
        "48": "icons/icon-48.png",
        "128": "icons/icon-128.png"
    }
}
```

## Key Features

### 🚀 Automatic Validation on Startup
- Extension validates license immediately when browser starts
- Handles network failures gracefully with caching
- Provides clear feedback to users

### 💾 Smart Caching
- Caches validation results for 1 hour to reduce API calls
- Handles offline scenarios gracefully
- Automatically refreshes expired cache

### 🔒 Secure Storage
- Uses Chrome's `chrome.storage.sync` for license keys (synced across devices)
- Uses `chrome.storage.local` for temporary cache
- Properly handles storage errors

### 🎯 Error Code Handling
- Leverages the enhanced error codes from your API
- Provides specific user actions for each error type
- Maintains good user experience even during errors

### 🔔 User Notifications
- Shows appropriate notifications for different license states
- Provides actionable buttons (Contact Support, Subscribe, etc.)
- Updates extension icon/badge to reflect status

### 🛠️ Developer Features
- Comprehensive logging for debugging
- Error handling for network issues
- Proper async/await patterns
- TypeScript-ready structure

## Testing Your Implementation

1. **Install extension** and verify it prompts for license key
2. **Enter valid license** and confirm extension activates
3. **Test invalid license** and verify proper error handling
4. **Test suspended license** using admin panel
5. **Test network failures** by disabling internet
6. **Test cache behavior** by restarting browser multiple times

## Best Practices

1. **Always validate on startup** - Never assume stored keys are still valid
2. **Cache validation results** - Reduce API load and improve offline experience
3. **Handle all error codes** - Provide specific guidance for each license state
4. **Graceful degradation** - Handle network failures appropriately
5. **User-friendly messaging** - Clear, actionable error messages
6. **Security** - Don't store sensitive data unnecessarily
7. **Performance** - Use timeouts and avoid blocking operations

This implementation provides a robust, user-friendly license validation system that handles all the error codes from your enhanced API!
