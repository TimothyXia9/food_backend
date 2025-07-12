# API Documentation

## Overview

This document outlines the RESTful API design for the calorie tracking web application. The API follows REST principles and uses JSON for data exchange.

## Base URL

- Development: `http://localhost:8000/api/v1`
- Production: `https://api.calotracker.com/v1`

## Authentication

All protected endpoints require authentication via JWT tokens.

### Headers
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

## Response Format

### Success Response
```json
{
  "success": true,
  "data": {...},
  "message": "Success message"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description",
    "details": {}
  }
}
```

## API Endpoints

### 1. Authentication

#### Register User
```
POST /auth/register
```

**Request Body:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "nickname": "string"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com",
      "nickname": "John"
    },
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

#### Login
```
POST /auth/login
```

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com",
      "nickname": "John"
    },
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

#### Refresh Token
```
POST /auth/refresh
```

**Request Body:**
```json
{
  "refresh_token": "string"
}
```

#### Logout
```
POST /auth/logout
```

### 2. User Profile

#### Get User Profile
```
GET /users/profile
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com",
      "nickname": "John"
    },
    "profile": {
      "date_of_birth": "1990-01-01",
      "gender": "Male",
      "height": 175.5,
      "weight": 70.0,
      "daily_calorie_goal": 2000
    }
  }
}
```

#### Update User Profile
```
PUT /users/profile
```

**Request Body:**
```json
{
  "nickname": "string",
  "date_of_birth": "1990-01-01",
  "gender": "Male",
  "height": 175.5,
  "weight": 70.0,
  "daily_calorie_goal": 2000
}
```

### 3. Food Management

#### Search Foods
```
GET /foods/search?q=<query>&category=<category_id>&limit=<limit>&offset=<offset>
```

**Query Parameters:**
- `q`: Search query (required)
- `category`: Filter by category ID (optional)
- `limit`: Number of results (default: 20)
- `offset`: Pagination offset (default: 0)

**Response:**
```json
{
  "success": true,
  "data": {
    "foods": [
      {
        "id": 1,
        "name": "Apple",
        "category": {
          "id": 1,
          "name": "Fruits"
        },
        "brand": null,
        "serving_size": 100,
        "calories_per_100g": 52,
        "protein_per_100g": 0.3,
        "fat_per_100g": 0.2,
        "carbs_per_100g": 14,
        "fiber_per_100g": 2.4,
        "sugar_per_100g": 10,
        "sodium_per_100g": 1,
        "is_custom": false,
        "created_by": null
      }
    ],
    "total": 1,
    "has_next": false
  }
}
```

#### Get Food Details
```
GET /foods/{food_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Apple",
    "category": {
      "id": 1,
      "name": "Fruits"
    },
    "brand": null,
    "barcode": null,
    "serving_size": 100,
    "calories_per_100g": 52,
    "protein_per_100g": 0.3,
    "fat_per_100g": 0.2,
    "carbs_per_100g": 14,
    "fiber_per_100g": 2.4,
    "sugar_per_100g": 10,
    "sodium_per_100g": 1,
    "is_custom": false,
    "created_by": null,
    "aliases": ["红苹果", "苹果"]
  }
}
```

#### Create Custom Food
```
POST /foods
```

**Request Body:**
```json
{
  "name": "My Custom Salad",
  "category_id": 1,
  "brand": "Homemade",
  "serving_size": 100,
  "calories_per_100g": 120,
  "protein_per_100g": 8.5,
  "fat_per_100g": 6.0,
  "carbs_per_100g": 15.0,
  "fiber_per_100g": 3.0,
  "sugar_per_100g": 2.0,
  "sodium_per_100g": 200,
  "aliases": ["自制沙拉", "蔬菜沙拉"]
}
```

#### Update Custom Food
```
PUT /foods/{food_id}
```

**Request Body:** (Same as create)

#### Delete Custom Food
```
DELETE /foods/{food_id}
```

#### Get Food Categories
```
GET /foods/categories
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Fruits",
      "description": "Fresh and dried fruits"
    },
    {
      "id": 2,
      "name": "Vegetables",
      "description": "Fresh and cooked vegetables"
    }
  ]
}
```

### 4. Meal Tracking

#### Get Meals by Date
```
GET /meals?date=<YYYY-MM-DD>&meal_type=<type>
```

**Query Parameters:**
- `date`: Target date (default: today)
- `meal_type`: Filter by meal type (optional)

**Response:**
```json
{
  "success": true,
  "data": {
    "date": "2024-01-15",
    "meals": [
      {
        "id": 1,
        "meal_type": "breakfast",
        "name": "Morning Breakfast",
        "notes": "Healthy start",
        "foods": [
          {
            "id": 1,
            "food": {
              "id": 1,
              "name": "Apple",
              "calories_per_100g": 52
            },
            "quantity": 150,
            "calories": 78,
            "protein": 0.45,
            "fat": 0.3,
            "carbs": 21
          }
        ],
        "total_calories": 78,
        "created_at": "2024-01-15T08:00:00Z"
      }
    ]
  }
}
```

#### Create Meal
```
POST /meals
```

**Request Body:**
```json
{
  "date": "2024-01-15",
  "meal_type": "breakfast",
  "name": "Morning Breakfast",
  "notes": "Healthy start",
  "foods": [
    {
      "food_id": 1,
      "quantity": 150
    }
  ]
}
```

#### Update Meal
```
PUT /meals/{meal_id}
```

**Request Body:** (Same as create)

#### Delete Meal
```
DELETE /meals/{meal_id}
```

#### Add Food to Meal
```
POST /meals/{meal_id}/foods
```

**Request Body:**
```json
{
  "food_id": 1,
  "quantity": 150
}
```

#### Update Food in Meal
```
PUT /meals/{meal_id}/foods/{meal_food_id}
```

**Request Body:**
```json
{
  "quantity": 200
}
```

#### Remove Food from Meal
```
DELETE /meals/{meal_id}/foods/{meal_food_id}
```

### 5. Daily Summary

#### Get Daily Summary
```
GET /summary/daily?date=<YYYY-MM-DD>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "date": "2024-01-15",
    "total_calories": 1800,
    "total_protein": 120,
    "total_fat": 60,
    "total_carbs": 200,
    "total_fiber": 25,
    "calorie_goal": 2000,
    "remaining_calories": 200,
    "weight_recorded": 70.5,
    "meals_summary": {
      "breakfast": {
        "calories": 400,
        "meal_count": 1
      },
      "lunch": {
        "calories": 600,
        "meal_count": 1
      },
      "dinner": {
        "calories": 700,
        "meal_count": 1
      },
      "snack": {
        "calories": 100,
        "meal_count": 2
      }
    }
  }
}
```

#### Update Daily Weight
```
POST /summary/daily/weight
```

**Request Body:**
```json
{
  "date": "2024-01-15",
  "weight": 70.5
}
```

### 6. Statistics

#### Get Weekly Summary
```
GET /statistics/weekly?start_date=<YYYY-MM-DD>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "week_start": "2024-01-15",
    "week_end": "2024-01-21",
    "daily_summaries": [
      {
        "date": "2024-01-15",
        "total_calories": 1800,
        "calorie_goal": 2000,
        "weight": 70.5
      }
    ],
    "weekly_stats": {
      "avg_calories": 1750,
      "avg_weight": 70.2,
      "total_meals": 21,
      "days_on_target": 5
    }
  }
}
```

#### Get Monthly Summary
```
GET /statistics/monthly?year=<YYYY>&month=<MM>
```

#### Get Nutrition Trends
```
GET /statistics/nutrition-trends?period=<week|month>&start_date=<YYYY-MM-DD>
```

### 7. Image Upload & Recognition

#### Upload Image
```
POST /images/upload
```

**Request:** (multipart/form-data)
```
file: <image_file>
meal_id: <meal_id> (optional)
```

**Response:**
```json
{
  "success": true,
  "data": {
    "image": {
      "id": 1,
      "filename": "food_image.jpg",
      "file_size": 1024000,
      "processing_status": "pending",
      "uploaded_at": "2024-01-15T12:00:00Z"
    }
  }
}
```

#### Get Recognition Results
```
GET /images/{image_id}/recognition
```

**Response:**
```json
{
  "success": true,
  "data": {
    "image_id": 1,
    "processing_status": "completed",
    "results": [
      {
        "id": 1,
        "food": {
          "id": 1,
          "name": "Apple",
          "calories_per_100g": 52
        },
        "confidence_score": 0.9234,
        "estimated_quantity": 150,
        "is_confirmed": false
      }
    ]
  }
}
```

#### Confirm Recognition Result
```
POST /images/{image_id}/recognition/{result_id}/confirm
```

**Request Body:**
```json
{
  "confirmed": true,
  "adjusted_quantity": 150
}
```

#### Add Recognition Result to Meal
```
POST /images/{image_id}/recognition/{result_id}/add-to-meal
```

**Request Body:**
```json
{
  "meal_id": 1,
  "quantity": 150
}
```

### 8. Search & Logging

#### Get Search History
```
GET /search/history?limit=<limit>
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "search_query": "apple",
      "search_type": "text",
      "results_count": 5,
      "created_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

## Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Request validation failed |
| `AUTHENTICATION_ERROR` | Authentication required or failed |
| `AUTHORIZATION_ERROR` | Insufficient permissions |
| `NOT_FOUND` | Resource not found |
| `DUPLICATE_ENTRY` | Duplicate data entry |
| `PROCESSING_ERROR` | Server processing error |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `FILE_TOO_LARGE` | Uploaded file exceeds size limit |
| `INVALID_FILE_TYPE` | Unsupported file type |

## Rate Limiting

- General API: 100 requests per minute
- Image Upload: 10 requests per minute
- Authentication: 5 requests per minute

## File Upload Limits

- Maximum file size: 10MB
- Supported formats: JPG, PNG, WEBP
- Maximum dimensions: 4096x4096 pixels

## Pagination

For endpoints that return lists, pagination is implemented using:
- `limit`: Number of items per page (default: 20, max: 100)
- `offset`: Number of items to skip (default: 0)

## Data Validation

### Common Validations
- `username`: 3-150 characters, alphanumeric and underscore
- `email`: Valid email format
- `password`: Minimum 8 characters
- `date`: ISO date format (YYYY-MM-DD)
- `weight`: 1-999 kg
- `height`: 50-300 cm
- `calories`: 0-9999 per 100g
- `quantity`: 0.1-9999 grams

## WebSocket Events (Future Enhancement)

For real-time updates:
- `image_processing_complete`: When image recognition is finished
- `meal_updated`: When meal is modified by user
- `daily_goal_achieved`: When daily calorie goal is met