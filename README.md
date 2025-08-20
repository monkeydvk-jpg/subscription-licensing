# Extension License Manager

A production-ready subscription licensing system built with FastAPI and Stripe. Perfect for selling monthly licenses for browser extensions, desktop apps, or any software product.

## Features

- **🔐 Secure License Management**: SHA-256 hashed license keys with secure validation
- **💳 Stripe Integration**: Complete checkout, subscription management, and webhooks
- **📊 Admin Dashboard**: Web-based interface for managing licenses and viewing analytics
- **🔄 Automatic Renewals**: Monthly billing with automatic license activation/suspension
- **📈 Usage Analytics**: Track license validation and user metrics
- **🛡️ Security**: JWT authentication, password hashing, IP tracking
- **⚡ Fast API**: High-performance endpoints for license validation

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd subscription-licensing
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

- Set a secure `SECRET_KEY`
- Add your Stripe API keys
- Configure admin credentials
- Set your domain URLs

### 3. Run the Application

```bash
# Development
python -m app.main

# Or with uvicorn
uvicorn app.main:app --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The application will be available at:
- **Main site**: http://localhost:8000
- **Admin panel**: http://localhost:8000/admin
- **API docs**: http://localhost:8000/docs

## Configuration

### Stripe Setup

1. Create a Stripe account and get your API keys
2. Create a monthly subscription product
3. Set up webhooks pointing to `https://yourdomain.com/webhooks/stripe`
4. Add the webhook secret to your `.env`

Required webhook events:
- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_failed`
- `invoice.payment_succeeded`

### Database

By default, uses SQLite for simplicity. For production, switch to PostgreSQL:

```bash
# Install PostgreSQL driver
pip install psycopg2-binary

# Update DATABASE_URL in .env
DATABASE_URL=postgresql://username:password@localhost/subscriptions
```

## API Endpoints

### Public Endpoints

#### Validate License
```http
POST /api/validate
Content-Type: application/json

{
    "license_key": "your-license-key",
    "extension_version": "1.0.0",
    "device_fingerprint": "optional-device-id"
}
```

Response:
```json
{
    "valid": true,
    "message": "License key is valid",
    "expires_at": "2024-02-01T00:00:00Z",
    "subscription_status": "active"
}
```

#### Create Checkout Session
```http
POST /api/checkout
Content-Type: application/json

{
    "email": "customer@example.com",
    "success_url": "https://yoursite.com/success",
    "cancel_url": "https://yoursite.com/cancel"
}
```

### Admin Endpoints

All admin endpoints require authentication with JWT token.

#### Login
```http
POST /api/admin/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=your-password
```

#### Get Dashboard Stats
```http
GET /api/admin/dashboard
Authorization: Bearer <jwt-token>
```

#### Manage Licenses
```http
# List licenses
GET /api/admin/licenses

# Create license
POST /api/admin/licenses
Content-Type: application/x-www-form-urlencoded
email=user@example.com

# Suspend license
POST /api/admin/licenses/{id}/suspend

# Activate license
POST /api/admin/licenses/{id}/activate

# Rotate license key
POST /api/admin/licenses/{id}/rotate
```

## Extension Integration

### Chrome Extension Example

```javascript
// background.js
class LicenseManager {
    constructor() {
        this.apiUrl = 'https://your-license-server.com/api';
        this.licenseKey = null;
        this.lastCheck = null;
    }

    async validateLicense(licenseKey) {
        try {
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
                this.licenseKey = licenseKey;
                this.lastCheck = Date.now();
                await this.storeLicenseData(licenseKey, result);
                return true;
            } else {
                console.error('License validation failed:', result.message);
                return false;
            }
        } catch (error) {
            console.error('License validation error:', error);
            return false;
        }
    }

    async getDeviceFingerprint() {
        // Create a simple device fingerprint
        const userAgent = navigator.userAgent;
        const screen = `${screen.width}x${screen.height}`;
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        
        const data = `${userAgent}-${screen}-${timezone}`;
        const buffer = new TextEncoder().encode(data);
        const hash = await crypto.subtle.digest('SHA-256', buffer);
        
        return Array.from(new Uint8Array(hash))
            .map(b => b.toString(16).padStart(2, '0'))
            .join('').substring(0, 16);
    }

    async storeLicenseData(key, validationResult) {
        await chrome.storage.local.set({
            licenseKey: key,
            licenseExpires: validationResult.expires_at,
            lastValidated: Date.now()
        });
    }

    async shouldCheckLicense() {
        if (!this.lastCheck) return true;
        
        const hoursSinceCheck = (Date.now() - this.lastCheck) / (1000 * 60 * 60);
        return hoursSinceCheck >= 24; // Check daily
    }
}

// Initialize license manager
const licenseManager = new LicenseManager();

// Check license on startup
chrome.runtime.onStartup.addListener(async () => {
    const data = await chrome.storage.local.get(['licenseKey']);
    if (data.licenseKey && await licenseManager.shouldCheckLicense()) {
        await licenseManager.validateLicense(data.licenseKey);
    }
});
```

## Architecture

### Project Structure

```
subscription-licensing/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database setup
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── security.py          # Security utilities
│   ├── deps.py              # Dependencies
│   ├── utils.py             # Utility functions
│   ├── tasks.py             # Background tasks
│   ├── services/
│   │   ├── license_service.py   # License management
│   │   └── stripe_service.py    # Stripe integration
│   └── webhooks/
│       └── stripe.py            # Stripe webhooks
├── templates/               # HTML templates
├── static/                  # Static files (CSS, JS)
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
└── README.md               # This file
```

### Database Models

- **User**: Customer information and Stripe customer ID
- **License**: License keys with metadata and usage tracking
- **Subscription**: Stripe subscription details and status
- **AdminUser**: Admin panel authentication
- **ApiLog**: API usage logging and analytics

## Security Features

- **License Key Hashing**: Keys stored as SHA-256 hashes
- **JWT Authentication**: Secure admin panel access
- **Rate Limiting**: Built-in FastAPI rate limiting
- **IP Tracking**: Monitor license usage by location
- **Device Fingerprinting**: Optional device binding
- **Webhook Verification**: Stripe webhook signature validation

## Maintenance

### Background Tasks

The system includes maintenance tasks that should run periodically:

```python
from app.tasks import run_all_maintenance_tasks

# Run maintenance (add to cron job)
run_all_maintenance_tasks()
```

Tasks include:
- Clean up old API logs
- Sync subscription statuses with Stripe
- Suspend expired licenses
- Update license expiry dates
- Generate usage statistics

### Monitoring

Monitor these endpoints for system health:
- `GET /api/health` - Health check
- Admin dashboard for usage metrics
- Database connection status
- Stripe webhook delivery status

## Production Deployment

### Environment Setup

1. Use a production database (PostgreSQL recommended)
2. Set secure environment variables
3. Configure proper logging
4. Set up SSL/HTTPS
5. Configure webhook endpoints
6. Set up monitoring and alerts

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Scaling Considerations

- Use Redis for session storage
- Implement proper caching
- Set up load balancing
- Monitor database performance
- Configure auto-scaling

## Support

For issues and questions:

1. Check the API documentation at `/docs`
2. Review the admin panel for system status
3. Check application logs
4. Verify Stripe webhook delivery
5. Test license validation endpoints

## License

This project is available under the MIT License.
