#!/bin/bash

# Quick fix script for aiohttp installation issues
echo "🔧 Fixing aiohttp installation issues..."
echo "===================================="

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
fi

# Method 1: Upgrade pip and try again
echo "🔄 Method 1: Upgrading pip and build tools..."
python -m pip install --upgrade pip setuptools wheel

# Method 2: Install aiohttp with pre-compiled wheel
echo "🔄 Method 2: Installing aiohttp with pre-compiled wheel..."
pip install --only-binary=aiohttp aiohttp

# Method 3: Install related packages separately
echo "🔄 Method 3: Installing related packages..."
pip install --only-binary=multidict multidict
pip install --only-binary=yarl yarl
pip install --only-binary=aiosignal aiosignal
pip install --only-binary=frozenlist frozenlist

# Method 4: Try installing all requirements
echo "🔄 Method 4: Installing all requirements..."
if pip install -r requirements.txt; then
    echo "✅ All dependencies installed successfully!"
else
    echo "❌ Still having issues. Let's try a different approach..."
    
    # Method 5: Create a minimal requirements file
    echo "🔄 Method 5: Creating minimal requirements..."
    cat > requirements_minimal.txt << EOF
Django==4.2.16
djangorestframework==3.16.0
djangorestframework-simplejwt==5.3.0
python-decouple==3.8
django-cors-headers==4.5.0
pillow==11.3.0
requests==2.31.0
python-dotenv==1.0.0
openai==1.57.4
EOF
    
    # Install minimal requirements first
    if pip install -r requirements_minimal.txt; then
        echo "✅ Minimal requirements installed!"
        
        # Now try aiohttp again
        echo "🔄 Trying aiohttp installation again..."
        if pip install aiohttp; then
            echo "✅ aiohttp installed successfully!"
        else
            echo "❌ aiohttp still failing. Trying alternative approaches..."
            
            # Try with conda if available
            if command -v conda &> /dev/null; then
                echo "🔄 Trying conda installation..."
                conda install -c conda-forge aiohttp
            else
                echo "💡 Please try installing aiohttp manually:"
                echo "   pip install --no-deps aiohttp"
                echo "   Or consider using conda: conda install -c conda-forge aiohttp"
            fi
        fi
    else
        echo "❌ Even minimal requirements failed. Please check your Python installation."
    fi
fi

# Show final status
echo ""
echo "📦 Current aiohttp status:"
python -c "import aiohttp; print(f'aiohttp version: {aiohttp.__version__}')" 2>/dev/null || echo "❌ aiohttp not installed"

echo ""
echo "🔍 Troubleshooting tips:"
echo "1. Make sure you have build tools installed"
echo "2. Try using Python 3.8-3.11 (newer versions may have issues)"
echo "3. Consider using conda instead of pip for aiohttp"
echo "4. Check if you're using the correct virtual environment"