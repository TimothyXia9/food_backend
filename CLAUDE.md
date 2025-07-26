# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Claude Guidelines

    1. use tabs for indentation instead of spaces
    2. for frontend code, use TypeScript with React, run `npm run lint` after making changes and fix any linting errors
    3. update CLAUDE.md with any new features or changes to the project structure
    4. if any new packages are added, update `requirements.txt` accordingly
    5. for virtual environment, use `source venv/bin/activate` before running Python commands
    6. for Python files, use `python3` to run scripts, do not add `#!/usr/bin/env python3` or `#!venv python3` shebang lines in Python files

## Project Overview

This is a calorie tracking web application where users can upload images or text to calculate calories and record dietary information. The project uses:

- **Frontend**: React
- **Backend**: Python Django

## Key Features

- Upload images or text to record dietary information
- Automatic food recognition and calorie calculation
- Historical records and statistics viewing
- Custom food uploads and modifications
- User registration and login system

## Project Structure

The frontend React application with TypeScript is implemented with the following structure:

- **Frontend React application** - User interface with complete API integration
- **Backend Django application** - Data processing and business logic (implemented)
- **Image processing and food recognition** - API endpoints defined
- **User authentication and data management** - Full service layer implemented

### Frontend Structure

```
src/
├── components/          # React components
├── pages/              # Page components (Dashboard, Login, etc.)
├── services/           # API service layer
│   ├── authService.ts  # Authentication services
│   ├── userService.ts  # User profile management
│   ├── foodService.ts  # Food search and management
│   ├── mealService.ts  # Meal tracking services
│   ├── statisticsService.ts # Statistics and summary
│   ├── imageService.ts # Image upload and recognition
│   └── index.ts        # Service exports
├── types/              # TypeScript type definitions
│   └── api.ts          # API interface types
├── utils/              # Utility functions
│   └── api.ts          # HTTP client and API configuration
└── ...
```

## Environment Setup

### Prerequisites

- Node.js 18+ and npm
- Python 3.12+ and pip
- OpenAI API Key(s) (required for image recognition features)
- USDA FoodData Central API Key (optional, for enhanced food nutrition data)

### Frontend Setup (React + TypeScript)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

### Backend Setup (Django)

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (if not exists)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (required for image recognition)
# Create .env file for OpenAI API key(s):
# For single API key:
# echo "OPENAI_API_KEY=your-api-key-here" > .env
# For multiple API keys (recommended for production):
# echo 'OPENAI_API_KEYS=["key1", "key2", "key3"]' > .env
# For USDA FoodData Central API (optional):
# echo "USDA_API_KEY=your-usda-api-key-here" >> .env

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

## Project Startup

### Start Both Services

```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
python manage.py runserver

# Terminal 2 - Frontend
cd frontend
npm start
```

### Access URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

## Development Commands

### Frontend Commands

- `npm start` - Start React development server
- `npm test` - Run React tests
- `npm run build` - Build React for production
- `npm test -- --watchAll=false` - Run tests once

### Backend Commands

- `python manage.py runserver` - Start Django development server
- `python manage.py migrate` - Run database migrations
- `python manage.py makemigrations` - Create new migrations
- `python manage.py test` - Run Django tests
- `python manage.py createsuperuser` - Create admin user

### Testing & Development Scripts

- `cd testing && python test_image_recognition.py` - Test OpenAI image recognition (legacy)
- `cd testing && python test_usda_nutrition.py` - Test USDA nutrition data
- `cd testing && python test_async_performance.py` - Test async performance
- `python manage.py test_openai_service --image path/to/image.jpg` - Test new OpenAI service
- `python manage.py test_openai_service --test-chat` - Test basic chat completion
- `python manage.py test_openai_service --test-vision --image path/to/image.jpg` - Test vision completion
- `python manage.py test_openai_service --test-analyzer --image path/to/image.jpg` - Test two-stage food analyzer

## Frontend API Implementation

The frontend includes complete API service layer implementation:

### Available Services

1. **Authentication Service** (`authService`)
   - User registration and login
   - JWT token management
   - Automatic token refresh
   - Logout functionality

2. **User Service** (`userService`)
   - Get user profile information
   - Update user profile and preferences

3. **Food Service** (`foodService`)
   - Search food database
   - Get detailed food information
   - Create and manage custom foods
   - Food category management

4. **Meal Service** (`mealService`)
   - Create and manage meals
   - Add/remove foods from meals
   - Track daily meal intake

5. **Statistics Service** (`statisticsService`)
   - Daily calorie summaries
   - Weekly and monthly statistics
   - Weight tracking
   - Nutrition trends

6. **Image Service** (`imageService`)
   - Upload food images
   - Food recognition results
   - Search history management

### Usage Example

```typescript
import { authService, foodService, mealService } from "./services";

// Login user
await authService.login({ username: "user", password: "pass" });

// Search for foods
const foods = await foodService.searchFoods({ q: "apple" });

// Create a meal
await mealService.createMeal({
  date: "2024-01-15",
  meal_type: "breakfast",
  name: "Morning Meal",
  foods: [{ food_id: 1, quantity: 150 }],
});
```

### Backend Structure

```
backend/
├── accounts/               # User authentication & profiles
│   ├── models.py          # User, UserProfile, UserActivityLog
│   ├── serializers.py     # API serializers
│   ├── views.py           # Authentication views
│   └── urls.py            # Auth endpoints
├── foods/                 # Food database & management
│   ├── models.py          # Food, FoodCategory, FoodAlias
│   ├── views.py           # Food CRUD operations
│   └── urls.py            # Food endpoints
├── meals/                 # Meal tracking & summaries
│   ├── models.py          # Meal, MealFood, DailySummary
│   ├── views.py           # Meal tracking views
│   └── urls.py            # Meal endpoints
├── images/                # Image upload & recognition
│   ├── models.py          # UploadedImage, FoodRecognitionResult
│   ├── views.py           # Image processing views
│   └── urls.py            # Image endpoints
├── calorie_tracker/       # Main Django configuration
│   ├── settings.py        # Django settings with DRF & JWT
│   └── urls.py            # Main URL routing
├── media/                 # User uploaded files
├── testing/               # Test scripts and utilities
│   ├── test_image_recognition.py # OpenAI image recognition testing
│   ├── test_usda_nutrition.py   # USDA API integration tests
│   ├── test_images/       # Sample images for testing
│   └── README.md          # Testing documentation
├── requirements.txt       # Python dependencies
└── manage.py              # Django management script
```

## Backend API Implementation

### Django Apps Architecture

- **accounts** - User authentication, profiles, and activity logging
- **foods** - Food database, categories, and search functionality
- **meals** - Meal tracking, daily summaries, and statistics
- **images** - Image upload and OpenAI-powered food recognition

### Implemented APIs ✅

#### Authentication APIs

- `POST /api/v1/auth/register` - User registration with JWT tokens
- `POST /api/v1/auth/login` - User login with JWT authentication
- `POST /api/v1/auth/refresh` - JWT token refresh
- `POST /api/v1/auth/logout` - Secure logout with token blacklisting

#### User Profile APIs

- `GET /api/v1/users/profile` - Get user profile with health data
- `PUT /api/v1/users/profile` - Update user profile and preferences

### Backend Features ✅

- **JWT Authentication** - Secure token-based authentication with blacklisting
- **Custom User Model** - Extended user model with profiles
- **Activity Logging** - Track user activities for security and analytics
- **CORS Configuration** - Ready for frontend integration
- **Standard API Responses** - Consistent response format across all endpoints
- **Database Models** - Complete schema implementation based on requirements
- **Migrations** - All database tables created and configured

### API Response Format

```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com",
      "profile": {
        "height": 175.5,
        "weight": 70.0,
        "daily_calorie_goal": 2000
      }
    },
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  },
  "message": "Login successful"
}
```

## OpenAI Service Architecture

The project now uses a centralized OpenAI service for better API key management and reliability:

### Features

- **Centralized API Management** - Single service for all OpenAI requests
- **API Key Rotation** - Automatic rotation between multiple API keys
- **Error Handling** - Comprehensive error handling with retry logic
- **Rate Limit Management** - Automatic handling of rate limits
- **Function Calling Support** - Complete support for OpenAI function calling
- **Vision API Support** - Image analysis capabilities
- **Async Operations** - Full async support for better performance

### Service Structure

```
calorie_tracker/
├── openai_service.py       # Centralized OpenAI service
└── two_stage_analyzer.py   # Refactored food analyzer using OpenAI service
```

### Usage

```python
from calorie_tracker.openai_service import get_openai_service

# Get service instance
service = get_openai_service()

# Chat completion
result = await service.chat_completion(
    messages=[{"role": "user", "content": "Hello"}]
)

# Vision completion
result = await service.vision_completion(
    image_path="path/to/image.jpg",
    prompt="What do you see?"
)

# Function calling
result = await service.function_calling_completion(
    messages=messages,
    functions=function_definitions
)
```

### Configuration

The service supports multiple configuration options:

```bash
# Single API key
OPENAI_API_KEY=your-api-key

# Multiple API keys (JSON array)
OPENAI_API_KEYS=["key1", "key2", "key3"]

# USDA API key (optional)
USDA_API_KEY=your-usda-key
```

## Architecture Notes

Current implementation status:

1. ✅ **Frontend API Layer** - Complete TypeScript service layer
2. ✅ **Type Definitions** - Full API interface types
3. ✅ **HTTP Client** - Configured with authentication
4. ✅ **Backend Django API** - Complete REST API implementation
5. ✅ **Database Models** - Complete schema with all relationships
6. ✅ **JWT Authentication** - Secure authentication with token management
7. ✅ **Food Management APIs** - Complete with USDA integration
8. ✅ **Meal Tracking APIs** - Complete implementation
9. ✅ **Statistics APIs** - Complete implementation
10. ✅ **Image Processing APIs** - Complete two-stage food analysis
11. ✅ **OpenAI Service** - Centralized API management with key rotation
12. ✅ **USDA Integration** - Real nutrition data from USDA FoodData Central

## Quick Start Guide

### Option A: One-Command Setup (Recommended)

```bash
# Navigate to backend directory
cd backend

# Run the quick start script
./start_dev.sh
```

This script will:

- Create virtual environment
- Install dependencies
- Set up .env file template
- Run migrations
- Test OpenAI service
- Start the development server

### Option B: Manual Setup

#### 1. Environment Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env  # Create .env file from template
# Edit .env file with your API keys (see .env.example for all options)
# Required:
# OPENAI_API_KEY=your-openai-key
# or for multiple keys (recommended):
# OPENAI_API_KEYS=["key1", "key2", "key3"]
# Optional but recommended:
# USDA_API_KEY=your-usda-key
```

#### 2. Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

#### 3. Start Backend Services

```bash
# Start Django development server
python manage.py runserver

# Backend will run on: http://localhost:8000
# Admin interface: http://localhost:8000/admin
# API base URL: http://localhost:8000/api/v1
```

### Common Tasks

#### 4. Test OpenAI Integration

```bash
# Test basic OpenAI service
python manage.py test_openai_service --test-chat

# Test image analysis (requires test image)
python manage.py test_openai_service --test-vision --image testing/test_images/your_image.jpg

# Test complete food analyzer
python manage.py test_openai_service --test-analyzer --image testing/test_images/your_image.jpg

# Run full test suite
python manage.py test_openai_service --image testing/test_images/your_image.jpg
```

#### 5. Test API Endpoints

```bash
# Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"testpass123"}'

# Login to get JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'

# Use the token for authenticated requests
TOKEN="your-jwt-token-here"

# Search foods
curl -X GET "http://localhost:8000/api/v1/foods/search?query=apple" \
  -H "Authorization: Bearer $TOKEN"

# Upload image for analysis
curl -X POST http://localhost:8000/api/v1/images/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "image=@path/to/your/image.jpg"
```

#### 6. Start Frontend (Optional)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Frontend will run on: http://localhost:3000
```

#### 7. Production Deployment

```bash
# Install production dependencies
pip install gunicorn

# Collect static files
python manage.py collectstatic

# Run with Gunicorn
gunicorn calorie_tracker.wsgi:application --bind 0.0.0.0:8000
```

## Complete Usage Workflow

### 1. Image-Based Food Analysis

```bash
# 1. Upload an image
curl -X POST http://localhost:8000/api/v1/images/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "image=@food_image.jpg"

# Response: {"success": true, "data": {"id": 1, ...}}

# 2. Analyze the image
curl -X POST http://localhost:8000/api/v1/images/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"image_id": 1}'

# 3. Get analysis results
curl -X GET http://localhost:8000/api/v1/images/1/results \
  -H "Authorization: Bearer $TOKEN"

# 4. Confirm recognized foods
curl -X POST http://localhost:8000/api/v1/images/confirm \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"result_id": 1, "is_confirmed": true}'

# 5. Create meal from image
curl -X POST http://localhost:8000/api/v1/images/create-meal \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"image_id": 1, "meal_type": "breakfast", "date": "2024-01-15"}'
```

### 2. Manual Food Tracking

```bash
# 1. Search for foods
curl -X GET "http://localhost:8000/api/v1/foods/search?query=chicken breast" \
  -H "Authorization: Bearer $TOKEN"

# 2. Create a meal
curl -X POST http://localhost:8000/api/v1/meals/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2024-01-15",
    "meal_type": "lunch",
    "name": "Healthy Lunch",
    "foods": [
      {"food_id": 1, "quantity": 200},
      {"food_id": 2, "quantity": 150}
    ]
  }'

# 3. Get daily summary
curl -X GET "http://localhost:8000/api/v1/meals/daily-summary?date=2024-01-15" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. USDA Food Integration

```bash
# 1. Search USDA database
curl -X GET "http://localhost:8000/api/v1/foods/usda/search?query=apple" \
  -H "Authorization: Bearer $TOKEN"

# 2. Get nutrition details
curl -X GET "http://localhost:8000/api/v1/foods/usda/nutrition/1102702" \
  -H "Authorization: Bearer $TOKEN"

# 3. Create food from USDA
curl -X POST http://localhost:8000/api/v1/foods/usda/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fdc_id": 1102702}'
```

## Troubleshooting

### Common Issues

#### 0. Dependencies Installation Issues

**Problem**: `aiohttp` compilation fails with "Failed building wheel for aiohttp"

**Solutions**:

For **Ubuntu/Debian**:

```bash
# Install build tools and dependencies
sudo apt-get update
sudo apt-get install -y build-essential python3-dev libffi-dev libssl-dev

# Upgrade pip and install wheel
pip install --upgrade pip setuptools wheel

# Try installing again
pip install -r requirements.txt
```

For **CentOS/RHEL**:

```bash
# Install build tools
sudo yum install -y gcc gcc-c++ python3-devel libffi-devel openssl-devel

# Upgrade pip and install wheel
pip install --upgrade pip setuptools wheel

# Try installing again
pip install -r requirements.txt
```

For **macOS**:

```bash
# Install Xcode command line tools
xcode-select --install

# Install dependencies via Homebrew
brew install libffi openssl

# Upgrade pip and install wheel
pip install --upgrade pip setuptools wheel

# Try installing again
pip install -r requirements.txt
```

For **Windows**:

```bash
# Install Microsoft C++ Build Tools
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Upgrade pip and install wheel
pip install --upgrade pip setuptools wheel

# Try installing again
pip install -r requirements.txt
```

**Alternative solution**: Use pre-compiled wheels

```bash
# Install aiohttp separately with pre-compiled wheel
pip install --only-binary=aiohttp aiohttp

# Then install other dependencies
pip install -r requirements.txt
```

**Automated solution**: Use the dependency installation script

```bash
# Run the automated dependency installer
./install_deps.sh

# This script will:
# - Detect your OS and install system dependencies
# - Try multiple installation strategies
# - Handle common compilation issues
# - Provide detailed error messages
```

#### 1. OpenAI API Key Issues

```bash
# Check if API key is configured
python manage.py shell
>>> from calorie_tracker.openai_service import get_openai_service
>>> service = get_openai_service()
>>> service.get_usage_stats()
```

**Solutions:**

- Ensure `.env` file contains valid OpenAI API key
- For multiple keys: `OPENAI_API_KEYS=["key1", "key2"]`
- Check API key permissions and billing status

#### 2. Image Analysis Fails

```bash
# Test image analysis step by step
python manage.py test_openai_service --test-vision --image path/to/image.jpg
```

**Solutions:**

- Check image format (JPG, PNG supported)
- Verify image file size (max 10MB)
- Ensure image contains food items
- Check OpenAI API quota

#### 3. Database Migration Issues

```bash
# Reset migrations if needed
python manage.py migrate --fake-initial
python manage.py migrate
```

#### 4. USDA API Issues

```bash
# Test USDA connection
cd testing
python test_usda_nutrition.py
```

**Solutions:**

- USDA API key is optional but recommended
- Check USDA API rate limits
- Verify network connectivity

#### 5. CORS Issues (Frontend Integration)

```python
# In settings.py, ensure CORS is configured
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

### Debug Mode

```bash
# Enable debug logging
export DJANGO_DEBUG=True
python manage.py runserver

# Check logs
tail -f logs/django.log
```

### Performance Optimization

```bash
# Use Redis for caching (optional)
pip install redis django-redis

# Configure in settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

## API Rate Limits

| Service               | Limit           | Notes                                   |
| --------------------- | --------------- | --------------------------------------- |
| OpenAI API            | Depends on plan | Use multiple keys for higher limits     |
| USDA FoodData Central | 1000/hour       | Free tier limit                         |
| Django API            | No limit        | Can be configured with django-ratelimit |

## Security Considerations

1. **API Keys**: Store in environment variables, never in code
2. **JWT Tokens**: Set appropriate expiration times
3. **File Uploads**: Validate file types and sizes
4. **Rate Limiting**: Implement for production use
5. **HTTPS**: Always use HTTPS in production

## Monitoring and Logging

```python
# Add to settings.py for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```
