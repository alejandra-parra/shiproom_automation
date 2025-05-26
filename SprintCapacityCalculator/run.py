#!/usr/bin/env python3
"""
Sprint Capacity Calculator - Main Startup Script
Automatically uses virtual environment and provides helpful error messages
"""

import os
import sys
import time
import webbrowser
import threading
import subprocess
from pathlib import Path

def get_venv_python():
    """Get the path to the virtual environment Python executable"""
    if os.name == 'nt':  # Windows
        venv_python = os.path.join('venv', 'Scripts', 'python.exe')
    else:  # macOS/Linux
        venv_python = os.path.join('venv', 'bin', 'python')
    
    if os.path.exists(venv_python):
        return venv_python
    return None

def is_venv_activated():
    """Check if we're running in the virtual environment"""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

def check_environment():
    """Check if the environment is properly set up"""
    issues = []
    warnings = []
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        warnings.append("⚠️  .env file not found. Copy env.example to .env and configure it.")
    
    # Check if required packages are installed
    try:
        import flask
        import requests
        from config import Config
        print("✅ All dependencies found")
    except ImportError as e:
        issues.append(f"❌ Missing dependency: {e.name}")
        issues.append("💡 Run: python setup.py")
    
    return issues, warnings

def open_browser_after_delay():
    """Open browser after a short delay to ensure server is ready"""
    time.sleep(2)
    webbrowser.open('http://localhost:5001')

def main():
    """Main function to run the application"""
    print("🚀 Starting Sprint Capacity Calculator...")
    print("=" * 50)
    
    # Check if we need to use virtual environment
    venv_python = get_venv_python()
    
    if venv_python and not is_venv_activated():
        print("🔄 Using virtual environment...")
        try:
            # Start browser opening in background thread
            browser_thread = threading.Thread(target=open_browser_after_delay)
            browser_thread.daemon = True
            browser_thread.start()
            
            # Run app.py using the virtual environment Python
            subprocess.run([venv_python, 'app.py'], check=True)
            return
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running with virtual environment: {e}")
            print("💡 Try running: python setup.py")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n👋 Server stopped by user")
            return
    
    # We're either in venv already or no venv exists - proceed with checks
    if venv_python:
        print("✅ Running in virtual environment")
    else:
        print("⚠️  No virtual environment found - using system Python")
    
    # Check environment
    issues, warnings = check_environment()
    
    # Show warnings (non-blocking)
    if warnings:
        print("⚠️  Warnings:")
        for warning in warnings:
            print(f"   {warning}")
        print()
    
    # Show critical issues (blocking)
    if issues:
        print("❌ Critical issues detected:")
        for issue in issues:
            print(f"   {issue}")
        sys.exit(1)
    
    # Import and run the app
    try:
        from app import app
        print("🌐 Starting web server...")
        print("📱 Opening browser to: http://localhost:5001")
        print("🛑 Press Ctrl+C to stop the server")
        print("-" * 50)
        
        # Start browser opening in background thread
        browser_thread = threading.Thread(target=open_browser_after_delay)
        browser_thread.daemon = True
        browser_thread.start()
        
        app.run(debug=True, host='0.0.0.0', port=5001)
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        print("💡 Check your configuration and try again")
        sys.exit(1)

if __name__ == "__main__":
    main() 