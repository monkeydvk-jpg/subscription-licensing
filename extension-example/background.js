/**
 * Background script for license management
 */

class LicenseManager {
    constructor() {
        this.apiUrl = 'https://your-license-server.com/api';
        this.licenseKey = null;
        this.lastCheck = null;
        this.isValid = false;
        this.checkInterval = 24 * 60 * 60 * 1000; // 24 hours
    }

    async initialize() {
        console.log('🔑 License Manager: Initializing...');
        
        // Load stored license data
        const data = await chrome.storage.local.get([
            'licenseKey', 
            'licenseExpires', 
            'lastValidated',
            'licenseValid'
        ]);
        
        if (data.licenseKey) {
            this.licenseKey = data.licenseKey;
            this.lastCheck = data.lastValidated;
            this.isValid = data.licenseValid || false;
            
            console.log('🔑 License Manager: Found stored license');
            
            // Check if we need to revalidate
            if (await this.shouldCheckLicense()) {
                console.log('🔑 License Manager: Revalidating license...');
                await this.validateLicense(this.licenseKey);
            }
        } else {
            console.log('🔑 License Manager: No license found, extension locked');
            this.isValid = false;
        }
        
        // Update extension badge
        this.updateBadge();
    }

    async validateLicense(licenseKey) {
        try {
            console.log('🔑 License Manager: Validating license...');
            
            const response = await fetch(`${this.apiUrl}/validate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    license_key: licenseKey,
                    extension_version: chrome.runtime.getManifest().version,
                    device_fingerprint: await this.getDeviceFingerprint()
                })
            });

            const result = await response.json();
            
            if (result.valid) {
                console.log('✅ License Manager: License is valid');
                
                this.licenseKey = licenseKey;
                this.lastCheck = Date.now();
                this.isValid = true;
                
                await this.storeLicenseData(licenseKey, result);
                this.updateBadge();
                
                // Notify content scripts
                this.notifyLicenseStatus(true);
                
                return true;
            } else {
                console.error('❌ License Manager: License validation failed:', result.message);
                
                this.isValid = false;
                this.updateBadge();
                this.notifyLicenseStatus(false, result.message);
                
                return false;
            }
        } catch (error) {
            console.error('🚨 License Manager: Validation error:', error);
            this.isValid = false;
            this.updateBadge();
            return false;
        }
    }

    async getDeviceFingerprint() {
        // Create a simple device fingerprint
        const userAgent = navigator.userAgent;
        const screen = `${screen.width}x${screen.height}`;
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        const language = navigator.language;
        
        const data = `${userAgent}-${screen}-${timezone}-${language}`;
        const encoder = new TextEncoder();
        const buffer = encoder.encode(data);
        
        const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        
        return hashArray
            .map(b => b.toString(16).padStart(2, '0'))
            .join('')
            .substring(0, 16);
    }

    async storeLicenseData(key, validationResult) {
        await chrome.storage.local.set({
            licenseKey: key,
            licenseExpires: validationResult.expires_at,
            lastValidated: Date.now(),
            licenseValid: true,
            subscriptionStatus: validationResult.subscription_status
        });
    }

    async shouldCheckLicense() {
        if (!this.lastCheck) return true;
        
        const timeSinceCheck = Date.now() - this.lastCheck;
        return timeSinceCheck >= this.checkInterval;
    }

    updateBadge() {
        const badgeText = this.isValid ? '✓' : '✗';
        const badgeColor = this.isValid ? '#4CAF50' : '#F44336';
        
        chrome.action.setBadgeText({ text: badgeText });
        chrome.action.setBadgeBackgroundColor({ color: badgeColor });
    }

    async notifyLicenseStatus(isValid, message = '') {
        // Send message to all tabs
        const tabs = await chrome.tabs.query({});
        
        for (const tab of tabs) {
            try {
                await chrome.tabs.sendMessage(tab.id, {
                    type: 'LICENSE_STATUS',
                    isValid,
                    message
                });
            } catch (error) {
                // Tab might not have content script, ignore
            }
        }
    }

    async activateLicense(licenseKey) {
        const isValid = await this.validateLicense(licenseKey);
        
        if (isValid) {
            console.log('🎉 License Manager: License activated successfully');
            return { success: true, message: 'License activated successfully!' };
        } else {
            console.log('💔 License Manager: License activation failed');
            return { success: false, message: 'Invalid or expired license key' };
        }
    }

    async deactivateLicense() {
        console.log('🔓 License Manager: Deactivating license...');
        
        this.licenseKey = null;
        this.isValid = false;
        this.lastCheck = null;
        
        // Clear stored data
        await chrome.storage.local.clear();
        
        this.updateBadge();
        this.notifyLicenseStatus(false, 'License deactivated');
        
        return { success: true, message: 'License deactivated' };
    }

    // Check if extension functionality should be enabled
    isFeatureEnabled() {
        return this.isValid;
    }

    // Get license status for popup
    getStatus() {
        return {
            isValid: this.isValid,
            hasKey: !!this.licenseKey,
            lastCheck: this.lastCheck,
            licenseKey: this.licenseKey ? this.maskLicenseKey(this.licenseKey) : null
        };
    }

    maskLicenseKey(key) {
        if (!key || key.length < 8) return key;
        return key.substring(0, 4) + '****' + key.substring(key.length - 4);
    }
}

// Initialize license manager
const licenseManager = new LicenseManager();

// Extension lifecycle events
chrome.runtime.onInstalled.addListener(async () => {
    console.log('🚀 Extension installed, initializing license manager...');
    await licenseManager.initialize();
});

chrome.runtime.onStartup.addListener(async () => {
    console.log('🌅 Browser started, initializing license manager...');
    await licenseManager.initialize();
});

// Handle messages from popup and content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    (async () => {
        switch (message.type) {
            case 'GET_LICENSE_STATUS':
                sendResponse(licenseManager.getStatus());
                break;
                
            case 'ACTIVATE_LICENSE':
                const activateResult = await licenseManager.activateLicense(message.licenseKey);
                sendResponse(activateResult);
                break;
                
            case 'DEACTIVATE_LICENSE':
                const deactivateResult = await licenseManager.deactivateLicense();
                sendResponse(deactivateResult);
                break;
                
            case 'CHECK_FEATURE_ENABLED':
                sendResponse({ enabled: licenseManager.isFeatureEnabled() });
                break;
                
            case 'REVALIDATE_LICENSE':
                if (licenseManager.licenseKey) {
                    const revalidateResult = await licenseManager.validateLicense(licenseManager.licenseKey);
                    sendResponse({ success: revalidateResult });
                } else {
                    sendResponse({ success: false, message: 'No license key found' });
                }
                break;
                
            default:
                sendResponse({ error: 'Unknown message type' });
        }
    })();
    
    return true; // Keep message channel open for async response
});

// Periodic license check (every hour when browser is active)
chrome.alarms.onAlarm.addListener(async (alarm) => {
    if (alarm.name === 'licenseCheck') {
        console.log('⏰ Periodic license check triggered');
        
        if (licenseManager.licenseKey && await licenseManager.shouldCheckLicense()) {
            await licenseManager.validateLicense(licenseManager.licenseKey);
        }
    }
});

// Set up periodic checks
chrome.alarms.create('licenseCheck', { 
    delayInMinutes: 60, 
    periodInMinutes: 60 
});

// Initialize on script load
licenseManager.initialize();
