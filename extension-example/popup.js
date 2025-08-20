/**
 * Popup script for license management interface
 */

class PopupManager {
    constructor() {
        this.elements = {
            loading: document.getElementById('loading'),
            content: document.getElementById('content'),
            statusCard: document.getElementById('status-card'),
            statusContent: document.getElementById('status-content'),
            alertContainer: document.getElementById('alert-container'),
            licenseFormSection: document.getElementById('license-form-section'),
            licenseActionsSection: document.getElementById('license-actions-section'),
            licenseKeyInput: document.getElementById('license-key'),
            activateBtn: document.getElementById('activate-btn'),
            revalidateBtn: document.getElementById('revalidate-btn'),
            deactivateBtn: document.getElementById('deactivate-btn')
        };
        
        this.setupEventListeners();
        this.loadLicenseStatus();
    }

    setupEventListeners() {
        // Activate license button
        this.elements.activateBtn.addEventListener('click', () => {
            this.activateLicense();
        });

        // Revalidate license button
        this.elements.revalidateBtn.addEventListener('click', () => {
            this.revalidateLicense();
        });

        // Deactivate license button
        this.elements.deactivateBtn.addEventListener('click', () => {
            this.deactivateLicense();
        });

        // Enter key in license input
        this.elements.licenseKeyInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.activateLicense();
            }
        });
    }

    async loadLicenseStatus() {
        try {
            const response = await this.sendMessage({ type: 'GET_LICENSE_STATUS' });
            this.updateUI(response);
        } catch (error) {
            console.error('Error loading license status:', error);
            this.showError('Failed to load license status');
        } finally {
            this.hideLoading();
        }
    }

    async activateLicense() {
        const licenseKey = this.elements.licenseKeyInput.value.trim();
        
        if (!licenseKey) {
            this.showError('Please enter a license key');
            return;
        }

        this.setLoading(this.elements.activateBtn, 'Activating...');
        this.clearAlerts();

        try {
            const response = await this.sendMessage({ 
                type: 'ACTIVATE_LICENSE', 
                licenseKey 
            });

            if (response.success) {
                this.showSuccess(response.message);
                await this.loadLicenseStatus();
                this.elements.licenseKeyInput.value = '';
            } else {
                this.showError(response.message);
            }
        } catch (error) {
            console.error('Error activating license:', error);
            this.showError('Failed to activate license. Please try again.');
        } finally {
            this.resetButton(this.elements.activateBtn, 'Activate License');
        }
    }

    async revalidateLicense() {
        this.setLoading(this.elements.revalidateBtn, 'Checking...');
        this.clearAlerts();

        try {
            const response = await this.sendMessage({ type: 'REVALIDATE_LICENSE' });

            if (response.success) {
                this.showSuccess('License status updated');
                await this.loadLicenseStatus();
            } else {
                this.showError(response.message || 'License validation failed');
            }
        } catch (error) {
            console.error('Error revalidating license:', error);
            this.showError('Failed to check license status');
        } finally {
            this.resetButton(this.elements.revalidateBtn, 'Check License Status');
        }
    }

    async deactivateLicense() {
        if (!confirm('Are you sure you want to deactivate your license? This will disable all premium features.')) {
            return;
        }

        this.setLoading(this.elements.deactivateBtn, 'Deactivating...');
        this.clearAlerts();

        try {
            const response = await this.sendMessage({ type: 'DEACTIVATE_LICENSE' });

            if (response.success) {
                this.showSuccess(response.message);
                await this.loadLicenseStatus();
            } else {
                this.showError('Failed to deactivate license');
            }
        } catch (error) {
            console.error('Error deactivating license:', error);
            this.showError('Failed to deactivate license');
        } finally {
            this.resetButton(this.elements.deactivateBtn, 'Deactivate License');
        }
    }

    updateUI(status) {
        // Update status card
        const statusClass = status.isValid ? 'status-valid' : 'status-invalid';
        const statusIcon = status.isValid ? '✅' : '❌';
        const statusText = status.isValid ? 'License Active' : 'License Invalid';
        
        this.elements.statusCard.className = `status-card ${statusClass}`;
        
        let statusDetails = '';
        if (status.isValid && status.licenseKey) {
            statusDetails = `Key: ${status.licenseKey}`;
            if (status.lastCheck) {
                const lastCheckDate = new Date(status.lastCheck);
                statusDetails += `<br>Last checked: ${lastCheckDate.toLocaleString()}`;
            }
        } else if (!status.hasKey) {
            statusDetails = 'No license key installed';
        } else {
            statusDetails = 'License key is not valid or expired';
        }

        this.elements.statusContent.innerHTML = `
            <div class="status-text">
                <span class="status-icon">${statusIcon}</span>
                ${statusText}
            </div>
            <div class="status-details">${statusDetails}</div>
        `;

        // Show/hide appropriate sections
        if (status.isValid) {
            this.elements.licenseFormSection.classList.add('hidden');
            this.elements.licenseActionsSection.classList.remove('hidden');
        } else {
            this.elements.licenseFormSection.classList.remove('hidden');
            this.elements.licenseActionsSection.classList.add('hidden');
        }
    }

    showSuccess(message) {
        this.clearAlerts();
        const alert = document.createElement('div');
        alert.className = 'alert alert-success';
        alert.textContent = message;
        this.elements.alertContainer.appendChild(alert);
        
        setTimeout(() => alert.remove(), 5000);
    }

    showError(message) {
        this.clearAlerts();
        const alert = document.createElement('div');
        alert.className = 'alert alert-error';
        alert.textContent = message;
        this.elements.alertContainer.appendChild(alert);
        
        setTimeout(() => alert.remove(), 5000);
    }

    clearAlerts() {
        this.elements.alertContainer.innerHTML = '';
    }

    setLoading(button, text) {
        button.disabled = true;
        button.textContent = text;
    }

    resetButton(button, text) {
        button.disabled = false;
        button.textContent = text;
    }

    hideLoading() {
        this.elements.loading.classList.add('hidden');
        this.elements.content.classList.remove('hidden');
    }

    async sendMessage(message) {
        return new Promise((resolve, reject) => {
            chrome.runtime.sendMessage(message, (response) => {
                if (chrome.runtime.lastError) {
                    reject(new Error(chrome.runtime.lastError.message));
                } else if (response && response.error) {
                    reject(new Error(response.error));
                } else {
                    resolve(response);
                }
            });
        });
    }
}

// Initialize popup manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PopupManager();
});
