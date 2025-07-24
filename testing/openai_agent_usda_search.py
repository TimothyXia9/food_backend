"""
OpenAI Agent for USDA Food Search
Uses OpenAI API as an intelligent agent to find the best matching foods in USDA database
"""

import asyncio
import json
import base64
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiohttp
from decouple import config
from dotenv import load_dotenv

# Import existing services
from usda_nutrition import USDANutritionAPI, format_nutrition_info

# Load environment variables
load_dotenv()


def load_config(config_path: str = None) -> Dict[str, Any]:
	"""Load configuration from JSON file"""
	if config_path is None:
		config_path = Path(__file__).parent / "config.json"
	
	try:
		with open(config_path, 'r', encoding='utf-8') as f:
			return json.load(f)
	except FileNotFoundError:
		print(f"⚠️  Config file not found: {config_path}")
		print("Using default configuration...")
		return get_default_config()
	except json.JSONDecodeError as e:
		print(f"⚠️  Invalid JSON in config file: {e}")
		print("Using default configuration...")
		return get_default_config()


def get_default_config() -> Dict[str, Any]:
	"""Get default configuration if config file is not available"""
	return {
		"openai": {
			"model": "gpt-4o",
			"temperature": 0.1,
			"max_iterations": 10,
			"timeout_seconds": 60
		},
		"usda_search": {
			"default_page_size": 25,
			"max_page_size": 100
		},
		"logging": {
			"enable_debug": True,
			"show_function_calls": True,
			"show_timing": True
		}
	}


class OpenAIUSDAAgent:
    """OpenAI Agent that intelligently searches USDA database for food matches"""

    def __init__(self, config_path: str = None):
        print("🤖 Initializing OpenAI USDA Agent...")

        # Load configuration
        self.config = load_config(config_path)
        
        # Load OpenAI API keys
        api_keys_str = config("OPENAI_API_KEYS", default="[]", cast=str)
        try:
            self.api_keys = json.loads(api_keys_str)
        except json.JSONDecodeError:
            single_key = config("OPENAI_API_KEY", default=None)
            if single_key:
                self.api_keys = [single_key]
            else:
                raise ValueError("No OpenAI API keys found")

        if not self.api_keys:
            raise ValueError("No OpenAI API keys found")

        self.current_key_index = 0

        # Initialize USDA service
        self.usda_service = USDANutritionAPI()

        # OpenAI API configuration
        self.base_url = "https://api.openai.com/v1"

        print(f"✅ Agent initialized with {len(self.api_keys)} API key(s)")
        if self.config["logging"]["enable_debug"]:
            print(f"🔧 Configuration loaded:")
            print(f"   - Model: {self.config['openai']['model']}")
            print(f"   - Default page size: {self.config['usda_search']['default_page_size']}")
            print(f"   - Max iterations: {self.config['openai']['max_iterations']}")

    def _get_current_api_key(self):
        """Get current API key"""
        return self.api_keys[self.current_key_index]

    def _rotate_api_key(self):
        """Rotate to next API key"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        print(
            f"🔄 Rotated to API key {self.current_key_index + 1}/{len(self.api_keys)}"
        )

    def search_usda_tool(self, query: str, page_size: int = None) -> Dict[str, Any]:
        """Tool function for OpenAI to search USDA database"""
        if page_size is None:
            page_size = self.config['usda_search']['default_page_size']
        
        # Ensure page_size doesn't exceed max
        max_page_size = self.config['usda_search']['max_page_size']
        if page_size > max_page_size:
            page_size = max_page_size
            
        if self.config["logging"]["enable_debug"]:
            print(f"🔍 Agent searching USDA: '{query}' (page_size: {page_size})")

        try:
            results = self.usda_service.search_foods(query, page_size=page_size)

            if results and results.get("foods"):
                foods = results["foods"]
                # Return simplified results for the agent
                simplified_foods = []
                for food in foods:
                    simplified_foods.append(
                        {
                            "fdc_id": food.get("fdcId"),
                            "description": food.get("description"),
                            "data_type": food.get("dataType"),
                            "brand_owner": food.get("brandOwner", ""),
                        }
                    )

                return {
                    "success": True,
                    "total_results": len(simplified_foods),
                    "foods": simplified_foods,
                }
            else:
                return {
                    "success": False,
                    "message": f"No results found for query: {query}",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_food_nutrition_tool(self, fdc_id: int) -> Dict[str, Any]:
        """Tool function for OpenAI to get detailed nutrition information"""
        if self.config["logging"]["enable_debug"]:
            print(f"📊 Agent getting nutrition for FDC ID: {fdc_id}")

        try:
            detailed_info = self.usda_service.get_food_details(fdc_id)
            nutrition_info = format_nutrition_info(detailed_info)

            if nutrition_info:
                return {"success": True, "nutrition_data": nutrition_info}
            else:
                return {
                    "success": False,
                    "message": f"No nutrition data found for FDC ID: {fdc_id}",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_function_definitions(self):
        """Get function definitions for OpenAI function calling"""
        if "function_definitions" in self.config:
            # Use definitions from config file
            config_functions = self.config["function_definitions"]
            return [
                config_functions.get("search_usda_database", {}),
                config_functions.get("get_food_nutrition", {})
            ]
        else:
            # Fallback to hardcoded definitions
            return [
                {
                    "name": "search_usda_database",
                    "description": "Search the USDA FoodData Central database for foods. Use specific food names and cooking methods for better results. Request 25 results by default for comprehensive search.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for food (e.g., 'chicken breast raw', 'broccoli steamed', 'apple')",
                            },
                            "page_size": {
                                "type": "integer",
                                "description": "Number of results to return (default 25, max 100)",
                                "default": 25,
                            },
                        },
                        "required": ["query"],
                    },
                },
                {
                    "name": "get_food_nutrition",
                    "description": "Get detailed nutrition information for a specific food using its FDC ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "fdc_id": {
                                "type": "integer",
                                "description": "The FDC ID of the food item from USDA database",
                            }
                        },
                        "required": ["fdc_id"],
                    },
                },
            ]

    async def _call_openai_with_tools(
        self, messages: List[Dict], max_iterations: int = None
    ):
        """Call OpenAI with function calling capability"""

        if max_iterations is None:
            max_iterations = self.config['openai']['max_iterations']

        headers = {
            "Authorization": f"Bearer {self._get_current_api_key()}",
            "Content-Type": "application/json",
        }

        functions = self._get_function_definitions()

        conversation_history = messages.copy()

        timeout_seconds = self.config['openai']['timeout_seconds']

        async with aiohttp.ClientSession() as session:
            for iteration in range(max_iterations):
                if self.config["logging"]["enable_debug"]:
                    print(f"🔄 OpenAI iteration {iteration + 1}/{max_iterations}")

                payload = {
                    "model": self.config['openai']['model'],
                    "messages": conversation_history,
                    "functions": functions,
                    "function_call": "auto",
                    "temperature": self.config['openai']['temperature'],
                }

                try:
                    async with session.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout_seconds),
                    ) as response:

                        if response.status == 429:
                            print("⚠️  Rate limit, rotating API key...")
                            self._rotate_api_key()
                            headers["Authorization"] = (
                                f"Bearer {self._get_current_api_key()}"
                            )
                            continue

                        response.raise_for_status()
                        result = await response.json()

                        message = result["choices"][0]["message"]
                        conversation_history.append(message)

                        # Check if the model wants to call a function
                        if message.get("function_call"):
                            function_name = message["function_call"]["name"]
                            function_args = json.loads(
                                message["function_call"]["arguments"]
                            )

                            if self.config["logging"]["show_function_calls"]:
                                print(
                                    f"🛠️  Agent calling function: {function_name} with args: {function_args}"
                                )

                            # Call the appropriate function
                            if function_name == "search_usda_database":
                                function_result = self.search_usda_tool(**function_args)
                            elif function_name == "get_food_nutrition":
                                function_result = self.get_food_nutrition_tool(
                                    **function_args
                                )
                            else:
                                function_result = {
                                    "error": f"Unknown function: {function_name}"
                                }

                            # Add function result to conversation
                            conversation_history.append(
                                {
                                    "role": "function",
                                    "name": function_name,
                                    "content": json.dumps(function_result),
                                }
                            )

                        else:
                            # Model has finished, return the final response
                            return {
                                "success": True,
                                "final_response": message["content"],
                                "conversation_history": conversation_history,
                            }

                except Exception as e:
                    print(f"❌ OpenAI API error: {e}")
                    return {"success": False, "error": str(e)}

            return {
                "success": False,
                "error": "Maximum iterations reached without completion",
            }

    async def analyze_food_image_with_agent(self, image_path: str) -> Dict[str, Any]:
        """Analyze food image using OpenAI agent to find best USDA matches"""

        if self.config["logging"]["enable_debug"]:
            print(f"📸 Agent analyzing image: {Path(image_path).name}")

        # Encode image
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            return {"success": False, "error": f"Failed to encode image: {e}"}

        # Get system message from config or use default
        system_message = self.config.get("system_messages", {}).get(
            "food_analysis_prompt", 
            "You are an expert food nutrition analyst with access to the USDA FoodData Central database."
        )

        # User message with image
        user_message = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Please analyze this food image and find the best matching nutrition data from USDA. Use the available tools to search and get detailed nutrition information.",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ],
        }

        messages = [{"role": "system", "content": system_message}, user_message]

        # Let the agent work
        result = await self._call_openai_with_tools(messages)

        if result["success"]:
            try:
                # Try to parse the JSON response
                final_response = result["final_response"]

                # Extract JSON from response if it's mixed with text
                import re

                json_match = re.search(r"\{.*\}", final_response, re.DOTALL)
                if json_match:
                    nutrition_data = json.loads(json_match.group())
                    return {
                        "success": True,
                        "nutrition_analysis": nutrition_data,
                        "agent_response": final_response,
                        "conversation_history": result["conversation_history"],
                    }
                else:
                    return {
                        "success": True,
                        "agent_response": final_response,
                        "conversation_history": result["conversation_history"],
                        "note": "Could not extract structured JSON from response",
                    }

            except json.JSONDecodeError:
                return {
                    "success": True,
                    "agent_response": result["final_response"],
                    "conversation_history": result["conversation_history"],
                    "note": "Response is not in JSON format",
                }
        else:
            return result


# Test functions
async def test_agent_analysis(agent: OpenAIUSDAAgent, image_path: str):
    """Test the OpenAI agent food analysis"""
    if agent.config["logging"]["enable_debug"]:
        print(f"🧪 Testing agent analysis: {Path(image_path).name}")

    import time
    start_time = time.time()

    result = await agent.analyze_food_image_with_agent(image_path)

    end_time = time.time()
    if agent.config["logging"]["show_timing"]:
        print(f"⏱️  Total processing time: {end_time - start_time:.2f} seconds")

    if result["success"]:
        print("✅ Agent analysis successful!")

        if "nutrition_analysis" in result:
            print("\n📊 Structured Nutrition Analysis:")
            nutrition = result["nutrition_analysis"]

            if "foods_identified" in nutrition:
                for i, food in enumerate(nutrition["foods_identified"], 1):
                    print(f"\n{i}. {food.get('name', 'Unknown')}")
                    print(f"   Weight: {food.get('estimated_weight_grams', 'N/A')}g")
                    print(f"   Method: {food.get('cooking_method', 'N/A')}")
                    print(f"   Confidence: {food.get('confidence', 0):.1%}")

                    if "usda_match" in food:
                        match = food["usda_match"]
                        print(f"   🥇 USDA Match: {match.get('description', 'N/A')}")
                        print(f"      FDC ID: {match.get('fdc_id', 'N/A')}")
                        print(
                            f"      Match Confidence: {match.get('match_confidence', 0):.1%}"
                        )

                    if "nutrition_per_portion" in food:
                        nutrition_per_portion = food["nutrition_per_portion"]
                        print(f"   📈 Nutrition:")
                        for nutrient, amount in nutrition_per_portion.items():
                            print(f"     • {nutrient}: {amount}")

            if "total_nutrition" in nutrition:
                print(f"\n🧮 Total Nutrition:")
                total = nutrition["total_nutrition"]
                for nutrient, amount in total.items():
                    print(f"  • {nutrient}: {amount}")

        print(f"\n🤖 Agent Response:")
        print(result["agent_response"])

        if agent.config["logging"]["show_function_calls"]:
            print(f"\n📝 Function Calls Made:")
            function_calls = 0
            for msg in result.get("conversation_history", []):
                if msg.get("role") == "assistant" and msg.get("function_call"):
                    function_calls += 1
                    func_name = msg["function_call"]["name"]
                    func_args = msg["function_call"]["arguments"]
                    print(f"  {function_calls}. {func_name}: {func_args}")

    else:
        print("❌ Agent analysis failed!")
        print(f"Error: {result.get('error', 'Unknown error')}")

    return result


async def main():
    """Main test function"""
    print("🤖 OpenAI USDA Agent Test")
    print("=" * 50)

    try:
        # Initialize agent
        agent = OpenAIUSDAAgent()

        # Check for test images
        test_image_dir = Path(__file__).parent / "test_images"
        if not test_image_dir.exists():
            print("❌ No test_images directory found")
            return

        image_files = (
            list(test_image_dir.glob("*.jpg"))
            + list(test_image_dir.glob("*.jpeg"))
            + list(test_image_dir.glob("*.png"))
        )

        if not image_files:
            print("❌ No images found in test_images directory")
            return

        print(f"📸 Found {len(image_files)} test images")

        # Test with first image
        if image_files:
            await test_agent_analysis(agent, str(image_files[0]))

        print("\n🎉 Agent test completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
