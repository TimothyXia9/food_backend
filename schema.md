# Database Schema Design

## Overview

This document outlines the database schema for the calorie tracking web application. The schema supports user authentication, food recognition, dietary tracking, and statistical analysis.

## Core Tables

### 1. User Management

#### users

| Column        | Type         | Constraints                 | Description            |
| ------------- | ------------ | --------------------------- | ---------------------- |
| id            | INTEGER      | PRIMARY KEY, AUTO_INCREMENT | Unique user identifier |
| username      | VARCHAR(150) | UNIQUE, NOT NULL            | User's chosen username |
| email         | VARCHAR(254) | UNIQUE, NOT NULL            | User's email address   |
| password_hash | VARCHAR(128) | NOT NULL                    | Hashed password        |
| nickname      | VARCHAR(30)  | NULL                        | User's nickname        |
| date_joined   | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP   | Account creation date  |
| last_login    | TIMESTAMP    | NULL                        | Last login timestamp   |

#### user_profiles

| Column             | Type         | Constraints                                           | Description                       |
| ------------------ | ------------ | ----------------------------------------------------- | --------------------------------- |
| id                 | INTEGER      | PRIMARY KEY, AUTO_INCREMENT                           | Profile identifier                |
| user_id            | INTEGER      | FOREIGN KEY (users.id), UNIQUE                        | Reference to user                 |
| date_of_birth      | DATE         | NULL                                                  | User's birth date                 |
| gender             | VARCHAR(10)  | NULL                                                  | User's gender (Male/Female/Other) |
| height             | DECIMAL(5,2) | NULL                                                  | Height in cm                      |
| weight             | DECIMAL(5,2) | NULL                                                  | Current weight in kg              |
| daily_calorie_goal | INTEGER      | NULL                                                  | Daily calorie target              |
| created_at         | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP                             | Profile creation date             |
| updated_at         | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Last update                       |

### 2. Food Database

#### food_categories

| Column      | Type         | Constraints                 | Description          |
| ----------- | ------------ | --------------------------- | -------------------- |
| id          | INTEGER      | PRIMARY KEY, AUTO_INCREMENT | Category identifier  |
| name        | VARCHAR(100) | UNIQUE, NOT NULL            | Category name        |
| description | TEXT         | NULL                        | Category description |
| created_at  | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP   | Creation date        |

#### foods

| Column            | Type         | Constraints                                           | Description                   |
| ----------------- | ------------ | ----------------------------------------------------- | ----------------------------- |
| id                | INTEGER      | PRIMARY KEY, AUTO_INCREMENT                           | Food identifier               |
| name              | VARCHAR(200) | NOT NULL                                              | Food name                     |
| category_id       | INTEGER      | FOREIGN KEY (food_categories.id)                      | Food category                 |
| brand             | VARCHAR(100) | NULL                                                  | Brand name                    |
| barcode           | VARCHAR(50)  | NULL                                                  | Product barcode               |
| serving_size      | DECIMAL(8,2) | NOT NULL                                              | Default serving size in grams |
| calories_per_100g | DECIMAL(8,2) | NOT NULL                                              | Calories per 100g             |
| protein_per_100g  | DECIMAL(8,2) | NULL                                                  | Protein per 100g              |
| fat_per_100g      | DECIMAL(8,2) | NULL                                                  | Fat per 100g                  |
| carbs_per_100g    | DECIMAL(8,2) | NULL                                                  | Carbohydrates per 100g        |
| fiber_per_100g    | DECIMAL(8,2) | NULL                                                  | Fiber per 100g                |
| sugar_per_100g    | DECIMAL(8,2) | NULL                                                  | Sugar per 100g                |
| sodium_per_100g   | DECIMAL(8,2) | NULL                                                  | Sodium per 100g               |
| is_verified       | BOOLEAN      | DEFAULT FALSE                                         | Data verification status      |
| created_by        | INTEGER      | FOREIGN KEY (users.id), NULL                          | User who added custom food    |
| created_at        | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP                             | Creation date                 |
| updated_at        | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Last update                   |

#### food_aliases

| Column     | Type         | Constraints                 | Description       |
| ---------- | ------------ | --------------------------- | ----------------- |
| id         | INTEGER      | PRIMARY KEY, AUTO_INCREMENT | Alias identifier  |
| food_id    | INTEGER      | FOREIGN KEY (foods.id)      | Reference to food |
| alias      | VARCHAR(200) | NOT NULL                    | Alternative name  |
| created_at | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP   | Creation date     |

### 3. Dietary Records

#### meals

| Column     | Type         | Constraints                                           | Description                         |
| ---------- | ------------ | ----------------------------------------------------- | ----------------------------------- |
| id         | INTEGER      | PRIMARY KEY, AUTO_INCREMENT                           | Meal identifier                     |
| user_id    | INTEGER      | FOREIGN KEY (users.id), NOT NULL                      | Reference to user                   |
| date       | DATE         | NOT NULL                                              | Meal date                           |
| meal_type  | VARCHAR(20)  | NOT NULL                                              | Type (breakfast/lunch/dinner/snack) |
| name       | VARCHAR(200) | NULL                                                  | Optional meal name                  |
| notes      | TEXT         | NULL                                                  | User notes                          |
| created_at | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP                             | Creation date                       |
| updated_at | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Last update                         |

#### meal_foods

| Column   | Type         | Constraints                      | Description              |
| -------- | ------------ | -------------------------------- | ------------------------ |
| id       | INTEGER      | PRIMARY KEY, AUTO_INCREMENT      | Entry identifier         |
| meal_id  | INTEGER      | FOREIGN KEY (meals.id), NOT NULL | Reference to meal        |
| food_id  | INTEGER      | FOREIGN KEY (foods.id), NOT NULL | Reference to food        |
| quantity | DECIMAL(8,2) | NOT NULL                         | Quantity in grams        |
| calories | DECIMAL(8,2) | NOT NULL                         | Calculated calories      |
| protein  | DECIMAL(8,2) | NULL                             | Calculated protein       |
| fat      | DECIMAL(8,2) | NULL                             | Calculated fat           |
| carbs    | DECIMAL(8,2) | NULL                             | Calculated carbohydrates |
| added_at | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP        | Addition date            |

#### daily_summaries

| Column          | Type         | Constraints                                           | Description                  |
| --------------- | ------------ | ----------------------------------------------------- | ---------------------------- |
| id              | INTEGER      | PRIMARY KEY, AUTO_INCREMENT                           | Summary identifier           |
| user_id         | INTEGER      | FOREIGN KEY (users.id), NOT NULL                      | Reference to user            |
| date            | DATE         | NOT NULL                                              | Summary date                 |
| total_calories  | DECIMAL(8,2) | DEFAULT 0                                             | Total calories consumed      |
| total_protein   | DECIMAL(8,2) | DEFAULT 0                                             | Total protein consumed       |
| total_fat       | DECIMAL(8,2) | DEFAULT 0                                             | Total fat consumed           |
| total_carbs     | DECIMAL(8,2) | DEFAULT 0                                             | Total carbohydrates consumed |
| total_fiber     | DECIMAL(8,2) | DEFAULT 0                                             | Total fiber consumed         |
| weight_recorded | DECIMAL(5,2) | NULL                                                  | Weight recorded for the day  |
| created_at      | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP                             | Creation date                |
| updated_at      | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Last update                  |

### 4. Image Processing & Recognition

#### uploaded_images

| Column            | Type         | Constraints                      | Description                                  |
| ----------------- | ------------ | -------------------------------- | -------------------------------------------- |
| id                | INTEGER      | PRIMARY KEY, AUTO_INCREMENT      | Image identifier                             |
| user_id           | INTEGER      | FOREIGN KEY (users.id), NOT NULL | Reference to user                            |
| meal_id           | INTEGER      | FOREIGN KEY (meals.id), NULL     | Associated meal                              |
| filename          | VARCHAR(255) | NOT NULL                         | Original filename                            |
| file_path         | VARCHAR(500) | NOT NULL                         | Storage path                                 |
| file_size         | INTEGER      | NOT NULL                         | File size in bytes                           |
| mime_type         | VARCHAR(100) | NOT NULL                         | Image MIME type                              |
| width             | INTEGER      | NULL                             | Image width                                  |
| height            | INTEGER      | NULL                             | Image height                                 |
| processing_status | VARCHAR(20)  | DEFAULT 'pending'                | Status (pending/processing/completed/failed) |
| uploaded_at       | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP        | Upload date                                  |
| processed_at      | TIMESTAMP    | NULL                             | Processing completion date                   |

#### food_recognition_results

| Column             | Type         | Constraints                                | Description                  |
| ------------------ | ------------ | ------------------------------------------ | ---------------------------- |
| id                 | INTEGER      | PRIMARY KEY, AUTO_INCREMENT                | Result identifier            |
| image_id           | INTEGER      | FOREIGN KEY (uploaded_images.id), NOT NULL | Reference to image           |
| food_id            | INTEGER      | FOREIGN KEY (foods.id), NULL               | Recognized food              |
| confidence_score   | DECIMAL(5,4) | NOT NULL                                   | Recognition confidence (0-1) |
| estimated_quantity | DECIMAL(8,2) | NULL                                       | Estimated quantity in grams  |
| is_confirmed       | BOOLEAN      | DEFAULT FALSE                              | User confirmation status     |
| created_at         | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP                  | Creation date                |

### 5. System & Logging

#### food_search_logs

| Column        | Type         | Constraints                  | Description                |
| ------------- | ------------ | ---------------------------- | -------------------------- |
| id            | INTEGER      | PRIMARY KEY, AUTO_INCREMENT  | Log identifier             |
| user_id       | INTEGER      | FOREIGN KEY (users.id), NULL | Reference to user          |
| search_query  | VARCHAR(500) | NOT NULL                     | Search query text          |
| results_count | INTEGER      | DEFAULT 0                    | Number of results returned |
| search_type   | VARCHAR(20)  | NOT NULL                     | Type (text/image/barcode)  |
| created_at    | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP    | Search date                |

#### user_activity_logs

| Column        | Type         | Constraints                      | Description              |
| ------------- | ------------ | -------------------------------- | ------------------------ |
| id            | INTEGER      | PRIMARY KEY, AUTO_INCREMENT      | Log identifier           |
| user_id       | INTEGER      | FOREIGN KEY (users.id), NOT NULL | Reference to user        |
| activity_type | VARCHAR(50)  | NOT NULL                         | Activity type            |
| activity_data | JSON         | NULL                             | Additional activity data |
| ip_address    | VARCHAR(45)  | NULL                             | User's IP address        |
| user_agent    | VARCHAR(500) | NULL                             | User's browser info      |
| created_at    | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP        | Activity date            |

## Indexes

### Performance Indexes

```sql
-- User lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- Food searches
CREATE INDEX idx_foods_name ON foods(name);
CREATE INDEX idx_foods_category ON foods(category_id);
CREATE INDEX idx_food_aliases_alias ON food_aliases(alias);

-- Meal queries
CREATE INDEX idx_meals_user_date ON meals(user_id, date);
CREATE INDEX idx_meals_user_type ON meals(user_id, meal_type);
CREATE INDEX idx_meal_foods_meal ON meal_foods(meal_id);

-- Daily summaries
CREATE INDEX idx_daily_summaries_user_date ON daily_summaries(user_id, date);

-- Image processing
CREATE INDEX idx_uploaded_images_user ON uploaded_images(user_id);
CREATE INDEX idx_uploaded_images_status ON uploaded_images(processing_status);
CREATE INDEX idx_recognition_results_image ON food_recognition_results(image_id);

-- Logging
CREATE INDEX idx_search_logs_user ON food_search_logs(user_id);
CREATE INDEX idx_activity_logs_user ON user_activity_logs(user_id);
CREATE INDEX idx_activity_logs_type ON user_activity_logs(activity_type);
```

## Data Relationships

### Key Relationships

-   Users have one profile (1:1)
-   Users can have multiple meals (1:N)
-   Users can have multiple daily summaries (1:N)
-   Meals can contain multiple foods (N:M via meal_foods)
-   Foods can belong to categories (N:1)
-   Foods can have multiple aliases (1:N)
-   Users can upload multiple images (1:N)
-   Images can have multiple recognition results (1:N)

### Cascade Rules

-   When a user is deleted: CASCADE delete profile, meals, summaries, images
-   When a meal is deleted: CASCADE delete meal_foods entries
-   When a food is deleted: SET NULL in meal_foods, recognition_results
-   When an image is deleted: CASCADE delete recognition_results
