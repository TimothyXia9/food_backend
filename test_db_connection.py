#!/usr/bin/env python
"""
Simple database connection test script for Railway debugging
"""
import os
import sys
import django

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calorie_tracker.settings')
django.setup()

from django.db import connection
from django.conf import settings

def test_database_connection():
    print("=== Database Connection Test ===")
    
    # Print database configuration
    db_config = settings.DATABASES['default']
    print(f"Engine: {db_config.get('ENGINE', 'Not set')}")
    print(f"Name: {db_config.get('NAME', 'Not set')}")
    print(f"Host: {db_config.get('HOST', 'Not set')}")
    print(f"Port: {db_config.get('PORT', 'Not set')}")
    print(f"User: {db_config.get('USER', 'Not set')}")
    
    # Print environment variables
    print("\n=== Environment Variables ===")
    for key in ['DATABASE_URL', 'PGHOST', 'PGDATABASE', 'PGUSER', 'PGPORT', 'RAILWAY_ENVIRONMENT']:
        value = os.environ.get(key, 'Not set')
        if 'PASSWORD' in key:
            value = '[HIDDEN]' if value != 'Not set' else 'Not set'
        print(f"{key}: {value}")
    
    # Test connection
    print("\n=== Connection Test ===")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            result = cursor.fetchone()
            print(f"✅ Database connection successful!")
            print(f"PostgreSQL version: {result[0]}")
            
            # Test basic query
            cursor.execute("SELECT NOW()")
            now = cursor.fetchone()
            print(f"Current time: {now[0]}")
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Additional debugging
        if "could not translate host name" in str(e):
            print("\n🔍 DNS Resolution Issue Detected:")
            print("- The PostgreSQL service might not be running")
            print("- The DATABASE_URL might be incorrect")
            print("- Railway internal DNS might not be working")
            print("\n💡 Solutions:")
            print("1. Check if PostgreSQL service is deployed in Railway")
            print("2. Verify DATABASE_URL environment variable")
            print("3. Check Railway service dependencies")

if __name__ == "__main__":
    test_database_connection()