/**
 * Content script for feature gating based on license status
 */

class ExtensionFeatures {
    constructor() {
        this.isLicensed = false;
        this.initialize();
    }

    async initialize() {
        console.log('🎯 Extension Features: Initializing content script...');
        
        // Check initial license status
        await this.checkLicenseStatus();
        
        // Listen for license status changes from background script
        this.setupMessageListener();
        
        // Start the extension functionality if licensed
        if (this.isLicensed) {
            this.enableFeatures();
        } else {
            this.showLicenseRequired();
        }
    }

    async checkLicenseStatus() {
        try {
            const response = await this.sendMessageToBackground({
                type: 'CHECK_FEATURE_ENABLED'
            });
            
            this.isLicensed = response.enabled;
            console.log(`🎯 Extension Features: License status - ${this.isLicensed ? 'ACTIVE' : 'INACTIVE'}`);
        } catch (error) {
            console.error('🚨 Extension Features: Failed to check license status:', error);
            this.isLicensed = false;
        }
    }

    setupMessageListener() {
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
            if (message.type === 'LICENSE_STATUS') {
                this.handleLicenseStatusChange(message.isValid, message.message);
            }
        });
    }

    handleLicenseStatusChange(isValid, message) {
        console.log(`🎯 Extension Features: License status changed - ${isValid ? 'VALID' : 'INVALID'}`);
        
        this.isLicensed = isValid;
        
        if (isValid) {
            this.removeLicenseWarning();
            this.enableFeatures();
            this.showNotification('✅ Extension activated!', 'success');
        } else {
            this.disableFeatures();
            this.showLicenseRequired();
            this.showNotification(`❌ ${message || 'License invalid'}`, 'error');
        }
    }

    enableFeatures() {
        console.log('🎯 Extension Features: Enabling premium features...');
        
        // Remove any existing license warnings
        this.removeLicenseWarning();
        
        // Example feature implementations
        this.addCustomButtons();
        this.addKeyboardShortcuts();
        this.initializeAdvancedFeatures();
        
        // Mark page as having premium features enabled
        document.body.setAttribute('data-extension-licensed', 'true');
    }

    disableFeatures() {
        console.log('🎯 Extension Features: Disabling premium features...');
        
        // Remove premium features
        this.removeCustomButtons();
        this.removeKeyboardShortcuts();
        this.disableAdvancedFeatures();
        
        // Mark page as not having premium features
        document.body.removeAttribute('data-extension-licensed');
    }

    showLicenseRequired() {
        // Create license warning banner
        const banner = this.createLicenseBanner();
        document.body.prepend(banner);
        
        // Show periodic reminders (every 30 seconds)
        this.licenseReminderInterval = setInterval(() => {
            this.showNotification('🔑 Premium features require a valid license', 'warning');
        }, 30000);
    }

    createLicenseBanner() {
        // Remove existing banner if present
        this.removeLicenseWarning();
        
        const banner = document.createElement('div');
        banner.id = 'extension-license-banner';
        banner.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 20px;
            text-align: center;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            font-size: 14px;
            font-weight: 500;
            z-index: 999999;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            border-bottom: 1px solid rgba(255,255,255,0.2);
        `;
        
        banner.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; gap: 15px;">
                <span>🔑 This extension requires a valid license to access premium features</span>
                <button id="extension-activate-btn" style="
                    background: rgba(255,255,255,0.2);
                    border: 1px solid rgba(255,255,255,0.3);
                    color: white;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 12px;
                    cursor: pointer;
                    font-weight: bold;
                    transition: all 0.3s ease;
                ">Activate License</button>
                <button id="extension-close-banner" style="
                    background: none;
                    border: none;
                    color: white;
                    font-size: 18px;
                    cursor: pointer;
                    padding: 0;
                    width: 20px;
                    height: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                ">×</button>
            </div>
        `;
        
        // Add event listeners
        banner.querySelector('#extension-activate-btn').addEventListener('click', () => {
            chrome.runtime.openOptionsPage();
        });
        
        banner.querySelector('#extension-close-banner').addEventListener('click', () => {
            banner.remove();
        });
        
        // Add hover effects
        const activateBtn = banner.querySelector('#extension-activate-btn');
        activateBtn.addEventListener('mouseenter', () => {
            activateBtn.style.background = 'rgba(255,255,255,0.3)';
        });
        activateBtn.addEventListener('mouseleave', () => {
            activateBtn.style.background = 'rgba(255,255,255,0.2)';
        });
        
        return banner;
    }

    removeLicenseWarning() {
        // Remove banner
        const existingBanner = document.getElementById('extension-license-banner');
        if (existingBanner) {
            existingBanner.remove();
        }
        
        // Clear reminder interval
        if (this.licenseReminderInterval) {
            clearInterval(this.licenseReminderInterval);
            this.licenseReminderInterval = null;
        }
    }

    // Example feature implementations
    addCustomButtons() {
        // Only add if not already present and licensed
        if (!this.isLicensed || document.querySelector('.extension-premium-button')) {
            return;
        }
        
        console.log('🎯 Extension Features: Adding custom buttons...');
        
        // Example: Add a floating action button
        const floatingButton = document.createElement('div');
        floatingButton.className = 'extension-premium-button';
        floatingButton.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 56px;
            height: 56px;
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            border-radius: 50%;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            z-index: 999998;
            transition: transform 0.3s ease;
        `;
        floatingButton.innerHTML = '⭐';
        floatingButton.title = 'Premium Feature (Licensed)';
        
        floatingButton.addEventListener('mouseenter', () => {
            floatingButton.style.transform = 'scale(1.1)';
        });
        
        floatingButton.addEventListener('mouseleave', () => {
            floatingButton.style.transform = 'scale(1)';
        });
        
        floatingButton.addEventListener('click', () => {
            this.showNotification('🌟 Premium feature activated!', 'success');
            // Add your premium feature logic here
        });
        
        document.body.appendChild(floatingButton);
    }

    removeCustomButtons() {
        const buttons = document.querySelectorAll('.extension-premium-button');
        buttons.forEach(button => button.remove());
    }

    addKeyboardShortcuts() {
        if (!this.isLicensed) return;
        
        console.log('🎯 Extension Features: Adding keyboard shortcuts...');
        
        this.keyboardHandler = (e) => {
            // Example: Ctrl+Shift+E for premium action
            if (e.ctrlKey && e.shiftKey && e.key === 'E') {
                e.preventDefault();
                this.showNotification('⌨️ Premium shortcut activated!', 'success');
                // Add your shortcut logic here
            }
        };
        
        document.addEventListener('keydown', this.keyboardHandler);
    }

    removeKeyboardShortcuts() {
        if (this.keyboardHandler) {
            document.removeEventListener('keydown', this.keyboardHandler);
            this.keyboardHandler = null;
        }
    }

    initializeAdvancedFeatures() {
        if (!this.isLicensed) return;
        
        console.log('🎯 Extension Features: Initializing advanced features...');
        
        // Example advanced features
        this.startAutoSave();
        this.enableAnalytics();
        // Add more premium features here
    }

    disableAdvancedFeatures() {
        this.stopAutoSave();
        this.disableAnalytics();
    }

    startAutoSave() {
        // Example auto-save feature
        this.autoSaveInterval = setInterval(() => {
            console.log('💾 Auto-saving (premium feature)...');
            // Implement auto-save logic
        }, 60000); // Every minute
    }

    stopAutoSave() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
            this.autoSaveInterval = null;
        }
    }

    enableAnalytics() {
        console.log('📊 Analytics enabled (premium feature)');
        // Implement analytics
    }

    disableAnalytics() {
        console.log('📊 Analytics disabled');
        // Disable analytics
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#F44336' : type === 'warning' ? '#FF9800' : '#2196F3'};
            color: white;
            padding: 12px 16px;
            border-radius: 6px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            font-size: 14px;
            font-weight: 500;
            z-index: 999999;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            max-width: 300px;
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Remove after delay
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    async sendMessageToBackground(message) {
        return new Promise((resolve, reject) => {
            chrome.runtime.sendMessage(message, (response) => {
                if (chrome.runtime.lastError) {
                    reject(new Error(chrome.runtime.lastError.message));
                } else {
                    resolve(response);
                }
            });
        });
    }
}

// Initialize extension features when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new ExtensionFeatures();
    });
} else {
    new ExtensionFeatures();
}
