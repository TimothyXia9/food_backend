#!/bin/bash

# Quick Start Script for Calorie Tracker Backend
# This script sets up and starts the development environment

echo "🚀 Starting Calorie Tracker Backend Development Environment"
echo "============================================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies using the dedicated script
echo "🔧 Installing system and Python dependencies..."
./install_deps.sh

# Check if installation was successful
if [ $? -ne 0 ]; then
    echo "❌ Dependency installation failed. Please check the errors above."
    echo "💡 You can also try running: ./install_deps.sh"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚙️  Setting up environment variables..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API keys before running the server!"
    echo "   Required: OPENAI_API_KEY or OPENAI_API_KEYS"
    echo "   Optional: USDA_API_KEY"
    echo ""
    read -p "Press Enter to continue once you've configured .env file..."
fi

# Run migrations
echo "🗄️  Running database migrations..."
python manage.py migrate

# Check if superuser exists
echo "👤 Checking for superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print('No superuser found. You can create one later with: python manage.py createsuperuser')
"

# Test OpenAI service
echo "🤖 Testing OpenAI service..."
python manage.py test_openai_service --test-chat || echo "⚠️  OpenAI service test failed. Check your API key configuration."

# Create logs directory
mkdir -p logs

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Starting Django development server..."
echo "   Backend will be available at: http://localhost:8000"
echo "   Admin interface: http://localhost:8000/admin"
echo "   API base URL: http://localhost:8000/api/v1"
echo ""
echo "📋 Useful commands:"
echo "   Test OpenAI: python manage.py test_openai_service --test-chat"
echo "   Create superuser: python manage.py createsuperuser"
echo "   Run tests: python manage.py test"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python manage.py runserver