#!/usr/bin/env python3
"""
Debug script to check barcode detection dependencies
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calorie_tracker.settings')
django.setup()

def test_system_libraries():
    """Test if system libraries are available"""
    print("=== Testing System Libraries ===")
    
    # Test libzbar0
    try:
        import ctypes
        libzbar = ctypes.CDLL('libzbar.so.0')
        print("✓ libzbar.so.0 is available")
    except Exception as e:
        print(f"✗ libzbar.so.0 error: {e}")
    
    # Test if zbar command exists
    import subprocess
    try:
        result = subprocess.run(['which', 'zbarimg'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ zbarimg command found at: {result.stdout.strip()}")
        else:
            print("✗ zbarimg command not found")
    except Exception as e:
        print(f"✗ zbarimg command error: {e}")

def test_python_dependencies():
    """Test if Python dependencies can be imported"""
    print("\n=== Testing Python Dependencies ===")
    
    # Test OpenCV
    try:
        import cv2
        print(f"✓ OpenCV version: {cv2.__version__}")
    except ImportError as e:
        print(f"✗ OpenCV import error: {e}")
    
    # Test NumPy
    try:
        import numpy as np
        print(f"✓ NumPy version: {np.__version__}")
    except ImportError as e:
        print(f"✗ NumPy import error: {e}")
    
    # Test PIL
    try:
        from PIL import Image
        print(f"✓ PIL version: {Image.__version__}")
    except ImportError as e:
        print(f"✗ PIL import error: {e}")
    
    # Test pyzbar
    try:
        from pyzbar import pyzbar
        print("✓ pyzbar imported successfully")
        
        # Test pyzbar with a simple decode
        try:
            # This should not crash even with empty input
            result = pyzbar.decode(b'')
            print(f"✓ pyzbar decode function works, result: {result}")
        except Exception as e:
            print(f"✗ pyzbar decode error: {e}")
            
    except ImportError as e:
        print(f"✗ pyzbar import error: {e}")

def test_barcode_service():
    """Test the actual barcode service"""
    print("\n=== Testing Barcode Service ===")
    
    try:
        from images.barcode_service import BarcodeDetectionService
        service = BarcodeDetectionService()
        print(f"✓ BarcodeDetectionService created")
        print(f"  - Dependencies available: {service.dependencies_available}")
        print(f"  - Supported formats: {service.supported_formats}")
        
        if service.dependencies_available:
            print("✓ All dependencies are available for barcode detection")
        else:
            print("✗ Some dependencies are missing")
            
    except Exception as e:
        print(f"✗ BarcodeDetectionService error: {e}")
        import traceback
        traceback.print_exc()

def test_django_import():
    """Test if Django models can be imported"""
    print("\n=== Testing Django Integration ===")
    
    try:
        from images.models import UploadedImage
        print("✓ UploadedImage model imported")
    except Exception as e:
        print(f"✗ UploadedImage model error: {e}")
    
    try:
        from images.views import detect_barcodes
        print("✓ detect_barcodes view imported")
    except Exception as e:
        print(f"✗ detect_barcodes view error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Barcode Detection Dependency Debug Script")
    print("=" * 50)
    
    test_system_libraries()
    test_python_dependencies()
    test_barcode_service()
    test_django_import()
    
    print("\n=== Summary ===")
    print("If all tests pass with ✓, barcode detection should work.")
    print("If any tests fail with ✗, those are the issues to fix.")