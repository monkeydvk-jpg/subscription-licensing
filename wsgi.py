#!/usr/bin/env python3
"""
WSGI configuration for PythonAnywhere deployment
This file adapts the FastAPI ASGI application to work with PythonAnywhere's WSGI infrastructure.
"""

import os
import sys

# Add your project directory to the Python path
# Replace 'your_username' and 'subscription-licensing' with your actual paths
project_home = '/home/your_username/subscription-licensing'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables if needed
os.environ.setdefault('DATABASE_URL', 'sqlite:///subscriptions.db')
os.environ.setdefault('SECRET_KEY', 'your-secret-key-change-in-production')

# Import your FastAPI application
try:
    from app.main import app as fastapi_app
except ImportError as e:
    # Fallback error handling
    def error_app(environ, start_response):
        status = '500 Internal Server Error'
        headers = [('Content-Type', 'text/plain')]
        start_response(status, headers)
        return [f'Import Error: {str(e)}'.encode()]
    
    application = error_app
else:
    # Use a2wsgi to wrap the FastAPI ASGI app for WSGI compatibility
    from a2wsgi import ASGIMiddleware
    application = ASGIMiddleware(fastapi_app)
