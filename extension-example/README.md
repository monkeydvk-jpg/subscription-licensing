# Chrome Extension License Integration Example

This directory contains a complete example of how to integrate the subscription licensing system into a Chrome extension.

## Files Overview

### Core Files
- **`manifest.json`** - Chrome extension manifest with required permissions
- **`background.js`** - Service worker handling license management and validation
- **`popup.html`** - Extension popup interface for license activation
- **`popup.js`** - Popup interface logic
- **`content.js`** - Content script for feature gating on web pages

## Features Demonstrated

### License Management
- ✅ Automatic license validation on startup
- ✅ Periodic license checks (configurable interval)
- ✅ Secure license key storage using Chrome storage API
- ✅ Device fingerprinting for additional security
- ✅ Real-time license status updates

### User Interface
- ✅ Clean, modern popup interface
- ✅ License activation/deactivation
- ✅ Status indicators with visual feedback
- ✅ Error handling and user notifications

### Feature Gating
- ✅ Automatic feature enabling/disabling based on license status
- ✅ Premium feature demonstrations (buttons, shortcuts, etc.)
- ✅ License warning banners for unlicensed users
- ✅ Graceful degradation when license expires

## Installation & Setup

### 1. Update Configuration

Edit the following files to match your licensing server:

**`manifest.json`**
```json
"host_permissions": [
    "https://your-license-server.com/*"
]
```

**`background.js`**
```javascript
this.apiUrl = 'https://your-license-server.com/api';
```

**`popup.html`**
```html
<a href="https://your-license-server.com" target="_blank">Get License</a>
<a href="https://your-license-server.com/support" target="_blank">Support</a>
```

### 2. Load Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked" and select this directory
4. The extension icon should appear in your toolbar

### 3. Test License Integration

1. Click the extension icon to open the popup
2. Enter a valid license key from your licensing system
3. Click "Activate License" to test validation
4. Visit any webpage to see premium features in action

## Code Architecture

### Background Script (`background.js`)

The `LicenseManager` class handles all license operations:

```javascript
class LicenseManager {
    async validateLicense(licenseKey) {
        // Validates license with your server
        // Stores validation result
        // Updates extension badge
        // Notifies content scripts
    }
    
    getDeviceFingerprint() {
        // Creates unique device identifier
        // Used for license binding
    }
    
    // ... other methods
}
```

### Popup Interface (`popup.js`)

The `PopupManager` class provides the user interface:

```javascript
class PopupManager {
    async activateLicense() {
        // Handles license activation
        // Shows success/error feedback
        // Updates UI state
    }
    
    // ... other methods
}
```

### Content Script (`content.js`)

The `ExtensionFeatures` class manages feature gating:

```javascript
class ExtensionFeatures {
    enableFeatures() {
        // Enables premium features
        // Adds UI elements
        // Starts advanced functionality
    }
    
    showLicenseRequired() {
        // Shows license warning banner
        // Limits functionality
        // Prompts for activation
    }
    
    // ... other methods
}
```

## Customization

### Adding Premium Features

To add your own premium features, modify the `ExtensionFeatures` class in `content.js`:

```javascript
enableFeatures() {
    // Your existing code
    this.addCustomButtons();
    this.addKeyboardShortcuts();
    
    // Add your new features
    this.enableCustomFeature();
    this.startPremiumService();
}

enableCustomFeature() {
    if (!this.isLicensed) return;
    
    // Your premium feature implementation
    console.log('🌟 Custom premium feature enabled');
    
    // Example: Add premium UI elements
    const premiumPanel = document.createElement('div');
    premiumPanel.id = 'premium-panel';
    // ... customize your UI
    
    document.body.appendChild(premiumPanel);
}
```

### Customizing License Validation

Modify the validation request in `background.js` to include additional data:

```javascript
async validateLicense(licenseKey) {
    const response = await fetch(`${this.apiUrl}/validate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            license_key: licenseKey,
            extension_version: chrome.runtime.getManifest().version,
            device_fingerprint: await this.getDeviceFingerprint(),
            // Add custom fields
            user_agent: navigator.userAgent,
            timestamp: Date.now()
        })
    });
    
    // ... rest of validation logic
}
```

### Styling the Popup

Customize the popup appearance by editing the CSS in `popup.html`:

```css
/* Change color scheme */
body {
    background: linear-gradient(135deg, #your-color1 0%, #your-color2 100%);
}

/* Customize buttons */
.btn-primary {
    background: #your-brand-color;
}

/* Add your own styles */
.custom-section {
    /* Your custom styling */
}
```

## Security Considerations

### License Key Protection
- ✅ License keys are hashed before storage
- ✅ Plain text keys are not persisted
- ✅ Validation includes device fingerprinting
- ✅ Periodic revalidation prevents key sharing

### API Communication
- ✅ All API calls use HTTPS
- ✅ Request validation includes version checks
- ✅ Error messages don't expose sensitive data
- ✅ Rate limiting friendly (caches validation results)

### Feature Protection
- ✅ Features disabled immediately when license invalid
- ✅ No client-side license bypass possible
- ✅ Server-side validation required for activation
- ✅ Graceful handling of network issues

## Debugging

### Console Logging

The extension includes comprehensive logging:

```javascript
// Background script logs
console.log('🔑 License Manager: Initializing...');
console.log('✅ License Manager: License is valid');
console.error('❌ License Manager: License validation failed');

// Content script logs
console.log('🎯 Extension Features: Enabling premium features...');
console.log('🎯 Extension Features: License status changed');
```

### Testing License States

Test different scenarios:

1. **No License**: Fresh install, no key entered
2. **Invalid License**: Enter fake or expired key
3. **Valid License**: Enter working license key
4. **Network Issues**: Disconnect internet during validation
5. **License Expiry**: Test with soon-to-expire license

### Chrome DevTools

Use Chrome's extension debugging tools:

1. Right-click extension icon → "Inspect popup"
2. Go to `chrome://extensions/` → Click "background page" link
3. Check Console tab for error messages
4. Monitor Network tab for API calls

## Production Deployment

### Before Publishing

1. **Update URLs**: Replace all localhost URLs with production URLs
2. **Test Thoroughly**: Test all license states and edge cases
3. **Security Review**: Ensure no sensitive data is logged
4. **Performance**: Verify license checks don't impact performance

### Store Submission

1. **Permissions**: Only request necessary permissions
2. **Privacy**: Update privacy policy to mention license validation
3. **Description**: Clearly state subscription requirement
4. **Screenshots**: Show both free and premium features

### Monitoring

Consider adding telemetry to track:
- License validation success rates
- Feature usage statistics
- Error frequencies
- User activation patterns

## Support

For integration questions:

1. Check the main README.md for API documentation
2. Review the licensing server logs for validation issues
3. Test with curl commands to isolate API problems
4. Check Chrome extension console for client-side errors

## License

This example code is provided as part of the Extension License Manager system and follows the same license terms.
