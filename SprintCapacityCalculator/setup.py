#!/usr/bin/env python3
"""
Setup script for Sprint Capacity Calculator
Helps initialize the project with proper configuration
"""

import os
import sys
import subprocess
import shutil

def create_env_file():
    """Create .env file from template if it doesn't exist"""
    if not os.path.exists('.env'):
        if os.path.exists('env.example'):
            shutil.copy('env.example', '.env')
            print("✅ Created .env file from template")
            print("⚠️  Please edit .env file with your actual API credentials")
        else:
            print("❌ env.example file not found")
    else:
        print("ℹ️  .env file already exists")

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version {sys.version.split()[0]} is compatible")
    return True

def create_virtual_environment():
    """Create virtual environment if it doesn't exist"""
    if not os.path.exists('venv'):
        print("📦 Creating virtual environment...")
        try:
            subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
            print("✅ Virtual environment created")
        except subprocess.CalledProcessError:
            print("❌ Failed to create virtual environment")
            return False
    else:
        print("ℹ️  Virtual environment already exists")
    return True

def install_dependencies():
    """Install dependencies in virtual environment"""
    venv_python = os.path.join('venv', 'Scripts', 'python') if os.name == 'nt' else os.path.join('venv', 'bin', 'python')
    
    if not os.path.exists(venv_python):
        print("❌ Virtual environment Python not found")
        return False
    
    print("📦 Installing dependencies...")
    try:
        subprocess.run([venv_python, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
        subprocess.run([venv_python, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def print_next_steps():
    """Print instructions for next steps"""
    activate_cmd = "venv\\Scripts\\activate" if os.name == 'nt' else "source venv/bin/activate"
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Activate the virtual environment:")
    print(f"   {activate_cmd}")
    print("\n2. Edit the .env file with your API credentials:")
    print("   - Workday API credentials")
    print("   - PagerDuty API key and schedule ID")
    print("\n3. Update team configuration in config.py:")
    print("   - Edit the TEAM_DATA dictionary")
    print("   - Add your team members with their details")
    print("\n4. Run the application:")
    print("   python app.py")
    print("\n5. Open your browser to:")
    print("   http://localhost:5000")
    print("\n📖 For detailed instructions, see README.md")

def main():
    """Main setup function"""
    print("🚀 Sprint Capacity Calculator Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    if not create_virtual_environment():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Create .env file
    create_env_file()
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main() 