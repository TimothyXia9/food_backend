# Django API Documentation

## Changelog

### 2025-07-28 - Barcode Recognition and Food Creation Integration

- **New Barcode Detection Endpoints**: Added comprehensive barcode recognition capabilities using computer vision
- **Open Food Facts Integration**: Added support for international food database queries via barcode
- **Food Creation from Barcode**: New endpoint to automatically create Food objects from barcode scan results
- **Combined Database Search**: Ability to query both USDA and Open Food Facts simultaneously
- **Complete Workflow**: Full integration from barcode scan to Food object creation and display
- **New Endpoints Added**:
  - `POST /images/detect-barcodes/` - Computer vision barcode detection
  - `POST /images/search-usda-barcode/` - USDA database barcode lookup
  - `POST /images/search-openfoodfacts-barcode/` - Open Food Facts barcode lookup
  - `POST /images/search-barcode-combined/` - Combined database search
  - `POST /images/create-food-from-barcode/` - **Primary endpoint** for creating Food objects from barcodes
  - `POST /images/analyze-with-barcode/` - Comprehensive image analysis with barcode detection

### 2025-07-26 - Image Analysis Streaming Format Update

- **Corrected Data Structure**: Updated streaming response format for `/images/analyze-stream/`
- **Fixed Field Names**: Corrected `stage_2.food_portions` instead of incorrect `results.portions`
- **Updated Event Types**: Changed from `stage1_*`/`stage2_*` to `start`, `food_detection`, `portion_estimation`, `complete`
- **Enhanced Documentation**: Added detailed data structure explanation and improved JavaScript client example
- **Breaking Change**: Frontend applications should listen for `stage_2.food_portions` instead of `results.portions`

### 2025-07-19 - USDA Food Integration

- **Enhanced Meal Creation**: Added support for automatic USDA food creation in meal endpoints
- **New Parameters**: Added `fdc_id` and `name` parameters for USDA foods
- **Automatic Processing**: System now automatically fetches USDA nutrition data and creates local food records
- **Affected Endpoints**: `POST /meals/create/` and `POST /meals/{meal_id}/add-food/`

## Overview

This document provides comprehensive documentation for the calorie tracking Django REST API. The API follows REST principles and returns JSON responses with a standardized format.

## Base URL

- **Development**: `http://localhost:8000/api/v1`
- **Production**: `https://your-domain.com/api/v1`

## Authentication

The API uses JWT (JSON Web Token) authentication. Most endpoints require authentication via the `Authorization` header:

```
Authorization: Bearer <access_token>
```

## Standard Response Format

All API responses follow this standardized format:

### Success Response

```json
{
	"success": true,
	"data": {...},
	"message": "Operation completed successfully"
}
```

### Error Response

```json
{
	"success": false,
	"error": {
		"code": "ERROR_CODE",
		"message": "Human readable error message",
		"details": {...}
	}
}
```

## Error Codes

- `VALIDATION_ERROR`: Request data validation failed
- `AUTHENTICATION_ERROR`: Invalid credentials or token
- `AUTHORIZATION_ERROR`: Insufficient permissions
- `NOT_FOUND_ERROR`: Requested resource not found
- `PROCESSING_ERROR`: Server-side processing error

---

## Authentication Endpoints

### User Registration

**POST** `/auth/register`

Register a new user account.

**Request Body:**

```json
{
  "username": "string (required)",
  "email": "string (required)",
  "password": "string (required, min 8 chars)",
  "nickname": "string (optional)"
}
```

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com",
      "nickname": "John",
      "profile": {
        "date_of_birth": null,
        "gender": null,
        "height": null,
        "weight": null,
        "daily_calorie_goal": null
      }
    },
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  },
  "message": "User registered successfully"
}
```

**Errors:**

- `400`: Validation errors (username/email already exists, weak password)

---

### User Login

**POST** `/auth/login`

Authenticate user and obtain JWT tokens.

**Request Body:**

```json
{
  "username": "string (required)",
  "password": "string (required)"
}
```

**Response (200 OK):**

```json
{
	"success": true,
	"data": {
		"access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
		"refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
		"user": {
			"id": 1,
			"username": "johndoe",
			"email": "john@example.com",
			"nickname": "John",
			"profile": {...}
		}
	},
	"message": "Login successful"
}
```

**Errors:**

- `401`: Invalid credentials

---

### Token Refresh

**POST** `/auth/refresh`

Refresh an access token using a refresh token.

**Request Body:**

```json
{
  "refresh": "string (required)"
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  },
  "message": "Token refreshed successfully"
}
```

**Errors:**

- `401`: Invalid refresh token

---

### User Logout

**POST** `/auth/logout`

Logout user and blacklist refresh token.

**Authentication:** Required

**Request Body:**

```json
{
  "refresh_token": "string (required)"
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": null,
  "message": "Logged out successfully"
}
```

---

## User Profile Endpoints

### Get User Profile

**GET** `/users/profile`

Get the authenticated user's profile information.

**Authentication:** Required

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "nickname": "John",
    "profile": {
      "date_of_birth": "1990-01-01",
      "gender": "M",
      "height": 175.5,
      "weight": 70.0,
      "daily_calorie_goal": 2000
    }
  }
}
```

---

### Update User Profile

**PUT** `/users/profile`

Update the authenticated user's profile information.

**Authentication:** Required

**Request Body (all fields optional):**

```json
{
  "nickname": "string",
  "date_of_birth": "YYYY-MM-DD",
  "gender": "M|F|O",
  "height": "number",
  "weight": "number",
  "daily_calorie_goal": "number"
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "nickname": "John Updated",
    "profile": {
      "date_of_birth": "1990-01-01",
      "gender": "M",
      "height": 175.5,
      "weight": 70.0,
      "daily_calorie_goal": 2200
    }
  },
  "message": "Profile updated successfully"
}
```

---

## Food Management Endpoints

### Search Foods

**GET** `/foods/search/`

Search for foods in the database. **Now uses USDA as primary source with local fallback**.

**Authentication:** None required (public access)

**Query Parameters:**

- `query` (required): Search term
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20)

**Example:** `/foods/search/?query=apple&page=1&page_size=10`

**Response (200 OK) - USDA Results:**

```json
{
  "success": true,
  "data": {
    "foods": [
      {
        "id": 1102702,
        "fdc_id": 1102702,
        "name": "Dole - Apples, raw, with skin",
        "brand": "Dole",
        "data_type": "branded_food",
        "publication_date": "2019-04-01",
        "is_usda": true,
        "calories_per_100g": 52.0,
        "protein_per_100g": 0.3,
        "fat_per_100g": 0.2,
        "carbs_per_100g": 13.8,
        "fiber_per_100g": 2.4,
        "sugar_per_100g": 10.4,
        "sodium_per_100g": 1.0,
        "category": { "name": "USDA Food" },
        "serving_size": 100,
        "is_custom": false
      }
    ],
    "total_count": 1,
    "page": 1,
    "page_size": 10,
    "total_pages": 1,
    "source": "USDA",
    "query": "apple"
  },
  "message": "Found 1 foods matching 'apple'"
}
```

**Response (200 OK) - Local Fallback Results:**

```json
{
  "success": true,
  "data": {
    "foods": [
      {
        "id": 1,
        "name": "Apple",
        "brand": null,
        "calories_per_100g": 52.0,
        "protein_per_100g": 0.3,
        "fat_per_100g": 0.2,
        "carbs_per_100g": 13.8,
        "serving_size": 100.0,
        "is_custom": false,
        "is_verified": true,
        "is_usda": false,
        "category": { "name": "Fruits" }
      }
    ],
    "total_count": 1,
    "page": 1,
    "page_size": 10,
    "total_pages": 1,
    "source": "LOCAL",
    "query": "apple"
  },
  "message": "Found 1 foods matching 'apple'"
}
```

**Notes:**

- The search now prioritizes USDA FoodData Central database
- If USDA is unavailable, falls back to local database
- USDA results include `is_usda: true` and `fdc_id` fields
- Food names are enhanced with brand information when available
- Some USDA search results may have `calories_per_100g: 0` until detailed nutrition is fetched

---

### Get Food Details

**GET** `/foods/{food_id}/`

Get detailed information about a specific food.

**Authentication:** Required

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Apple",
    "brand": null,
    "calories_per_100g": 52.0,
    "protein_per_100g": 0.3,
    "fat_per_100g": 0.2,
    "carbs_per_100g": 13.8,
    "fiber_per_100g": 2.4,
    "sugar_per_100g": 10.4,
    "sodium_per_100g": 1.0,
    "serving_size": 100.0,
    "is_custom": false,
    "is_verified": true,
    "usda_fdc_id": "1102702",
    "aliases": ["red apple", "green apple"]
  }
}
```

---

### Create Custom Food

**POST** `/foods/create/`

Create a custom food entry.

**Authentication:** Required

**Request Body:**

```json
{
  "name": "string (required)",
  "brand": "string (optional)",
  "calories_per_100g": "number (required)",
  "protein_per_100g": "number (optional)",
  "fat_per_100g": "number (optional)",
  "carbs_per_100g": "number (optional)",
  "fiber_per_100g": "number (optional)",
  "sugar_per_100g": "number (optional)",
  "sodium_per_100g": "number (optional)",
  "serving_size": "number (required)"
}
```

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "id": 100,
    "name": "My Custom Food",
    "brand": "My Brand",
    "calories_per_100g": 200.0,
    "is_custom": true,
    "is_verified": false
  },
  "message": "Custom food created successfully"
}
```

---

### Update Food

**PUT** `/foods/{food_id}/update/`

Update a food entry (only custom foods created by the user).

**Authentication:** Required

**Request Body:** Same as Create Custom Food

**Response (200 OK):**

```json
{
	"success": true,
	"data": {...},
	"message": "Food updated successfully"
}
```

**Errors:**

- `403`: Cannot edit non-custom foods or foods created by other users
- `404`: Food not found

---

### Delete Food

**DELETE** `/foods/{food_id}/delete/`

Delete a food entry (only custom foods created by the user).

**Authentication:** Required

**Response (200 OK):**

```json
{
  "success": true,
  "data": null,
  "message": "Food deleted successfully"
}
```

**Errors:**

- `403`: Cannot delete non-custom foods or foods created by other users
- `404`: Food not found

---

## USDA Integration Endpoints

### Search USDA Foods

**GET** `/foods/usda/search/`

Search foods in the USDA FoodData Central database.

**Authentication:** Required

**Query Parameters:**

- `query` (required): Search term
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20)

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "foods": [
      {
        "fdc_id": "1102702",
        "description": "Apples, raw, with skin",
        "brand_owner": null,
        "food_category": "Fruits and Fruit Juices",
        "publication_date": "2019-04-01"
      }
    ],
    "total_hits": 150,
    "page": 1,
    "page_size": 20
  }
}
```

---

### Get USDA Nutrition

**GET** `/foods/usda/nutrition/{fdc_id}/`

Get detailed nutrition information for a USDA food. **Now returns data in Food interface format**.

**Authentication:** None required (public access)

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": 1102702,
    "fdc_id": 1102702,
    "name": "Apples, raw, with skin",
    "brand": "Dole",
    "data_type": "branded_food",
    "publication_date": "2019-04-01",
    "is_usda": true,
    "calories_per_100g": 52.0,
    "protein_per_100g": 0.26,
    "fat_per_100g": 0.17,
    "carbs_per_100g": 13.81,
    "fiber_per_100g": 2.4,
    "sugar_per_100g": 10.39,
    "sodium_per_100g": 1.0,
    "category": { "name": "USDA Food" },
    "serving_size": 100,
    "is_custom": false,
    "is_verified": true,
    "ingredients": "Apples",
    "nutrients": [
      {
        "nutrient_id": 1008,
        "nutrient_name": "Energy",
        "unit_name": "kcal",
        "value": 52.0
      },
      {
        "nutrient_id": 1003,
        "nutrient_name": "Protein",
        "unit_name": "g",
        "value": 0.26
      }
    ]
  },
  "message": "Retrieved nutrition data for FDC ID 1102702"
}
```

**Notes:**

- Returns complete nutrition data formatted to match our Food interface
- Includes both structured nutrition data and detailed nutrient breakdown
- Can be used directly in frontend components without additional processing

---

### Create Food from USDA

**POST** `/foods/usda/create/`

Create a food entry from USDA data.

**Authentication:** Required

**Request Body:**

```json
{
  "fdc_id": "string (required)",
  "custom_name": "string (optional)"
}
```

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "id": 101,
    "name": "Apples, raw, with skin",
    "usda_fdc_id": "1102702",
    "calories_per_100g": 52.0,
    "is_verified": true
  },
  "message": "Food created from USDA data successfully"
}
```

---

### Get Search History

**GET** `/foods/search/history/`

Get the user's food search history.

**Authentication:** Required

**Query Parameters:**

- `limit` (optional): Number of recent searches (default: 10)

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "searches": [
      {
        "id": 1,
        "search_query": "apple",
        "search_type": "text",
        "results_count": 5,
        "created_at": "2024-01-15T10:30:00Z"
      }
    ]
  }
}
```

---

## Meal Tracking Endpoints

### Create Meal

**POST** `/meals/create/`

Create a new meal entry.

**Authentication:** Required

**Request Body:**

```json
{
  "date": "YYYY-MM-DD (required)",
  "meal_type": "breakfast|lunch|dinner|snack (required)",
  "name": "string (optional)",
  "notes": "string (optional)",
  "foods": [
    {
      "food_id": "number (required, use -1 for USDA foods)",
      "quantity": "number (required)",
      "fdc_id": "number (optional, required when food_id is -1)",
      "name": "string (optional, for USDA foods)"
    }
  ]
}
```

**USDA Food Support:**

The API now supports automatic creation of USDA foods when adding them to meals. For USDA foods:

1. Set `food_id` to `-1` (placeholder for non-existent local food)
2. Include `fdc_id` with the USDA FoodData Central ID
3. Optionally include `name` as a fallback food name

Example with USDA food:

```json
{
  "date": "2024-01-15",
  "meal_type": "breakfast",
  "name": "Morning Meal",
  "foods": [
    {
      "food_id": -1,
      "quantity": 150,
      "fdc_id": 171688,
      "name": "Apples, raw"
    },
    {
      "food_id": 5,
      "quantity": 200
    }
  ]
}
```

The system will:

- Check if a food with the given `fdc_id` already exists locally
- If not, automatically fetch nutrition data from USDA and create a local Food record
- Add the food to the meal with accurate nutritional calculations

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "date": "2024-01-15",
    "meal_type": "breakfast",
    "name": "Morning Meal",
    "total_calories": 520.0,
    "total_protein": 15.2,
    "total_fat": 8.5,
    "total_carbs": 85.3,
    "foods": [
      {
        "id": 1,
        "food": {
          "id": 1,
          "name": "Apple"
        },
        "quantity": 150.0,
        "calories": 78.0
      }
    ]
  },
  "message": "Meal created successfully"
}
```

---

### Get Meal Details

**GET** `/meals/{meal_id}/`

Get detailed information about a specific meal.

**Authentication:** Required

**Response (200 OK):**

```json
{
	"success": true,
	"data": {
		"id": 1,
		"date": "2024-01-15",
		"meal_type": "breakfast",
		"name": "Morning Meal",
		"notes": "Healthy start to the day",
		"total_calories": 520.0,
		"total_protein": 15.2,
		"total_fat": 8.5,
		"total_carbs": 85.3,
		"foods": [...]
	}
}
```

---

### Update Meal

**PUT** `/meals/{meal_id}/update/`

Update a meal entry.

**Authentication:** Required

**Request Body:** Same as Create Meal

**Response (200 OK):**

```json
{
	"success": true,
	"data": {...},
	"message": "Meal updated successfully"
}
```

---

### Delete Meal

**DELETE** `/meals/{meal_id}/delete/`

Delete a meal entry.

**Authentication:** Required

**Response (200 OK):**

```json
{
  "success": true,
  "data": null,
  "message": "Meal deleted successfully"
}
```

---

### Get User Meals

**GET** `/meals/list/`

Get meals for the authenticated user.

**Authentication:** Required

**Query Parameters:**

- `date` (optional): Filter by specific date (YYYY-MM-DD)
- `meal_type` (optional): Filter by meal type
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20)

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "meals": [
      {
        "id": 1,
        "date": "2024-01-15T00:00:00Z",
        "meal_type": "breakfast",
        "name": "Morning Meal",
        "total_calories": 520.0,
        "total_protein": 15.2,
        "total_fat": 8.5,
        "total_carbs": 85.3,
        "foods": [
          {
            "id": 1,
            "food": {
              "id": 1,
              "name": "Apple"
            },
            "quantity": 150.0,
            "calories": 78.0
          }
        ],
        "food_count": 1,
        "created_at": "2024-01-15T08:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_pages": 1,
      "total_count": 10,
      "has_next": false,
      "has_previous": false
    }
  }
}
```

---

### Get Recent Meals

**GET** `/meals/recent/`

Get the user's most recent meals.

**Authentication:** Required

**Query Parameters:**

- `limit` (optional): Number of recent meals (default: 10)

**Response (200 OK):**

```json
{
	"success": true,
	"data": {
		"meals": [...]
	}
}
```

---

### Add Food to Meal

**POST** `/meals/{meal_id}/add-food/`

Add a food item to an existing meal.

**Authentication:** Required

**Request Body:**

```json
{
  "food_id": "number (required, use -1 for USDA foods)",
  "quantity": "number (required)",
  "fdc_id": "number (optional, required when food_id is -1)",
  "name": "string (optional, for USDA foods)"
}
```

**USDA Food Support:**

Similar to meal creation, this endpoint supports adding USDA foods. For USDA foods:

1. Set `food_id` to `-1`
2. Include `fdc_id` with the USDA FoodData Central ID
3. Optionally include `name` as a fallback food name

Example with USDA food:

```json
{
  "food_id": -1,
  "quantity": 100,
  "fdc_id": 171688,
  "name": "Apples, raw"
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "meal_food_id": 5,
    "food": {
      "id": 2,
      "name": "Banana"
    },
    "quantity": 120.0,
    "calories": 107.0
  },
  "message": "Food added to meal successfully"
}
```

---

### Update Meal Food

**PUT** `/meals/food/{meal_food_id}/update/`

Update the quantity of a food item in a meal.

**Authentication:** Required

**Request Body:**

```json
{
  "quantity": "number (required)"
}
```

**Response (200 OK):**

```json
{
	"success": true,
	"data": {...},
	"message": "Meal food updated successfully"
}
```

---

### Remove Food from Meal

**DELETE** `/meals/food/{meal_food_id}/delete/`

Remove a food item from a meal.

**Authentication:** Required

**Response (200 OK):**

```json
{
  "success": true,
  "data": null,
  "message": "Food removed from meal successfully"
}
```

---

### Create Meal Plan

**POST** `/meals/plan/`

Create a meal plan for multiple days.

**Authentication:** Required

**Request Body:**

```json
{
	"start_date": "YYYY-MM-DD (required)",
	"end_date": "YYYY-MM-DD (required)",
	"meal_template": {
		"breakfast": [
			{
				"food_id": 1,
				"quantity": 150
			}
		],
		"lunch": [...],
		"dinner": [...]
	}
}
```

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "meals_created": 21,
    "start_date": "2024-01-15",
    "end_date": "2024-01-21"
  },
  "message": "Meal plan created successfully"
}
```

---

## Nutrition Tracking Endpoints

### Get Daily Summary

**GET** `/meals/daily-summary/`

Get nutrition summary for a specific date.

**Authentication:** Required

**Query Parameters:**

- `date` (optional): Date in YYYY-MM-DD format (default: today)

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "date": "2024-01-15",
    "total_calories": 1850.0,
    "total_protein": 85.5,
    "total_fat": 65.2,
    "total_carbs": 220.8,
    "total_fiber": 28.5,
    "goal_calories": 2000,
    "goal_protein": 100,
    "goal_fat": 70,
    "goal_carbs": 250,
    "meals": [
      {
        "meal_type": "breakfast",
        "calories": 520.0,
        "protein": 15.2,
        "fat": 8.5,
        "carbs": 85.3
      }
    ]
  }
}
```

---

### Get Nutrition Stats

**GET** `/meals/nutrition-stats/`

Get nutrition statistics over a time period.

**Authentication:** Required

**Query Parameters:**

- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)
- `period` (optional): 'weekly' | 'monthly' (default: 'weekly')

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "period": "weekly",
    "start_date": "2024-01-01",
    "end_date": "2024-01-07",
    "average_calories": 1875.0,
    "average_protein": 82.3,
    "average_fat": 63.8,
    "average_carbs": 215.5,
    "daily_stats": [
      {
        "date": "2024-01-01",
        "calories": 1850.0,
        "protein": 85.5,
        "fat": 65.2,
        "carbs": 220.8
      }
    ]
  }
}
```

---

### Record Weight

**POST** `/meals/record-weight/`

Record a weight measurement.

**Authentication:** Required

**Request Body:**

```json
{
  "weight": "number (required)",
  "date": "YYYY-MM-DD (optional, default: today)",
  "notes": "string (optional)"
}
```

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "weight": 70.5,
    "date": "2024-01-15",
    "notes": "Morning weight"
  },
  "message": "Weight recorded successfully"
}
```

---

## Image Processing Endpoints

### Upload Image

**POST** `/images/upload/`

Upload a food image for analysis.

**Authentication:** Required

**Request Body (multipart/form-data):**

- `image`: Image file (JPG, PNG, max 10MB)
- `notes` (optional): Description or notes about the image

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "image_url": "/media/images/food_123.jpg",
    "upload_date": "2024-01-15T10:30:00Z",
    "notes": "Lunch plate",
    "status": "uploaded"
  },
  "message": "Image uploaded successfully"
}
```

---

### Analyze Image

**POST** `/images/analyze/`

Analyze an uploaded image for food recognition.

**Authentication:** Required

**Request Body:**

```json
{
  "image_id": "number (required)",
  "analysis_type": "full|quick (optional, default: full)"
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "analysis_id": 1,
    "status": "processing",
    "estimated_completion": "2024-01-15T10:35:00Z"
  },
  "message": "Image analysis started"
}
```

---

### Analyze Image Stream

**POST** `/images/analyze-stream/`

Analyze an uploaded image for food recognition with real-time streaming results using Server-Sent Events (SSE).

**Authentication:** Required

**Request Body:**

```json
{
  "image_id": "number (required)"
}
```

**Response (200 OK - text/event-stream):**

The endpoint returns a streaming response with Server-Sent Events (SSE) format. Each event contains JSON data with the current analysis step:

```
data: {"step": "start", "message": "开始分析图片", "image_id": 23}

data: {"step": "food_detection", "message": "正在识别食物种类...", "progress": 25}

data: {"step": "food_detection_complete", "foods": [{"name": "Apple", "confidence": 0.92}], "progress": 50}

data: {"step": "portion_estimation", "message": "正在估算食物分量...", "progress": 75}

data: {"step": "complete", "success": true, "progress": 100,
       "stage_1": {"food_types": [{"name": "猪排", "confidence": 0.95}]},
       "stage_2": {"food_portions": [
                {"name": "猪排", "estimated_grams": 300, "cooking_method": "煎"},
                {"name": "青菜", "estimated_grams": 100, "cooking_method": "炒"}
        ]}}
```

**Streaming Event Types:**

- `start`: Analysis begins, returns image_id
- `food_detection`: Food identification phase in progress
- `food_detection_complete`: Food identification complete, includes detected foods with confidence scores
- `portion_estimation`: Portion estimation phase in progress
- `complete`: Complete analysis finished with full results including stage_1 and stage_2 data
- `error`: Analysis error occurred

**Data Structure:**

- `stage_1.food_types`: Array of detected foods with confidence scores
- `stage_2.food_portions`: Array of food portions with estimated weights and cooking methods
- Each portion contains: `name`, `estimated_grams`, `cooking_method` (optional)

**Frontend Integration Notes:**

Frontend applications should listen for food portion data in the `complete` event:

```javascript
if (data.step === "complete" && data.stage_2?.food_portions) {
  // Handle food portions array
  data.stage_2.food_portions.forEach((portion) => {
    console.log(`${portion.name}: ${portion.estimated_grams}g`);
    if (portion.cooking_method) {
      console.log(`Cooking method: ${portion.cooking_method}`);
    }
  });
}
```

**Headers:**

- `Content-Type: text/event-stream; charset=utf-8`
- `Cache-Control: no-cache, no-store, must-revalidate`
- `Access-Control-Allow-Origin: http://localhost:3000`

**JavaScript Client Example:**

```javascript
const eventSource = new EventSource("/api/v1/images/analyze-stream/", {
  headers: {
    Authorization: "Bearer " + token,
  },
});

eventSource.onmessage = function (event) {
  const data = JSON.parse(event.data);
  console.log("Analysis step:", data.step, data.message);

  // Handle different analysis stages
  switch (data.step) {
    case "food_detection_complete":
      console.log("Detected foods:", data.foods);
      break;
    case "complete":
      console.log("Food types:", data.stage_1?.food_types);
      console.log("Food portions:", data.stage_2?.food_portions);
      eventSource.close();
      break;
    case "error":
      console.error("Analysis error:", data.message);
      eventSource.close();
      break;
  }
};

eventSource.onerror = function (event) {
  console.error("Stream error:", event);
  eventSource.close();
};
```

**Notes:**

- Uses Server-Sent Events (SSE) for real-time progress updates
- Provides step-by-step analysis feedback to improve user experience
- Automatically handles CORS for frontend integration
- Stream closes automatically when analysis is complete or fails
- Supports the same two-stage analysis as the regular analyze endpoint

---

### Get Image Results

**GET** `/images/{image_id}/results/`

Get the food recognition results for an analyzed image.

**Authentication:** Required

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "image_id": 1,
    "status": "completed",
    "analysis_date": "2024-01-15T10:35:00Z",
    "recognized_foods": [
      {
        "id": 1,
        "food_name": "Grilled Chicken Breast",
        "confidence": 0.92,
        "estimated_quantity": 150.0,
        "estimated_calories": 248.0,
        "bounding_box": {
          "x": 100,
          "y": 150,
          "width": 200,
          "height": 180
        },
        "usda_match": {
          "fdc_id": "1234567",
          "description": "Chicken, broilers or fryers, breast, meat only, cooked, roasted"
        }
      }
    ],
    "total_estimated_calories": 520.0,
    "analysis_notes": "High confidence detection of 3 food items"
  }
}
```

---

### Delete Image

**DELETE** `/images/{image_id}/delete/`

Delete an uploaded image and its analysis results.

**Authentication:** Required

**Response (200 OK):**

```json
{
  "success": true,
  "data": null,
  "message": "Image deleted successfully"
}
```

---

### Get User Images

**GET** `/images/list/`

Get all images uploaded by the authenticated user.

**Authentication:** Required

**Query Parameters:**

- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20)
- `status` (optional): Filter by status ('uploaded', 'processing', 'completed', 'failed')

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "images": [
      {
        "id": 1,
        "image_url": "/media/images/food_123.jpg",
        "upload_date": "2024-01-15T10:30:00Z",
        "status": "completed",
        "recognized_foods_count": 3,
        "total_estimated_calories": 520.0
      }
    ],
    "total_count": 1,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

---

### Confirm Food Recognition

**POST** `/images/confirm/`

Confirm or correct the food recognition results.

**Authentication:** Required

**Request Body:**

```json
{
  "result_id": "number (required)",
  "is_confirmed": "boolean (required)",
  "corrections": [
    {
      "recognized_food_id": 1,
      "actual_food_id": 5,
      "actual_quantity": 180.0
    }
  ]
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "result_id": 1,
    "confirmed": true,
    "corrections_applied": 1
  },
  "message": "Food recognition confirmed successfully"
}
```

---

### Create Meal from Image

**POST** `/images/create-meal/`

Create a meal entry from confirmed image recognition results.

**Authentication:** Required

**Request Body:**

```json
{
  "image_id": "number (required)",
  "meal_type": "breakfast|lunch|dinner|snack (required)",
  "date": "YYYY-MM-DD (optional, default: today)",
  "meal_name": "string (optional)"
}
```

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "meal_id": 5,
    "image_id": 1,
    "foods_added": 3,
    "total_calories": 520.0
  },
  "message": "Meal created from image successfully"
}
```

---

### Detect Barcodes

**POST** `/images/detect-barcodes/`

Detect barcodes in an uploaded image using computer vision.

**Authentication:** Required

**Request Body:**

```json
{
  "image_id": "number (required)"
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "image_id": 1,
    "total_barcodes": 2,
    "food_barcodes": 1,
    "barcodes": [
      {
        "data": "1234567890123",
        "type": "EAN13",
        "quality": 95,
        "orientation": "horizontal",
        "rect": {
          "left": 100,
          "top": 150,
          "width": 200,
          "height": 50
        },
        "polygon": [[100, 150], [300, 150], [300, 200], [100, 200]],
        "is_food_barcode": true,
        "formatted_data": "1234567890123"
      }
    ],
    "food_barcodes_only": [
      {
        "data": "1234567890123",
        "type": "EAN13",
        "quality": 95,
        "orientation": "horizontal",
        "rect": {
          "left": 100,
          "top": 150,
          "width": 200,
          "height": 50
        },
        "polygon": [[100, 150], [300, 150], [300, 200], [100, 200]],
        "is_food_barcode": true,
        "formatted_data": "1234567890123"
      }
    ]
  },
  "message": "Barcode detection completed"
}
```

---

### Search USDA by Barcode

**POST** `/images/search-usda-barcode/`

Search USDA FoodData Central database using a barcode/UPC code.

**Authentication:** Required

**Request Body:**

```json
{
  "barcode": "string (required) - Product barcode/UPC code"
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "barcode": "1234567890123",
    "usda_results": [
      {
        "fdc_id": 123456,
        "description": "Product Name",
        "data_type": "Branded",
        "brand_owner": "Brand Name",
        "ingredients": "Water, Sugar, Natural Flavors",
        "gtin_upc": "1234567890123",
        "serving_size": "250",
        "serving_size_unit": "ml"
      }
    ],
    "total_results": 1
  },
  "message": "USDA barcode search completed"
}
```

---

### Search Open Food Facts by Barcode

**POST** `/images/search-openfoodfacts-barcode/`

Search Open Food Facts database using a barcode for international product information.

**Authentication:** Required

**Request Body:**

```json
{
  "barcode": "string (required) - Product barcode/UPC code"
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "barcode": "1234567890123",
    "product": {
      "barcode": "1234567890123",
      "product_name": "Product Name",
      "product_name_en": "Product Name (English)",
      "brands": "Brand Name",
      "categories": "Beverages, Soft drinks",
      "ingredients_text": "Water, Sugar, Natural flavors",
      "serving_size": "250ml",
      "serving_quantity": "250",
      "nutrition_grade": "a",
      "image_url": "https://images.openfoodfacts.org/images/products/123/456/789/front_en.jpg",
      "image_front_url": "https://images.openfoodfacts.org/images/products/123/456/789/front_en.jpg",
      "nutrition_per_100g": {
        "energy_kcal": 42,
        "proteins": 0,
        "carbohydrates": 10.5,
        "sugars": 10.5,
        "fat": 0,
        "saturated_fat": 0,
        "fiber": 0,
        "sodium": 0.01
      },
      "data_source": "Open Food Facts"
    }
  },
  "message": "Product found in Open Food Facts"
}
```

---

### Search Combined Barcode Databases

**POST** `/images/search-barcode-combined/`

Search both USDA and Open Food Facts databases simultaneously for comprehensive product information.

**Authentication:** Required

**Request Body:**

```json
{
  "barcode": "string (required) - Product barcode/UPC code"
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "barcode": "1234567890123",
    "usda_results": [
      {
        "fdc_id": 123456,
        "description": "Product Name",
        "data_type": "Branded",
        "brand_owner": "Brand Name",
        "ingredients": "Water, Sugar, Natural Flavors",
        "gtin_upc": "1234567890123",
        "serving_size": "250",
        "serving_size_unit": "ml"
      }
    ],
    "openfoodfacts_result": {
      "barcode": "1234567890123",
      "product_name": "Product Name",
      "product_name_en": "Product Name (English)",
      "brands": "Brand Name",
      "categories": "Beverages, Soft drinks",
      "ingredients_text": "Water, Sugar, Natural flavors",
      "serving_size": "250ml",
      "serving_quantity": "250",
      "nutrition_grade": "a",
      "image_url": "https://images.openfoodfacts.org/images/products/123/456/789/front_en.jpg",
      "image_front_url": "https://images.openfoodfacts.org/images/products/123/456/789/front_en.jpg",
      "nutrition_per_100g": {
        "energy_kcal": 42,
        "proteins": 0,
        "carbohydrates": 10.5,
        "sugars": 10.5,
        "fat": 0,
        "saturated_fat": 0,
        "fiber": 0,
        "sodium": 0.01
      },
      "data_source": "Open Food Facts"
    },
    "total_sources": 2
  },
  "message": "Found product information from 2 source(s)"
}
```

---

### Create Food from Barcode

**POST** `/images/create-food-from-barcode/`

Create a Food object in the database from barcode scan results. This endpoint automatically queries Open Food Facts (and USDA if available) to get product information and creates a local Food record.

**Authentication:** Required

**Request Body:**

```json
{
  "barcode": "string (required) - Product barcode/UPC code"
}
```

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "food": {
      "id": 123,
      "name": "Coca-Cola Classic",
      "brand": "Coca-Cola",
      "barcode": "1234567890123",
      "serving_size": 100,
      "serving_unit": "g",
      "calories_per_100g": 42,
      "protein_per_100g": 0,
      "fat_per_100g": 0,
      "carbs_per_100g": 10.5,
      "fiber_per_100g": 0,
      "sugar_per_100g": 10.5,
      "sodium_per_100g": 0.01,
      "description": "Product scanned from barcode 1234567890123",
      "ingredients": "Water, Sugar, Natural flavors, Caffeine",
      "data_source": "Open Food Facts",
      "nutrition_grade": "a",
      "image_url": "https://images.openfoodfacts.org/images/products/123/456/789/front_en.jpg"
    },
    "message": "Created food from barcode: Coca-Cola Classic"
  }
}
```

**Response (404 Not Found):**

```json
{
  "success": false,
  "message": "No product found for barcode 1234567890123 in any database"
}
```

---

### Analyze Image with Barcode

**POST** `/images/analyze-with-barcode/`

Perform comprehensive image analysis including both food recognition and barcode detection with nutrition lookup.

**Authentication:** Required

**Request Body:**

```json
{
  "image_id": "number (required)"
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "image_id": 1,
    "status": "completed",
    "barcode_detection": {
      "total_barcodes": 1,
      "food_barcodes": 1,
      "barcodes": [
        {
          "data": "1234567890123",
          "type": "EAN13",
          "quality": 95,
          "orientation": "horizontal",
          "rect": {
            "left": 100,
            "top": 150,
            "width": 200,
            "height": 50
          },
          "polygon": [[100, 150], [300, 150], [300, 200], [100, 200]],
          "is_food_barcode": true,
          "formatted_data": "1234567890123"
        }
      ]
    },
    "usda_barcode_results": {
      "total_products": 1,
      "products": [
        {
          "fdc_id": 123456,
          "description": "Product Name",
          "data_type": "Branded",
          "brand_owner": "Brand Name",
          "ingredients": "Water, Sugar, Natural Flavors",
          "gtin_upc": "1234567890123",
          "serving_size": "250",
          "serving_size_unit": "ml",
          "source_barcode": "1234567890123",
          "barcode_info": {
            "data": "1234567890123",
            "type": "EAN13",
            "quality": 95,
            "orientation": "horizontal",
            "rect": {
              "left": 100,
              "top": 150,
              "width": 200,
              "height": 50
            },
            "polygon": [[100, 150], [300, 150], [300, 200], [100, 200]],
            "is_food_barcode": true,
            "formatted_data": "1234567890123"
          }
        }
      ]
    },
    "openfoodfacts_results": {
      "total_products": 1,
      "products": [
        {
          "barcode": "1234567890123",
          "product_name": "Product Name",
          "product_name_en": "Product Name (English)",
          "brands": "Brand Name",
          "categories": "Beverages, Soft drinks",
          "ingredients_text": "Water, Sugar, Natural flavors",
          "serving_size": "250ml",
          "serving_quantity": "250",
          "nutrition_grade": "a",
          "image_url": "https://images.openfoodfacts.org/images/products/123/456/789/front_en.jpg",
          "image_front_url": "https://images.openfoodfacts.org/images/products/123/456/789/front_en.jpg",
          "nutrition_per_100g": {
            "energy_kcal": 42,
            "proteins": 0,
            "carbohydrates": 10.5,
            "sugars": 10.5,
            "fat": 0,
            "saturated_fat": 0,
            "fiber": 0,
            "sodium": 0.01
          },
          "data_source": "Open Food Facts",
          "source_barcode": "1234567890123",
          "barcode_info": {
            "data": "1234567890123",
            "type": "EAN13",
            "quality": 95,
            "orientation": "horizontal",
            "rect": {
              "left": 100,
              "top": 150,
              "width": 200,
              "height": 50
            },
            "polygon": [[100, 150], [300, 150], [300, 200], [100, 200]],
            "is_food_barcode": true,
            "formatted_data": "1234567890123"
          }
        }
      ]
    },
    "food_analysis": {
      "success": true,
      "stage_1": {
        "food_types": [
          {
            "name": "Soda can",
            "confidence": 0.95
          }
        ]
      },
      "stage_2": {
        "food_portions": [
          {
            "name": "Coca-Cola",
            "estimated_grams": 330,
            "cooking_method": "canned"
          }
        ]
      }
    }
  },
  "message": "Image analysis with barcode detection completed"
}
```

---

## Rate Limits

| Endpoint Type     | Rate Limit    | Window   |
| ----------------- | ------------- | -------- |
| Authentication    | 10 requests   | 1 minute |
| Image Upload      | 20 requests   | 1 hour   |
| Image Analysis    | 10 requests   | 1 hour   |
| Barcode Detection | 15 requests   | 1 hour   |
| Barcode Search    | 25 requests   | 1 hour   |
| Food Creation     | 10 requests   | 1 hour   |
| USDA API       | 100 requests  | 1 hour   |
| General API    | 1000 requests | 1 hour   |

## HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required or failed
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Pagination

List endpoints support pagination with the following parameters:

- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)

Pagination response includes:

- `total_count`: Total number of items
- `page`: Current page number
- `page_size`: Items per page
- `total_pages`: Total number of pages

## Testing

Use the following curl commands to test the API:

### Authentication Test

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"testpass123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'
```

### Authenticated Request Test

```bash
TOKEN="your-jwt-token-here"

# Search foods
curl -X GET "http://localhost:8000/api/v1/foods/search/?query=apple" \
  -H "Authorization: Bearer $TOKEN"
```

## SDK and Integration

For frontend integration, see the TypeScript service layer documentation in `/frontend/src/services/`.

The API is designed to work seamlessly with the React frontend application, providing complete calorie tracking functionality with AI-powered food recognition.
