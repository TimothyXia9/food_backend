"""
Barcode Detection Service
Uses computer vision to detect barcodes in images
"""

import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import cv2
    import numpy as np
    from PIL import Image
    from pyzbar import pyzbar
    BARCODE_DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Barcode detection dependencies not available: {e}")
    cv2 = None
    np = None
    Image = None
    pyzbar = None
    BARCODE_DEPENDENCIES_AVAILABLE = False


class BarcodeDetectionService:
    """Service for detecting barcodes in images using computer vision"""

    def __init__(self):
        """Initialize barcode detection service"""
        self.supported_formats = [
            "EAN13", "EAN8", "UPCA", "UPCE", "CODE128", "CODE39", 
            "ITF", "CODABAR", "PDF417", "QRCODE", "DATAMATRIX"
        ]
        self.dependencies_available = BARCODE_DEPENDENCIES_AVAILABLE
        
        if not self.dependencies_available:
            logger.warning("Barcode detection service initialized without required dependencies")

    def _check_dependencies(self):
        """Check if dependencies are available"""
        if not self.dependencies_available:
            raise ImportError(
                "Barcode detection dependencies are not available. "
                "Please install opencv-python, pyzbar and system libzbar library: "
                "sudo apt-get install libzbar0 libzbar-dev"
            )

    def detect_barcodes_from_path(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Detect barcodes from image file path
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of detected barcodes with their data and metadata
        """
        try:
            self._check_dependencies()
            
            if not os.path.exists(image_path):
                logger.error(f"Image file not found: {image_path}")
                return []

            # Read image using OpenCV
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to load image: {image_path}")
                return []

            return self._detect_barcodes_from_array(image)

        except ImportError as e:
            logger.error(f"Barcode detection dependencies not available: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error detecting barcodes from path: {str(e)}")
            return []

    def detect_barcodes_from_pil(self, pil_image) -> List[Dict[str, Any]]:
        """
        Detect barcodes from PIL Image object
        
        Args:
            pil_image: PIL Image object
            
        Returns:
            List of detected barcodes with their data and metadata
        """
        try:
            self._check_dependencies()
            
            # Convert PIL to OpenCV format
            image_array = np.array(pil_image)
            
            # Convert RGB to BGR for OpenCV
            if len(image_array.shape) == 3:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)

            return self._detect_barcodes_from_array(image_array)

        except ImportError as e:
            logger.error(f"Barcode detection dependencies not available: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error detecting barcodes from PIL image: {str(e)}")
            return []

    def _detect_barcodes_from_array(self, image) -> List[Dict[str, Any]]:
        """
        Detect barcodes from OpenCV image array
        
        Args:
            image: OpenCV image array (BGR format)
            
        Returns:
            List of detected barcodes with their data and metadata
        """
        try:
            # Convert to grayscale for better barcode detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply different preprocessing techniques
            processed_images = [
                gray,  # Original grayscale
                self._enhance_contrast(gray),  # Enhanced contrast
                self._gaussian_blur(gray),     # Gaussian blur
                self._threshold_image(gray),   # Binary threshold
            ]
            
            all_barcodes = []
            
            # Try detection on each processed version
            for processed_image in processed_images:
                barcodes = pyzbar.decode(processed_image)
                
                for barcode in barcodes:
                    barcode_data = self._format_barcode_data(barcode)
                    
                    # Avoid duplicates
                    if not any(existing['data'] == barcode_data['data'] for existing in all_barcodes):
                        all_barcodes.append(barcode_data)
            
            logger.info(f"Detected {len(all_barcodes)} unique barcodes")
            return all_barcodes

        except Exception as e:
            logger.error(f"Error in barcode detection: {str(e)}")
            return []

    def _enhance_contrast(self, image):
        """Enhance image contrast using CLAHE"""
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(image)
        except Exception:
            return image

    def _gaussian_blur(self, image):
        """Apply Gaussian blur to reduce noise"""
        try:
            return cv2.GaussianBlur(image, (3, 3), 0)
        except Exception:
            return image

    def _threshold_image(self, image):
        """Apply adaptive threshold"""
        try:
            return cv2.adaptiveThreshold(
                image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
        except Exception:
            return image

    def _format_barcode_data(self, barcode) -> Dict[str, Any]:
        """
        Format barcode detection result into standard dictionary
        
        Args:
            barcode: pyzbar.Decoded object
            
        Returns:
            Formatted barcode data dictionary
        """
        try:
            # Extract barcode data
            barcode_data = barcode.data.decode('utf-8')
            barcode_type = barcode.type
            
            # Get bounding box coordinates
            rect = barcode.rect
            
            # Calculate polygon points if available
            polygon_points = []
            if hasattr(barcode, 'polygon') and barcode.polygon:
                polygon_points = [(point.x, point.y) for point in barcode.polygon]
            
            return {
                'data': barcode_data,
                'type': barcode_type,
                'quality': barcode.quality if hasattr(barcode, 'quality') else None,
                'orientation': barcode.orientation if hasattr(barcode, 'orientation') else None,
                'rect': {
                    'left': rect.left,
                    'top': rect.top,
                    'width': rect.width,
                    'height': rect.height
                },
                'polygon': polygon_points,
                'is_food_barcode': self._is_food_barcode(barcode_data, barcode_type),
                'formatted_data': self._format_barcode_for_display(barcode_data, barcode_type)
            }
            
        except Exception as e:
            logger.error(f"Error formatting barcode data: {str(e)}")
            return {
                'data': str(barcode.data),
                'type': str(barcode.type),
                'error': str(e)
            }

    def _is_food_barcode(self, data: str, barcode_type: str) -> bool:
        """
        Determine if barcode is likely a food product barcode
        
        Args:
            data: Barcode data string
            barcode_type: Type of barcode (EAN13, UPCA, etc.)
            
        Returns:
            True if likely a food product barcode
        """
        try:
            # Common food product barcode types
            food_barcode_types = ["EAN13", "EAN8", "UPCA", "UPCE"]
            
            if barcode_type not in food_barcode_types:
                return False
            
            # Check barcode length and format
            if barcode_type in ["EAN13", "UPCA"] and len(data) in [12, 13]:
                return True
            elif barcode_type in ["EAN8", "UPCE"] and len(data) in [7, 8]:
                return True
            
            return False
            
        except Exception:
            return False

    def _format_barcode_for_display(self, data: str, barcode_type: str) -> str:
        """
        Format barcode data for display
        
        Args:
            data: Raw barcode data
            barcode_type: Type of barcode
            
        Returns:
            Formatted barcode string
        """
        try:
            if barcode_type == "EAN13" and len(data) == 13:
                # Format as: 1-234567-890123
                return f"{data[0]}-{data[1:7]}-{data[7:13]}"
            elif barcode_type == "UPCA" and len(data) == 12:
                # Format as: 123456-789012
                return f"{data[:6]}-{data[6:12]}"
            elif barcode_type == "EAN8" and len(data) == 8:
                # Format as: 1234-5678
                return f"{data[:4]}-{data[4:8]}"
            else:
                return data
        except Exception:
            return data

    def get_supported_formats(self) -> List[str]:
        """Get list of supported barcode formats"""
        return self.supported_formats.copy()

    def validate_barcode_data(self, data: str, barcode_type: str) -> Dict[str, Any]:
        """
        Validate barcode data integrity
        
        Args:
            data: Barcode data string
            barcode_type: Type of barcode
            
        Returns:
            Validation result with success status and details
        """
        try:
            result = {
                "is_valid": False,
                "barcode_type": barcode_type,
                "data": data,
                "errors": []
            }
            
            # Basic length validation
            expected_lengths = {
                "EAN13": [13],
                "EAN8": [8],
                "UPCA": [12],
                "UPCE": [6, 7, 8],
                "CODE128": None,  # Variable length
                "CODE39": None,   # Variable length
            }
            
            if barcode_type in expected_lengths:
                expected = expected_lengths[barcode_type]
                if expected and len(data) not in expected:
                    result["errors"].append(f"Invalid length for {barcode_type}: expected {expected}, got {len(data)}")
                    return result
            
            # Check if data contains only digits for UPC/EAN
            if barcode_type in ["EAN13", "EAN8", "UPCA", "UPCE"]:
                if not data.isdigit():
                    result["errors"].append(f"{barcode_type} should contain only digits")
                    return result
            
            result["is_valid"] = True
            return result
            
        except Exception as e:
            return {
                "is_valid": False,
                "barcode_type": barcode_type,
                "data": data,
                "errors": [f"Validation error: {str(e)}"]
            }