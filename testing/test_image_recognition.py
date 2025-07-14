"""
Test script for image recognition using OpenAI GPT-4V API
"""

import os
import json
import base64
from pathlib import Path
from openai import OpenAI
from decouple import config

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
# Ensure the OpenAI API key is set
if not config("OPENAI_API_KEY"):
    raise ValueError(
        "OPENAI_API_KEY not found in environment variables. Please set it in a .env file or as an environment variable."
    )


# Load the food prompt
def load_food_prompt():
    prompt_path = Path(__file__).parent / "food_prompt.txt"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


# Convert image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# Test image recognition
def test_image_recognition(image_path, api_key=None):
    """
    Test image recognition using OpenAI GPT-4V

    Args:
            image_path (str): Path to the image file
            api_key (str): OpenAI API key (optional, will try env vars)

    Returns:
            dict: Recognition results in JSON format
    """

    # Initialize OpenAI client
    if api_key:
        client = OpenAI(api_key=api_key)
    else:
        # Try to get from environment variables
        api_key = config("OPENAI_API_KEY", default=None)
        if not api_key:
            print(
                "Error: OPENAI_API_KEY not found. Set it as environment variable or pass as parameter"
            )
            return None
        client = OpenAI(api_key=api_key)

    # Load prompt
    food_prompt = load_food_prompt()

    # Encode image
    try:
        base64_image = encode_image(image_path)
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None

    # Make API call
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Use gpt-4o which supports vision
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": food_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=1000,
            temperature=0.1,
        )

        # Parse response
        result_text = response.choices[0].message.content

        # Try to extract JSON from response
        try:
            # Find JSON in the response
            import re

            json_match = re.search(r"\{.*\}", result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
            else:
                result = {
                    "error": "No JSON found in response",
                    "raw_response": result_text,
                }
        except json.JSONDecodeError:
            result = {"error": "Invalid JSON in response", "raw_response": result_text}

        return result

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None


# Main test function
def main():
    print("🍎 Food Image Recognition Test")
    print("=" * 40)

    # Check if test image exists
    test_image_dir = Path(__file__).parent / "test_images"
    if not test_image_dir.exists():
        print(f"Creating test_images directory: {test_image_dir}")
        test_image_dir.mkdir()
        print("Please add some test images to the test_images/ directory")
        return

    # Find test images
    image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".gif"]
    test_images = []
    for ext in image_extensions:
        test_images.extend(test_image_dir.glob(f"*{ext}"))
        test_images.extend(test_image_dir.glob(f"*{ext.upper()}"))

    if not test_images:
        print("No test images found. Please add images to the test_images/ directory")
        print(f"Supported formats: {', '.join(image_extensions)}")
        return

    print(f"Found {len(test_images)} test image(s)")

    # Test each image
    for image_path in test_images:
        print(f"\n📸 Testing image: {image_path.name}")
        print("-" * 30)

        result = test_image_recognition(str(image_path))

        if result:
            print("✅ Recognition successful!")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("❌ Recognition failed!")


if __name__ == "__main__":
    main()
