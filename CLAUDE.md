# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Claude Guidelines

    1. for frontend code, use TypeScript with React, run `npm run lint:fix` and `npm run type-check` after making changes and fix any linting errors
    2. if any new packages are added, update `requirements.txt` accordingly
    3. for virtual environment, use `source venv/bin/activate` before running Python commands
    4. for Python files, use `python3` to run scripts, do not add `#!/usr/bin/env python3` or `#!venv python3` shebang lines in Python files
    5. if any frontend and backend apis are updated, ensure to update the API documentation in `API.md` accordingly
    6. when dealing with API endpoints, ensure to refer to the `API.md` file for the latest endpoint definitions
    7. for every reply, maintain a `update.md` file that contains the latest updates to the codebase, including new features, bug fixes, reason for the problem, and any other relevant changes, make changes at the beginning of the file, and don't need to repeat the entire file. can be used to track the latest changes in the codebase
    8. use `npx pyright` for Python files to check for type errors
    9. `npx prettier --write .` to format frontend code and `black .` for backend Python files after made any changes

## Project Overview

This is a full-stack calorie tracking web application that allows users to upload food images for automatic calorie calculation and nutrition tracking. The application uses AI-powered food recognition to identify foods and retrieve nutritional information.

### ✨ Latest Features (Updated: 2025-01-18)

-   **🎨 Custom Notification System** - Beautiful toast notifications replacing all browser alerts
-   **✅ User Foods API Fix** - Fixed backend API for retrieving user-created custom foods
-   **🔧 Database Structure Optimization** - Removed unnecessary category dependencies
-   **📱 Responsive UI Components** - Improved mobile-friendly notification display
-   **🎯 Enhanced UX** - Smooth animations and consistent visual feedback

## Tech Stack

-   **Frontend**: React 18.2.0 with TypeScript 4.9.5
-   **Backend**: Django 4.2.16 with Django REST Framework
-   **AI/ML**: OpenAI GPT-4 Vision API for food recognition
-   **Data Source**: USDA FoodData Central API for nutrition data
-   **Authentication**: JWT tokens with refresh and blacklisting
-   **Database**: SQLite (development)

## Project Structure

```
├── frontend/               # React TypeScript application
│   ├── src/
│   │   ├── components/     # Reusable React components
│   │   │   ├── Notification.tsx         # Custom notification component
│   │   │   ├── NotificationContainer.tsx # Notification container with animations
│   │   │   ├── LoginModal.tsx           # User authentication modal
│   │   │   └── Navigation.tsx           # Main navigation bar
│   │   ├── contexts/       # React Context providers
│   │   │   ├── AuthContext.tsx          # Authentication state management
│   │   │   └── NotificationContext.tsx  # Global notification system
│   │   ├── pages/          # Page components (Dashboard, Login, etc.)
│   │   │   ├── FoodSearch.tsx           # Food search and management (public homepage)
│   │   │   ├── Dashboard.tsx            # User dashboard (login required)
│   │   │   ├── Profile.tsx              # User profile management (login required)
│   │   │   ├── Statistics.tsx           # Nutrition statistics (login required)
│   │   │   └── ApiTest.tsx              # API testing page (public)
│   │   ├── services/       # API service layer with complete implementations
│   │   │   ├── authService.ts           # Authentication API calls
│   │   │   ├── foodService.ts           # Food search and CRUD operations
│   │   │   ├── mealService.ts           # Meal tracking services
│   │   │   ├── userService.ts           # User profile management
│   │   │   ├── imageService.ts          # Image upload and recognition
│   │   │   └── statisticsService.ts     # Nutrition statistics
│   │   ├── types/          # TypeScript type definitions
│   │   │   └── api.ts                   # Complete API interface types
│   │   └── utils/          # Utility functions including HTTP client
│   │       └── api.ts                   # HTTP client with JWT authentication
│   ├── package.json        # Frontend dependencies and scripts
│   └── tsconfig.json       # TypeScript configuration
└── backend/                # Django REST API
    ├── accounts/           # User authentication and profiles
    ├── foods/              # Food database and management
    ├── meals/              # Meal tracking and summaries
    ├── images/             # Image upload and AI recognition
    ├── calorie_tracker/    # Main Django configuration
    │   ├── openai_service.py      # Centralized OpenAI API service
    │   ├── two_stage_analyzer.py  # Two-stage food analysis system
    │   └── settings.py     # Django settings with DRF and JWT
    ├── testing/            # Testing utilities and scripts
    ├── requirements.txt    # Python dependencies
    └── manage.py          # Django management script
```

## Key Architecture Components

### Two-Stage Food Analysis System

-   **Stage 1**: Fast food identification and portion estimation using OpenAI Vision API
-   **Stage 2**: Parallel USDA nutrition data retrieval for accurate nutritional information
-   Centralized OpenAI service with API key rotation and error handling

### Complete API Service Layer

The frontend has a fully implemented service layer with:

-   **Authentication**: JWT token management with automatic refresh
-   **Food Management**: Search, CRUD operations, USDA integration
-   **Meal Tracking**: Create meals, track daily intake, get summaries
-   **Image Processing**: Upload images, get AI analysis results
-   **Statistics**: Daily/weekly/monthly nutrition summaries

### Django Apps Architecture

-   **accounts**: User authentication, profiles, activity logging
-   **foods**: Food database, categories, search with USDA integration
-   **meals**: Meal tracking, daily summaries, statistics
-   **images**: Image upload and OpenAI-powered food recognition

## Common Development Commands

### Frontend Commands

```bash
cd frontend
npm install                   # Install dependencies
npm start                     # Start development server (localhost:3000)
npm run build                 # Build for production
npm test                      # Run tests
npm run type-check            # TypeScript type checking
npm run lint                  # ESLint code checking
npm run lint:fix              # Fix linting errors automatically
```

### Backend Commands

```bash
cd backend
source venv/bin/activate            # Activate virtual environment
pip install -r requirements.txt     # Install dependencies
python manage.py runserver          # Start development server (localhost:8000)
python manage.py migrate            # Run database migrations
python manage.py makemigrations     # Create new migrations
python manage.py test               # Run Django tests
python manage.py createsuperuser    # Create admin user
```

## Environment Configuration

````

### API Configuration

-   **OpenAI**: GPT-4 Vision API for food recognition
-   **USDA**: FoodData Central API for nutrition data (optional, 1000 requests/hour)
-   **Django**: JWT authentication with 1-hour access tokens, 7-day refresh tokens

## Key Features Implementation Status

-   **Complete Frontend API Integration** - All services implemented with TypeScript
-   **JWT Authentication** - Secure token-based auth with refresh and blacklisting
-   **Image Recognition** - Two-stage food analysis with OpenAI Vision API
-   **USDA Integration** - Real nutrition data from USDA FoodData Central
-   **Food Management** - Complete CRUD operations with search and categories
-   **Meal Tracking** - Daily meal creation and nutrition summaries
-   **Statistics** - Daily/weekly/monthly nutrition tracking
-   **OpenAI Service** - Centralized API management with key rotation

## Development Guidelines

1. **Code Style**: Use tabs for indentation (both frontend and backend)
2. **TypeScript**: Strict typing enforced, run `npm run type-check` before commits
3. **Linting**: Run `npm run lint` after frontend changes, fix all errors
4. **Testing**: Backend has comprehensive test commands, frontend uses Jest + React Testing Library
5. **API Keys**: Store in environment variables, never commit to code
6. **Error Handling**: Comprehensive error handling implemented in both OpenAI service and API clients

## Important Notes for Claude Code

### Current Backend Status ✅ FULLY OPERATIONAL

All Django apps are **ENABLED** and fully functional:

-   ✅ `meals` app - **ACTIVE** - Complete meal tracking and nutrition summaries
-   ✅ `images` app - **ACTIVE** - Image upload and AI-powered food recognition
-   ✅ `rest_framework_simplejwt` - **ACTIVE** - JWT authentication with token blacklisting
-   ✅ All API endpoints documented in `API.md` are **LIVE** and operational

### API Documentation Status

-   **API.md** - ✅ **UP TO DATE** - Accurately reflects all current backend endpoints
-   **Complete API Coverage** - All documented endpoints match implementation
-   **Production Ready** - Full authentication, CRUD operations, AI integration

## Production Considerations

-   **Database**: Migrate from SQLite to PostgreSQL for production
-   **Security**: Use HTTPS, configure proper CORS origins, rate limiting
-   **Scaling**: Consider Redis for caching, multiple OpenAI keys for higher limits
-   **Monitoring**: Logging configured, add monitoring for OpenAI API usage
-   **Deployment**: Use gunicorn for Django, proper static file serving

## Troubleshooting

1. **Dependency Issues**: Run `./install_deps.sh` for automated dependency resolution
2. **OpenAI API**: Check API key configuration and billing status
3. **USDA API**: Optional but recommended for accurate nutrition data
4. **CORS**: Ensure frontend origin is in CORS_ALLOWED_ORIGINS
5. **JWT**: Tokens expire after 1 hour, refresh tokens last 7 days

## Current Implementation Status

### ✅ Backend Status - FULLY OPERATIONAL

-   **All Django Apps Active**: meals, images, accounts, foods
-   **JWT Authentication**: Fully functional with token blacklisting
-   **OpenAI Integration**: Two-stage food analysis system operational
-   **USDA Integration**: Real nutrition data lookup active
-   **Database**: All migrations applied, models fully functional
-   **API Endpoints**: All documented endpoints in API.md are live
-   **🔧 User Foods API Fixed**: Resolved category field dependency issues in get_user_foods endpoint
-   **🛠️ Database Optimization**: Removed unnecessary category relationships for simplified food model

### ✅ Frontend Status - FULLY OPERATIONAL

-   **Login Modal System**: Complete login/register modal with tab switching
-   **Food Search as Homepage**: Public food search functionality as the main entry point
-   **Flexible Authentication**: Unauthenticated users can browse and search foods
-   **Login Required Actions**: Smart login prompts for protected operations (meal tracking, profile, stats)
-   **Navigation Integration**: Dynamic login/logout button and protected menu items with visual indicators
-   **All Pages Updated**: Dashboard (login-only), FoodSearch (public), Profile (login-only), Statistics (login-only), ApiTest (public)
-   **Error Handling**: Comprehensive error handling and user feedback
-   **🎨 Custom Notification System**: Beautiful toast notifications completely replace browser alerts/confirms
-   **📱 Responsive Design**: Mobile-optimized notification display with smooth animations
-   **✨ Enhanced UX**: Consistent visual feedback across all user interactions

### ✅ API Documentation Status

-   **API.md**: Accurately reflects current backend implementation
-   **Endpoint Coverage**: 100% match between docs and implementation
-   **Authentication**: JWT flow documented and working
-   **Response Formats**: Standardized across all endpoints

### ✅ Available Features (Production Ready)

1. **User Management**: Registration, login, profile management
2. **Food Database**: Search, CRUD, USDA integration, custom foods with fixed user foods API
3. **Meal Tracking**: Create meals, nutrition summaries, daily tracking
4. **Image Recognition**: Upload images, AI food analysis, portion estimation
5. **Statistics**: Daily/weekly/monthly nutrition tracking
6. **OpenAI Service**: Centralized API management with key rotation
7. **Flexible Authentication**: Browse without login, login when needed
8. **🎨 Custom Notification System**: Toast notifications with 4 types (success, error, warning, info)
9. **📱 Responsive UI**: Mobile-optimized components with smooth animations
10. **🛠️ Enhanced API Reliability**: Fixed database relationships and optimized queries

### 🔧 Quick Verification Commands

```bash
# Verify backend status
cd backend && python manage.py runserver

# Test authentication
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'

# Test food search
curl -X GET "http://localhost:8000/api/v1/foods/search/?query=apple" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test user foods API (fixed)
curl -X GET "http://localhost:8000/api/v1/foods/user/" \
  -H "Authorization: Bearer YOUR_TOKEN"
````

The codebase is production-ready with complete frontend-backend integration, AI-powered food recognition, comprehensive nutrition tracking capabilities, and modern UI/UX features including custom notifications.
