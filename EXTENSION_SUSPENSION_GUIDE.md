# Extension License Suspension Handling Guide

## 🔍 Issue Identified
The backend API correctly detects and rejects suspended licenses, but the extension may not be handling suspended license responses properly.

## ✅ API Response Format

### Valid License Response:
```json
{
  "valid": true,
  "message": "License key is valid",
  "expires_at": "2025-09-18T10:35:16.878970",
  "subscription_status": "active"
}
```

### Suspended License Response:
```json
{
  "valid": false,
  "message": "License key is suspended",
  "expires_at": null,
  "subscription_status": null
}
```

## 🛠️ Extension Implementation Requirements

### 1. Check the `valid` Field First
```javascript
// Always check this first
if (response.valid === false) {
    // License is invalid - check why
    handleInvalidLicense(response);
    return false;
}
```

### 2. Handle Different Invalid States
```javascript
function handleInvalidLicense(response) {
    const message = response.message.toLowerCase();
    
    if (message.includes('suspended')) {
        // License is suspended
        showSuspensionNotification();
        disableExtension();
        clearCache(); // Important: clear any cached license data
        
    } else if (message.includes('inactive')) {
        // License is inactive
        showInactiveNotification();
        
    } else if (message.includes('subscription')) {
        // Subscription issue
        showSubscriptionIssueNotification();
        
    } else {
        // Generic invalid license
        showInvalidLicenseNotification();
    }
}
```

### 3. Clear License Cache on Suspension
```javascript
function clearCache() {
    // Clear any stored license validation data
    localStorage.removeItem('licenseValidation');
    localStorage.removeItem('lastValidationTime');
    
    // Reset extension state
    chrome.storage.local.clear(['licenseData', 'validationCache']);
}
```

### 4. Show Appropriate User Notification
```javascript
function showSuspensionNotification() {
    const notification = {
        type: 'error',
        title: 'License Suspended',
        message: 'Your license has been suspended. Please contact support for assistance.',
        buttons: [
            {
                title: 'Contact Support',
                onClick: () => chrome.tabs.create({url: 'mailto:support@example.com'})
            }
        ]
    };
    
    chrome.notifications.create(notification);
}
```

### 5. Disable Extension Functionality
```javascript
function disableExtension() {
    // Disable main extension features
    chrome.action.setIcon({path: 'icons/disabled-icon.png'});
    chrome.action.setBadgeText({text: '❌'});
    chrome.action.setBadgeBackgroundColor({color: '#ff0000'});
    
    // Set flag to prevent functionality
    chrome.storage.local.set({extensionDisabled: true});
}
```

## 🔄 Complete Validation Flow

```javascript
async function validateLicense(licenseKey) {
    try {
        const response = await fetch('http://127.0.0.1:8000/api/validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                license_key: licenseKey,
                extension_version: chrome.runtime.getManifest().version,
                device_fingerprint: await getDeviceFingerprint()
            })
        });
        
        const result = await response.json();
        
        // Always check valid field first
        if (result.valid === false) {
            console.log('License validation failed:', result.message);
            handleInvalidLicense(result);
            return false;
        }
        
        // License is valid
        console.log('License validated successfully');
        updateValidationCache(result);
        return true;
        
    } catch (error) {
        console.error('License validation error:', error);
        // Handle network errors appropriately
        return false;
    }
}
```

## ⚠️ Common Issues to Avoid

1. **Caching Valid Responses**: Don't cache license validation responses indefinitely. Always re-validate periodically.

2. **Ignoring Error Messages**: Always check the `message` field to understand why validation failed.

3. **Not Clearing State**: When a license becomes invalid, clear all cached data and reset extension state.

4. **Poor User Experience**: Provide clear notifications about license status changes.

## 🧪 Testing Suspension

1. Get a valid license key
2. Test that it validates successfully
3. Use admin panel to suspend the license
4. Test validation again - should now return `{valid: false, message: "License key is suspended"}`
5. Verify extension handles this properly

## 🔧 Debug Tips

Add logging to see what responses the extension receives:

```javascript
console.log('License validation response:', result);
console.log('Valid:', result.valid);
console.log('Message:', result.message);
```

This will help identify if the extension is receiving the correct suspension response.
