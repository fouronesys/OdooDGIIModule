#!/usr/bin/env python3
"""
Demo application entry point for the NCF Management Flask application
"""

from app import app

# app is already created and configured in app.py

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)