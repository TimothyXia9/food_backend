"""
Two-Stage Food Analysis System (Refactored)
Stage 1: Food Identification - Fast food detection and portion estimation
Stage 2: Nutrition Lookup - Parallel USDA nutrition data retrieval

This version uses the centralized OpenAI service for better API key management.
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Import OpenAI service and USDA service
from .openai_service import get_openai_service
from foods.usda_nutrition import USDANutritionAPI, format_nutrition_info


def load_config(config_path: str = None) -> Dict[str, Any]:
	"""Load configuration from JSON file"""
	if config_path is None:
		config_path = Path(__file__).parent.parent / "testing" / "config_two_stage.json"
	
	try:
		with open(config_path, 'r', encoding='utf-8') as f:
			return json.load(f)
	except FileNotFoundError:
		print(f"⚠️  Config file not found: {config_path}")
		print("Using default two-stage configuration...")
		return get_default_two_stage_config()
	except json.JSONDecodeError as e:
		print(f"⚠️  Invalid JSON in config file: {e}")
		print("Using default two-stage configuration...")
		return get_default_two_stage_config()


def get_default_two_stage_config() -> Dict[str, Any]:
	"""Get default two-stage configuration"""
	return {
		"openai": {
			"model": "gpt-4o",
			"temperature": 0.1,
			"max_iterations": 5,
			"timeout_seconds": 60
		},
		"usda_search": {
			"default_page_size": 25,
			"max_page_size": 100
		},
		"stages": {
			"food_identification": {
				"max_iterations": 3,
				"temperature": 0.2,
				"timeout_seconds": 30
			},
			"nutrition_lookup": {
				"max_iterations": 5,
				"temperature": 0.0,
				"timeout_seconds": 45,
				"parallel_agents": 3,
				"max_concurrent_foods": 5
			}
		},
		"logging": {
			"enable_debug": True,
			"show_function_calls": True,
			"show_timing": True,
			"show_stage_progress": True
		}
	}


class FoodIdentificationAgent:
	"""Stage 1: Specialized agent for food identification only"""
	
	def __init__(self, config: Dict[str, Any]):
		self.config = config
		self.openai_service = get_openai_service()
		
		if self.config["logging"]["enable_debug"]:
			print("🔍 Food Identification Agent initialized")
	
	async def identify_foods_in_image(self, image_path: str) -> Dict[str, Any]:
		"""Stage 1: Identify foods in image without nutrition lookup"""
		
		stage_start = time.time()
		
		if self.config["logging"]["show_stage_progress"]:
			print(f"🔍 Stage 1: Identifying foods in {Path(image_path).name}")
		
		# Get system message from config
		system_message = self.config.get("system_messages", {}).get(
			"food_identification_prompt",
			"Identify all foods in the image and estimate their portions."
		)
		
		# Get stage-specific config
		stage_config = self.config["stages"]["food_identification"]
		
		# Create messages
		messages = [
			{"role": "system", "content": system_message}
		]
		
		# Call OpenAI for food identification
		result = await self.openai_service.vision_completion(
			image_path=image_path,
			prompt="Please identify all foods in this image and estimate their portions. Do not search for nutrition data.",
			model=self.config["openai"]["model"],
			temperature=stage_config["temperature"],
			max_tokens=1000,
			timeout=stage_config["timeout_seconds"]
		)
		
		stage_end = time.time()
		
		if self.config["logging"]["show_timing"]:
			print(f"⏱️  Stage 1 completed in {stage_end - stage_start:.2f} seconds")
		
		if result["success"]:
			# Try to parse JSON from response
			try:
				content = result["data"]["choices"][0]["message"]["content"]
				import re
				json_match = re.search(r'\{.*\}', content, re.DOTALL)
				if json_match:
					foods_data = json.loads(json_match.group())
					return {
						"success": True,
						"foods_identified": foods_data.get("foods_identified", []),
						"raw_response": content
					}
				else:
					return {
						"success": False,
						"error": "No JSON found in response",
						"raw_response": content
					}
			except json.JSONDecodeError:
				return {
					"success": False,
					"error": "Invalid JSON in response",
					"raw_response": content
				}
		else:
			return {
				"success": False,
				"error": result.get("error", "OpenAI API request failed")
			}


class NutritionLookupAgent:
	"""Stage 2: Specialized agent for USDA nutrition lookup"""
	
	def __init__(self, config: Dict[str, Any], agent_id: int = 0):
		self.config = config
		self.agent_id = agent_id
		self.openai_service = get_openai_service()
		self.usda_service = USDANutritionAPI()
		
		if self.config["logging"]["enable_debug"]:
			print(f"📊 Nutrition Agent #{agent_id} initialized")
	
	def search_usda_tool(self, query: str, page_size: int = None) -> Dict[str, Any]:
		"""Search USDA database"""
		if page_size is None:
			page_size = self.config['usda_search']['default_page_size']
		
		max_page_size = self.config['usda_search']['max_page_size']
		if page_size > max_page_size:
			page_size = max_page_size
		
		if self.config["logging"]["enable_debug"]:
			print(f"🔍 Agent #{self.agent_id} searching USDA: '{query}' (page_size: {page_size})")
		
		try:
			results = self.usda_service.search_foods(query, page_size=page_size)
			
			if results and results.get("foods"):
				foods = results["foods"]
				simplified_foods = []
				for food in foods:
					simplified_foods.append({
						"fdc_id": food.get("fdcId"),
						"description": food.get("description"),
						"data_type": food.get("dataType"),
						"brand_owner": food.get("brandOwner", "")
					})
				
				return {
					"success": True,
					"total_results": len(simplified_foods),
					"foods": simplified_foods
				}
			else:
				return {
					"success": False,
					"message": f"No results found for query: {query}"
				}
		
		except Exception as e:
			return {"success": False, "error": str(e)}
	
	def get_food_nutrition_tool(self, fdc_id: int) -> Dict[str, Any]:
		"""Get detailed nutrition information"""
		if self.config["logging"]["enable_debug"]:
			print(f"📊 Agent #{self.agent_id} getting nutrition for FDC ID: {fdc_id}")
		
		try:
			detailed_info = self.usda_service.get_food_details(fdc_id)
			nutrition_info = format_nutrition_info(detailed_info)
			
			if nutrition_info:
				return {"success": True, "nutrition_data": nutrition_info}
			else:
				return {
					"success": False,
					"message": f"No nutrition data found for FDC ID: {fdc_id}"
				}
		
		except Exception as e:
			return {"success": False, "error": str(e)}
	
	async def lookup_nutrition_for_food(self, food_item: Dict[str, Any]) -> Dict[str, Any]:
		"""Stage 2: Look up nutrition data for a single food item"""
		
		lookup_start = time.time()
		
		if self.config["logging"]["show_stage_progress"]:
			print(f"📊 Agent #{self.agent_id}: Looking up nutrition for '{food_item.get('name', 'Unknown')}'")
		
		# Get system message from config
		system_message = self.config.get("system_messages", {}).get(
			"nutrition_lookup_prompt",
			"Find the best USDA nutrition match for the given food."
		)
		
		# Create search terms from the food item
		search_terms = food_item.get("search_terms", [food_item.get("name", "")])
		cooking_method = food_item.get("cooking_method", "")
		
		# Add cooking method to search terms if not already included
		if cooking_method and cooking_method not in ["", "unknown"]:
			enhanced_terms = [f"{term} {cooking_method}" for term in search_terms]
			search_terms.extend(enhanced_terms)
		
		user_message = {
			"role": "user",
			"content": f"Find nutrition data for this food: {food_item.get('name')} ({cooking_method}). Try these search terms: {', '.join(search_terms[:3])}"
		}
		
		messages = [
			{"role": "system", "content": system_message},
			user_message
		]
		
		# Get function definitions
		functions = self._get_function_definitions()
		
		# Get stage-specific config
		stage_config = self.config["stages"]["nutrition_lookup"]
		
		# Start function calling conversation
		result = await self.openai_service.function_calling_completion(
			messages=messages,
			functions=functions,
			model=self.config["openai"]["model"],
			temperature=stage_config["temperature"],
			max_iterations=stage_config["max_iterations"],
			timeout=stage_config["timeout_seconds"]
		)
		
		if not result["success"]:
			return {
				"success": False,
				"food_item": food_item,
				"agent_id": self.agent_id,
				"error": result.get("error", "OpenAI API request failed")
			}
		
		# Process function calling results
		return await self._process_function_calling_result(result, food_item)
	
	def _get_function_definitions(self):
		"""Get function definitions for nutrition lookup"""
		if "function_definitions" in self.config:
			config_functions = self.config["function_definitions"]
			return [
				config_functions.get("search_usda_database", {}),
				config_functions.get("get_food_nutrition", {})
			]
		else:
			# Fallback definitions
			return [
				{
					"name": "search_usda_database",
					"description": "Search the USDA FoodData Central database for foods.",
					"parameters": {
						"type": "object",
						"properties": {
							"query": {
								"type": "string",
								"description": "Search query for food"
							},
							"page_size": {
								"type": "integer",
								"description": "Number of results to return (default 25, max 100)",
								"default": 25
							}
						},
						"required": ["query"]
					}
				},
				{
					"name": "get_food_nutrition",
					"description": "Get detailed nutrition information for a specific food using its FDC ID.",
					"parameters": {
						"type": "object",
						"properties": {
							"fdc_id": {
								"type": "integer",
								"description": "The FDC ID of the food item from USDA database"
							}
						},
						"required": ["fdc_id"]
					}
				}
			]
	
	async def _process_function_calling_result(self, result: Dict[str, Any], food_item: Dict[str, Any]) -> Dict[str, Any]:
		"""Process the function calling result and execute functions as needed"""
		
		if not result.get("needs_function_execution"):
			# No function execution needed, return final response
			try:
				content = result.get("final_response", "")
				import re
				json_match = re.search(r'\{.*\}', content, re.DOTALL)
				if json_match:
					nutrition_data = json.loads(json_match.group())
					return {
						"success": True,
						"food_item": food_item,
						"nutrition_data": nutrition_data,
						"agent_id": self.agent_id
					}
				else:
					return {
						"success": True,
						"food_item": food_item,
						"raw_response": content,
						"agent_id": self.agent_id,
						"note": "Could not extract structured JSON"
					}
			except json.JSONDecodeError:
				return {
					"success": True,
					"food_item": food_item,
					"raw_response": result.get("final_response", ""),
					"agent_id": self.agent_id,
					"note": "Response is not in JSON format"
				}
		
		# Execute the function
		conversation_history = result["conversation_history"]
		function_call = result["current_function_call"]
		function_name = function_call["name"]
		function_args = json.loads(function_call["arguments"])
		
		if self.config["logging"]["show_function_calls"]:
			print(f"🛠️  Agent #{self.agent_id} calling: {function_name} with {function_args}")
		
		# Call the appropriate function
		if function_name == "search_usda_database":
			function_result = self.search_usda_tool(**function_args)
		elif function_name == "get_food_nutrition":
			function_result = self.get_food_nutrition_tool(**function_args)
		else:
			function_result = {"error": f"Unknown function: {function_name}"}
		
		# Continue the conversation with function result
		continued_result = await self.openai_service.continue_function_conversation(
			conversation_history=conversation_history,
			function_name=function_name,
			function_result=function_result,
			functions=self._get_function_definitions(),
			model=self.config["openai"]["model"],
			temperature=self.config["stages"]["nutrition_lookup"]["temperature"],
			max_iterations=self.config["stages"]["nutrition_lookup"]["max_iterations"] - 1,
			timeout=self.config["stages"]["nutrition_lookup"]["timeout_seconds"]
		)
		
		# Process the continued result
		return await self._process_function_calling_result(continued_result, food_item)


class TwoStageFoodAnalyzer:
	"""Coordinator for two-stage food analysis using centralized OpenAI service"""
	
	def __init__(self, config_path: str = None):
		self.config = load_config(config_path)
		self.openai_service = get_openai_service()
		
		# Initialize Stage 1 agent
		self.food_identification_agent = FoodIdentificationAgent(self.config)
		
		if self.config["logging"]["enable_debug"]:
			print(f"🤖 Two-Stage Food Analyzer initialized using centralized OpenAI service")
	
	async def analyze_food_image(
		self, 
		image_path: str, 
		progress_callback: Callable[[str, Dict], None] = None
	) -> Dict[str, Any]:
		"""
		Analyze food image in two stages
		
		Args:
			image_path: Path to the image file
			progress_callback: Optional callback function to report progress
		"""
		
		total_start = time.time()
		
		if self.config["logging"]["show_stage_progress"]:
			print(f"🤖 Starting two-stage analysis of {Path(image_path).name}")
		
		# STAGE 1: Food Identification
		if progress_callback:
			progress_callback("stage1_start", {"stage": "Food Identification", "status": "starting"})
		
		stage1_result = await self.food_identification_agent.identify_foods_in_image(image_path)
		
		if not stage1_result["success"]:
			return {
				"success": False,
				"error": f"Stage 1 failed: {stage1_result.get('error', 'Unknown error')}",
				"stage": "food_identification"
			}
		
		foods_identified = stage1_result["foods_identified"]
		
		if progress_callback:
			progress_callback("stage1_complete", {
				"stage": "Food Identification",
				"status": "completed",
				"foods_count": len(foods_identified),
				"foods": foods_identified
			})
		
		if self.config["logging"]["show_stage_progress"]:
			print(f"✅ Stage 1 complete: Found {len(foods_identified)} foods")
			for i, food in enumerate(foods_identified, 1):
				print(f"   {i}. {food.get('name', 'Unknown')} ({food.get('estimated_weight_grams', 0)}g)")
		
		# STAGE 2: Parallel Nutrition Lookup
		if progress_callback:
			progress_callback("stage2_start", {"stage": "Nutrition Lookup", "status": "starting"})
		
		stage2_result = await self._parallel_nutrition_lookup(foods_identified, progress_callback)
		
		total_end = time.time()
		
		if self.config["logging"]["show_timing"]:
			print(f"⏱️  Total analysis completed in {total_end - total_start:.2f} seconds")
		
		# Combine results
		final_result = {
			"success": True,
			"analysis_time_seconds": total_end - total_start,
			"stage1_result": stage1_result,
			"stage2_results": stage2_result,
			"foods_with_nutrition": self._combine_food_and_nutrition_data(foods_identified, stage2_result),
			"summary": self._generate_summary(foods_identified, stage2_result)
		}
		
		if progress_callback:
			progress_callback("analysis_complete", {
				"stage": "Complete",
				"status": "finished",
				"result": final_result
			})
		
		return final_result
	
	async def _parallel_nutrition_lookup(
		self, 
		foods: List[Dict], 
		progress_callback: Callable[[str, Dict], None] = None
	) -> List[Dict[str, Any]]:
		"""Stage 2: Parallel nutrition lookup for multiple foods"""
		
		stage_config = self.config["stages"]["nutrition_lookup"]
		max_concurrent = min(
			stage_config["max_concurrent_foods"],
			len(foods)
		)
		
		if self.config["logging"]["show_stage_progress"]:
			print(f"📊 Stage 2: Looking up nutrition for {len(foods)} foods using {max_concurrent} parallel agents")
		
		# Create nutrition agents
		nutrition_agents = []
		for i in range(max_concurrent):
			agent = NutritionLookupAgent(self.config, agent_id=i)
			nutrition_agents.append(agent)
		
		# Create tasks for parallel processing
		tasks = []
		for i, food in enumerate(foods):
			agent = nutrition_agents[i % len(nutrition_agents)]
			task = agent.lookup_nutrition_for_food(food)
			tasks.append(task)
		
		# Execute tasks with progress tracking
		results = []
		completed = 0
		
		for task in asyncio.as_completed(tasks):
			result = await task
			results.append(result)
			completed += 1
			
			if progress_callback:
				progress_callback("stage2_progress", {
					"stage": "Nutrition Lookup",
					"status": "in_progress",
					"completed": completed,
					"total": len(foods),
					"latest_result": result
				})
			
			if self.config["logging"]["show_stage_progress"]:
				food_name = result.get("food_item", {}).get("name", "Unknown")
				print(f"✅ Nutrition lookup {completed}/{len(foods)}: {food_name}")
		
		return results
	
	def _combine_food_and_nutrition_data(
		self, 
		foods: List[Dict], 
		nutrition_results: List[Dict]
	) -> List[Dict]:
		"""Combine food identification with nutrition data"""
		
		combined = []
		
		for i, food in enumerate(foods):
			# Find corresponding nutrition result
			nutrition_result = None
			for result in nutrition_results:
				if result.get("food_item", {}).get("name") == food.get("name"):
					nutrition_result = result
					break
			
			# Combine data
			combined_item = {
				"original_food": food,
				"nutrition_lookup": nutrition_result,
				"combined_data": None
			}
			
			if nutrition_result and nutrition_result.get("success"):
				nutrition_data = nutrition_result.get("nutrition_data", {})
				estimated_weight = food.get("estimated_weight_grams", 0)
				
				# Calculate nutrition for estimated portion
				if "nutrition_per_100g" in nutrition_data:
					nutrition_per_100g = nutrition_data["nutrition_per_100g"]
					multiplier = estimated_weight / 100.0
					
					combined_item["combined_data"] = {
						"name": food.get("name"),
						"estimated_weight_grams": estimated_weight,
						"cooking_method": food.get("cooking_method"),
						"confidence": food.get("confidence"),
						"usda_match": nutrition_data.get("usda_match", {}),
						"nutrition_per_portion": {
							"calories": round(nutrition_per_100g.get("calories", 0) * multiplier, 1),
							"protein_g": round(nutrition_per_100g.get("protein_g", 0) * multiplier, 1),
							"fat_g": round(nutrition_per_100g.get("fat_g", 0) * multiplier, 1),
							"carbs_g": round(nutrition_per_100g.get("carbs_g", 0) * multiplier, 1),
							"fiber_g": round(nutrition_per_100g.get("fiber_g", 0) * multiplier, 1)
						}
					}
			
			combined.append(combined_item)
		
		return combined
	
	def _generate_summary(self, foods: List[Dict], nutrition_results: List[Dict]) -> Dict[str, Any]:
		"""Generate overall summary of the analysis"""
		
		total_nutrition = {
			"calories": 0,
			"protein_g": 0,
			"fat_g": 0,
			"carbs_g": 0,
			"fiber_g": 0
		}
		
		successful_lookups = 0
		
		# Calculate totals from successful nutrition lookups
		for result in nutrition_results:
			if result.get("success") and "nutrition_data" in result:
				nutrition_data = result["nutrition_data"]
				food_item = result["food_item"]
				estimated_weight = food_item.get("estimated_weight_grams", 0)
				
				if "nutrition_per_100g" in nutrition_data:
					nutrition_per_100g = nutrition_data["nutrition_per_100g"]
					multiplier = estimated_weight / 100.0
					
					total_nutrition["calories"] += nutrition_per_100g.get("calories", 0) * multiplier
					total_nutrition["protein_g"] += nutrition_per_100g.get("protein_g", 0) * multiplier
					total_nutrition["fat_g"] += nutrition_per_100g.get("fat_g", 0) * multiplier
					total_nutrition["carbs_g"] += nutrition_per_100g.get("carbs_g", 0) * multiplier
					total_nutrition["fiber_g"] += nutrition_per_100g.get("fiber_g", 0) * multiplier
					
					successful_lookups += 1
		
		# Round totals
		for key in total_nutrition:
			total_nutrition[key] = round(total_nutrition[key], 1)
		
		return {
			"total_foods_identified": len(foods),
			"successful_nutrition_lookups": successful_lookups,
			"total_nutrition": total_nutrition,
			"success_rate": f"{(successful_lookups / len(foods) * 100):.1f}%" if foods else "0%"
		}


# Test functions
async def test_two_stage_analysis(image_path: str, config_path: str = None):
	"""Test the two-stage food analysis system"""
	
	print("🤖 Two-Stage Food Analysis Test (Using Centralized OpenAI Service)")
	print("=" * 60)
	
	def progress_callback(stage: str, data: Dict):
		"""Progress callback for testing"""
		if stage == "stage1_complete":
			print(f"\n✅ {data['stage']} completed!")
			print(f"Found {data['foods_count']} foods:")
			for i, food in enumerate(data['foods'], 1):
				print(f"  {i}. {food.get('name', 'Unknown')} ({food.get('estimated_weight_grams', 0)}g, {food.get('confidence', 0):.1%} confidence)")
		
		elif stage == "stage2_progress":
			if data['completed'] == 1:
				print(f"\n📊 {data['stage']} starting...")
			print(f"  Progress: {data['completed']}/{data['total']} completed")
		
		elif stage == "analysis_complete":
			print(f"\n🎉 {data['stage']} - Analysis finished!")
	
	try:
		# Initialize analyzer
		analyzer = TwoStageFoodAnalyzer(config_path)
		
		# Run analysis
		result = await analyzer.analyze_food_image(image_path, progress_callback)
		
		if result["success"]:
			print("\n📊 Final Results:")
			print("=" * 30)
			
			summary = result["summary"]
			print(f"📋 Summary:")
			print(f"  • Total foods: {summary['total_foods_identified']}")
			print(f"  • Successful lookups: {summary['successful_nutrition_lookups']}")
			print(f"  • Success rate: {summary['success_rate']}")
			print(f"  • Analysis time: {result['analysis_time_seconds']:.2f} seconds")
			
			print(f"\n🧮 Total Nutrition:")
			total_nutrition = summary["total_nutrition"]
			for nutrient, amount in total_nutrition.items():
				print(f"  • {nutrient}: {amount}")
			
			print(f"\n🍽️  Foods with Nutrition:")
			for i, item in enumerate(result["foods_with_nutrition"], 1):
				combined = item.get("combined_data")
				if combined:
					print(f"\n{i}. {combined['name']}")
					print(f"   Weight: {combined['estimated_weight_grams']}g")
					print(f"   Method: {combined['cooking_method']}")
					nutrition = combined['nutrition_per_portion']
					print(f"   Nutrition: {nutrition['calories']} cal, {nutrition['protein_g']}g protein, {nutrition['fat_g']}g fat, {nutrition['carbs_g']}g carbs")
				else:
					original = item["original_food"]
					print(f"\n{i}. {original.get('name', 'Unknown')} - ❌ Nutrition lookup failed")
		
		else:
			print("❌ Analysis failed!")
			print(f"Error: {result.get('error', 'Unknown error')}")
		
		return result
		
	except Exception as e:
		print(f"❌ Test failed: {e}")
		import traceback
		traceback.print_exc()


async def main():
	"""Main test function"""
	
	# Check for test images
	test_image_dir = Path(__file__).parent.parent / "testing" / "test_images"
	if not test_image_dir.exists():
		print("❌ No test_images directory found")
		return
	
	image_files = (
		list(test_image_dir.glob("*.jpg")) +
		list(test_image_dir.glob("*.jpeg")) +
		list(test_image_dir.glob("*.png"))
	)
	
	if not image_files:
		print("❌ No images found in test_images directory")
		return
	
	print(f"📸 Found {len(image_files)} test images")
	
	# Test with first image
	if image_files:
		await test_two_stage_analysis(str(image_files[0]))


if __name__ == "__main__":
	asyncio.run(main())