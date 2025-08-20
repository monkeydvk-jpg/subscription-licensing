# Extension License Error Handling Guide

This guide provides instructions for browser extension developers on how to properly handle license validation responses with the enhanced error code system.

## Overview

The license validation API now returns an `error_code` field in addition to the `valid` boolean and `message` string. This allows extensions to programmatically handle different error states without relying on string parsing.

## License Validation Response Schema

```json
{
  "valid": boolean,
  "message": string,
  "error_code": string | null,
  "expires_at": string | null,
  "subscription_status": string | null
}
```

## Error Codes

### SUSPENDED
- **Description**: License key has been suspended by an administrator
- **Handling**: 
  - Clear any cached license data
  - Disable extension functionality
  - Show suspension notice to user
  - Provide contact information for support

### INVALID_KEY
- **Description**: License key was not found in the database
- **Handling**:
  - Clear stored license key
  - Show "Invalid license key" message
  - Prompt user to enter a valid license key

### INACTIVE
- **Description**: License key has been deactivated
- **Handling**:
  - Clear cached license data
  - Disable extension functionality
  - Show "License inactive" message
  - Provide renewal/reactivation instructions

### NO_SUBSCRIPTION
- **Description**: User has no active subscription associated with their license
- **Handling**:
  - Show subscription required message
  - Provide link to subscription purchase page
  - Disable premium features

### SUBSCRIPTION_INACTIVE
- **Description**: User's subscription is not in an active state (canceled, past_due, etc.)
- **Handling**:
  - Check `subscription_status` field for specific status
  - Show appropriate message based on status
  - Provide renewal or payment update links

## Recommended Implementation

### JavaScript Example

```javascript
class LicenseValidator {
    constructor(licenseKey) {
        this.licenseKey = licenseKey;
        this.validationEndpoint = 'https://your-api.com/api/license/validate';
    }

    async validateLicense() {
        try {
            const response = await fetch(this.validationEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    license_key: this.licenseKey,
                    extension_version: chrome.runtime.getManifest().version,
                    device_fingerprint: await this.generateDeviceFingerprint()
                })
            });

            const result = await response.json();
            return this.handleValidationResult(result);
        } catch (error) {
            console.error('License validation failed:', error);
            return this.handleNetworkError();
        }
    }

    handleValidationResult(result) {
        // Always check 'valid' field first
        if (result.valid) {
            return this.handleValidLicense(result);
        }

        // Handle specific error cases using error_code
        switch (result.error_code) {
            case 'SUSPENDED':
                return this.handleSuspendedLicense(result);
            
            case 'INVALID_KEY':
                return this.handleInvalidKey(result);
            
            case 'INACTIVE':
                return this.handleInactiveLicense(result);
            
            case 'NO_SUBSCRIPTION':
                return this.handleNoSubscription(result);
            
            case 'SUBSCRIPTION_INACTIVE':
                return this.handleInactiveSubscription(result);
            
            default:
                // Fallback to message-based handling for unknown error codes
                return this.handleGenericError(result);
        }
    }

    handleValidLicense(result) {
        // Enable extension functionality
        this.enableExtension();
        
        // Cache validation result with expiration
        this.cacheValidation(result, result.expires_at);
        
        // Update UI to show active status
        this.updateUI({
            status: 'active',
            expires_at: result.expires_at,
            subscription_status: result.subscription_status
        });
        
        return { success: true, result };
    }

    handleSuspendedLicense(result) {
        // Clear any cached data
        this.clearCache();
        
        // Disable extension functionality
        this.disableExtension();
        
        // Show suspension notice
        this.showNotification({
            type: 'error',
            title: 'License Suspended',
            message: 'Your license has been suspended. Please contact support for assistance.',
            persistent: true
        });
        
        // Update UI
        this.updateUI({
            status: 'suspended',
            message: result.message
        });
        
        return { success: false, error: 'SUSPENDED', result };
    }

    handleInvalidKey(result) {
        // Clear stored license key
        this.clearStoredLicense();
        
        // Show invalid key message
        this.showNotification({
            type: 'error',
            title: 'Invalid License',
            message: 'The license key you entered is not valid. Please check and try again.'
        });
        
        // Prompt for new license key
        this.promptForLicenseKey();
        
        return { success: false, error: 'INVALID_KEY', result };
    }

    handleInactiveLicense(result) {
        // Clear cached data
        this.clearCache();
        
        // Disable extension
        this.disableExtension();
        
        // Show reactivation message
        this.showNotification({
            type: 'warning',
            title: 'License Inactive',
            message: 'Your license is inactive. Please contact support to reactivate your license.',
            actions: [{
                text: 'Contact Support',
                action: () => this.openSupportPage()
            }]
        });
        
        return { success: false, error: 'INACTIVE', result };
    }

    handleNoSubscription(result) {
        // Show subscription required message
        this.showNotification({
            type: 'info',
            title: 'Subscription Required',
            message: 'An active subscription is required to use this extension.',
            actions: [{
                text: 'Subscribe Now',
                action: () => this.openSubscriptionPage()
            }]
        });
        
        // Disable premium features
        this.disablePremiumFeatures();
        
        return { success: false, error: 'NO_SUBSCRIPTION', result };
    }

    handleInactiveSubscription(result) {
        const subscriptionStatus = result.subscription_status;
        let message, actions = [];
        
        switch (subscriptionStatus) {
            case 'canceled':
                message = 'Your subscription has been canceled. Renew to continue using premium features.';
                actions = [{
                    text: 'Renew Subscription',
                    action: () => this.openSubscriptionPage()
                }];
                break;
            
            case 'past_due':
                message = 'Your subscription payment is past due. Please update your payment method.';
                actions = [{
                    text: 'Update Payment',
                    action: () => this.openPaymentPage()
                }];
                break;
            
            case 'unpaid':
                message = 'Your subscription has unpaid invoices. Please resolve payment issues.';
                actions = [{
                    text: 'View Invoices',
                    action: () => this.openBillingPage()
                }];
                break;
            
            default:
                message = `Your subscription status is ${subscriptionStatus}. Please check your account.`;
                actions = [{
                    text: 'View Account',
                    action: () => this.openAccountPage()
                }];
        }
        
        this.showNotification({
            type: 'warning',
            title: 'Subscription Issue',
            message,
            actions
        });
        
        // Disable premium features
        this.disablePremiumFeatures();
        
        return { success: false, error: 'SUBSCRIPTION_INACTIVE', result };
    }

    handleGenericError(result) {
        // Fallback handling for unknown error codes
        console.warn('Unknown error code:', result.error_code);
        
        this.showNotification({
            type: 'error',
            title: 'License Error',
            message: result.message || 'An error occurred while validating your license.'
        });
        
        return { success: false, error: 'UNKNOWN', result };
    }

    handleNetworkError() {
        // Handle network/server errors
        this.showNotification({
            type: 'error',
            title: 'Connection Error',
            message: 'Unable to validate license. Please check your internet connection and try again.'
        });
        
        return { success: false, error: 'NETWORK_ERROR' };
    }

    // Helper methods (implement based on your extension architecture)
    enableExtension() {
        // Enable all extension functionality
    }

    disableExtension() {
        // Disable extension functionality but keep basic UI
    }

    disablePremiumFeatures() {
        // Disable only premium features, keep basic functionality
    }

    clearCache() {
        // Clear any cached license validation data
    }

    clearStoredLicense() {
        // Remove stored license key
    }

    cacheValidation(result, expiresAt) {
        // Cache validation result with expiration
    }

    showNotification(options) {
        // Show notification to user based on your UI framework
    }

    updateUI(status) {
        // Update extension UI based on license status
    }

    promptForLicenseKey() {
        // Show license key input dialog
    }

    openSupportPage() {
        // Open support contact page
    }

    openSubscriptionPage() {
        // Open subscription purchase page
    }

    openPaymentPage() {
        // Open payment method update page
    }

    openBillingPage() {
        // Open billing/invoices page
    }

    openAccountPage() {
        // Open user account page
    }

    async generateDeviceFingerprint() {
        // Generate a unique device fingerprint
        // This could be based on browser info, screen resolution, etc.
        return 'device_fingerprint_hash';
    }
}
```

## Best Practices

### 1. Cache Management
- Clear cache immediately when receiving error responses
- Set appropriate cache expiration based on `expires_at` for valid licenses
- Implement cache invalidation for manual refresh

### 2. User Experience
- Show clear, actionable messages for each error type
- Provide direct links to resolve issues (subscription, payment, support)
- Use appropriate notification types (error, warning, info)
- Don't spam users with repeated validation attempts

### 3. Graceful Degradation
- Disable features progressively based on license status
- Keep basic extension functionality when possible
- Provide clear indication of what features are unavailable

### 4. Error Logging
- Log validation attempts and results for debugging
- Include error codes in logs for easier support
- Don't log sensitive information (license keys, user data)

### 5. Retry Logic
- Implement exponential backoff for network errors
- Don't retry on definitive errors (INVALID_KEY, SUSPENDED)
- Respect rate limits and server responses

## Migration from Message-Based Handling

If you're currently checking the `message` field for specific strings:

**Old approach:**
```javascript
if (result.message.includes('suspended')) {
    // Handle suspension
}
```

**New approach:**
```javascript
if (result.error_code === 'SUSPENDED') {
    // Handle suspension
}
```

This new approach is more reliable and language-independent.

## Testing Your Implementation

1. Test each error code scenario in your development environment
2. Verify proper UI updates for each case
3. Test offline/network error scenarios
4. Validate cache behavior across different error states
5. Test user flows for resolving each error type

## Support

If you encounter issues implementing these error handling patterns, please contact our developer support team with:
- Your extension ID and version
- Specific error codes you're seeing
- Console logs and network requests
- Steps to reproduce the issue
