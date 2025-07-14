#!/bin/bash

# Dependency Installation Script for Calorie Tracker Backend
# This script handles common installation issues

echo "🔧 Installing system dependencies and Python packages"
echo "=================================================="

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if command -v apt-get &> /dev/null; then
        OS="ubuntu"
    elif command -v yum &> /dev/null; then
        OS="centos"
    elif command -v dnf &> /dev/null; then
        OS="fedora"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    OS="windows"
fi

echo "🖥️  Detected OS: $OS"

# Install system dependencies
case $OS in
    ubuntu)
        echo "📦 Installing system dependencies for Ubuntu/Debian..."
        sudo apt-get update
        sudo apt-get install -y \
            build-essential \
            python3-dev \
            python3-pip \
            python3-venv \
            libffi-dev \
            libssl-dev \
            libyaml-dev \
            libxml2-dev \
            libxslt1-dev \
            zlib1g-dev \
            libjpeg-dev \
            libpng-dev \
            git
        ;;
    centos)
        echo "📦 Installing system dependencies for CentOS/RHEL..."
        sudo yum install -y \
            gcc \
            gcc-c++ \
            python3-devel \
            python3-pip \
            libffi-devel \
            openssl-devel \
            libyaml-devel \
            libxml2-devel \
            libxslt-devel \
            zlib-devel \
            libjpeg-devel \
            libpng-devel \
            git
        ;;
    fedora)
        echo "📦 Installing system dependencies for Fedora..."
        sudo dnf install -y \
            gcc \
            gcc-c++ \
            python3-devel \
            python3-pip \
            libffi-devel \
            openssl-devel \
            libyaml-devel \
            libxml2-devel \
            libxslt-devel \
            zlib-devel \
            libjpeg-devel \
            libpng-devel \
            git
        ;;
    macos)
        echo "📦 Installing system dependencies for macOS..."
        # Check if Homebrew is installed
        if ! command -v brew &> /dev/null; then
            echo "🍺 Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        
        # Install Xcode command line tools
        if ! command -v gcc &> /dev/null; then
            echo "🔨 Installing Xcode command line tools..."
            xcode-select --install
        fi
        
        # Install dependencies via Homebrew
        brew install libffi openssl libyaml libxml2 libxslt zlib jpeg libpng git
        ;;
    windows)
        echo "🪟 For Windows, please install:"
        echo "  1. Microsoft C++ Build Tools from:"
        echo "     https://visualstudio.microsoft.com/visual-cpp-build-tools/"
        echo "  2. Python 3.8+ from https://python.org"
        echo "  3. Git from https://git-scm.com"
        echo ""
        echo "Then run this script again."
        ;;
    *)
        echo "⚠️  Unknown OS. Please install build tools manually:"
        echo "  - C/C++ compiler (gcc/clang)"
        echo "  - Python development headers"
        echo "  - OpenSSL development headers"
        echo "  - libffi development headers"
        ;;
esac

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment detected: $VIRTUAL_ENV"
else
    echo "⚠️  No virtual environment detected. Creating one..."
    python3 -m venv venv
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
fi

# Upgrade pip and install build tools
echo "🔄 Upgrading pip and installing build tools..."
python -m pip install --upgrade pip
pip install --upgrade setuptools wheel build

# Install Python dependencies with error handling
echo "📚 Installing Python dependencies..."

# Try to install dependencies with different strategies
INSTALL_SUCCESS=false

# Strategy 1: Normal installation
echo "🔄 Attempting normal installation..."
if pip install -r requirements.txt; then
    INSTALL_SUCCESS=true
    echo "✅ Normal installation successful!"
else
    echo "❌ Normal installation failed, trying alternatives..."
    
    # Strategy 2: Install problematic packages separately
    echo "🔄 Installing problematic packages separately..."
    if pip install --only-binary=aiohttp aiohttp && \
       pip install --only-binary=multidict multidict && \
       pip install --only-binary=yarl yarl && \
       pip install -r requirements.txt; then
        INSTALL_SUCCESS=true
        echo "✅ Separate installation successful!"
    else
        echo "❌ Separate installation failed, trying no-binary..."
        
        # Strategy 3: Force compilation with no-binary
        echo "🔄 Force compilation with no-binary..."
        if pip install --no-binary=aiohttp,multidict,yarl -r requirements.txt; then
            INSTALL_SUCCESS=true
            echo "✅ Force compilation successful!"
        else
            echo "❌ Force compilation failed, trying conda..."
            
            # Strategy 4: Try conda if available
            if command -v conda &> /dev/null; then
                echo "🔄 Trying conda installation..."
                conda install -c conda-forge aiohttp
                if pip install -r requirements.txt; then
                    INSTALL_SUCCESS=true
                    echo "✅ Conda installation successful!"
                fi
            fi
        fi
    fi
fi

if [ "$INSTALL_SUCCESS" = true ]; then
    echo ""
    echo "✅ Dependencies installed successfully!"
    echo "🚀 You can now run: python manage.py runserver"
else
    echo ""
    echo "❌ Installation failed. Please check the errors above."
    echo "💡 Try these manual steps:"
    echo "   1. pip install --upgrade pip setuptools wheel"
    echo "   2. pip install --only-binary=aiohttp aiohttp"
    echo "   3. pip install -r requirements.txt"
    echo ""
    echo "📝 For more help, check the troubleshooting section in CLAUDE.md"
fi

# Show installed packages
echo ""
echo "📦 Installed packages:"
pip list | grep -E "(aiohttp|django|openai|pillow)"