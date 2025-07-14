"""
Example usage of the Two-Stage Food Analyzer
示例：如何使用两阶段食物分析器
"""

import asyncio
import json
from pathlib import Path
from two_stage_food_analyzer import TwoStageFoodAnalyzer


class ProgressTracker:
	"""示例进度跟踪器，模拟前端更新"""
	
	def __init__(self):
		self.current_stage = None
		self.foods_identified = []
		self.nutrition_progress = {}
	
	def update_progress(self, stage: str, data: dict):
		"""进度回调函数"""
		
		if stage == "stage1_start":
			print("🔍 开始识别食物...")
			self.current_stage = "identifying"
		
		elif stage == "stage1_complete":
			print(f"✅ 食物识别完成！发现 {data['foods_count']} 种食物")
			self.foods_identified = data['foods']
			self.current_stage = "foods_identified"
			
			# 显示识别的食物
			print("\n📋 识别的食物:")
			for i, food in enumerate(self.foods_identified, 1):
				name = food.get('name', 'Unknown')
				weight = food.get('estimated_weight_grams', 0)
				confidence = food.get('confidence', 0)
				method = food.get('cooking_method', 'unknown')
				print(f"  {i}. {name}")
				print(f"     重量: {weight}g | 烹饪方法: {method} | 置信度: {confidence:.1%}")
			
			print(f"\n📊 开始获取营养数据...")
		
		elif stage == "stage2_start":
			self.current_stage = "nutrition_lookup"
		
		elif stage == "stage2_progress":
			completed = data['completed']
			total = data['total']
			latest = data.get('latest_result', {})
			
			# 更新进度
			progress_percent = (completed / total) * 100
			print(f"📊 营养数据获取进度: {completed}/{total} ({progress_percent:.1f}%)")
			
			# 显示最新完成的食物营养信息
			if latest.get('success'):
				food_name = latest.get('food_item', {}).get('name', 'Unknown')
				print(f"   ✅ {food_name} 营养数据获取完成")
			else:
				food_name = latest.get('food_item', {}).get('name', 'Unknown')
				print(f"   ❌ {food_name} 营养数据获取失败")
		
		elif stage == "analysis_complete":
			print("🎉 完整分析完成！")
			self.current_stage = "complete"


async def example_basic_usage():
	"""基本使用示例"""
	
	print("=" * 60)
	print("🤖 两阶段食物分析器 - 基本使用示例")
	print("=" * 60)
	
	# 初始化分析器
	try:
		analyzer = TwoStageFoodAnalyzer("config_two_stage.json")
		print("✅ 分析器初始化成功")
	except ValueError as e:
		print(f"❌ 分析器初始化失败: {e}")
		print("请确保设置了 OPENAI_API_KEY 环境变量")
		return
	
	# 检查测试图片
	test_image_dir = Path(__file__).parent / "test_images"
	if not test_image_dir.exists():
		print("❌ 测试图片目录不存在，请创建 test_images/ 目录并添加食物图片")
		return
	
	image_files = list(test_image_dir.glob("*.jpg")) + list(test_image_dir.glob("*.png"))
	if not image_files:
		print("❌ test_images/ 目录中没有找到图片文件")
		return
	
	# 选择第一张图片进行测试
	test_image = str(image_files[0])
	print(f"📸 使用测试图片: {Path(test_image).name}")
	
	# 创建进度跟踪器
	progress_tracker = ProgressTracker()
	
	# 开始分析
	print(f"\n🚀 开始两阶段分析...")
	start_time = asyncio.get_event_loop().time()
	
	try:
		result = await analyzer.analyze_food_image(
			test_image,
			progress_callback=progress_tracker.update_progress
		)
		
		end_time = asyncio.get_event_loop().time()
		total_time = end_time - start_time
		
		# 显示最终结果
		await display_final_results(result, total_time)
		
	except Exception as e:
		print(f"❌ 分析过程出错: {e}")
		import traceback
		traceback.print_exc()


async def display_final_results(result: dict, total_time: float):
	"""显示最终结果"""
	
	print("\n" + "=" * 60)
	print("📊 最终分析结果")
	print("=" * 60)
	
	if not result.get("success"):
		print(f"❌ 分析失败: {result.get('error', 'Unknown error')}")
		return
	
	summary = result["summary"]
	
	# 基本统计
	print(f"📋 分析统计:")
	print(f"  • 总处理时间: {total_time:.2f} 秒")
	print(f"  • 识别食物数: {summary['total_foods_identified']}")
	print(f"  • 成功获取营养数据: {summary['successful_nutrition_lookups']}")
	print(f"  • 成功率: {summary['success_rate']}")
	
	# 总营养信息
	print(f"\n🧮 总营养成分:")
	total_nutrition = summary["total_nutrition"]
	print(f"  • 卡路里: {total_nutrition['calories']:.1f} kcal")
	print(f"  • 蛋白质: {total_nutrition['protein_g']:.1f} g")
	print(f"  • 脂肪: {total_nutrition['fat_g']:.1f} g")
	print(f"  • 碳水化合物: {total_nutrition['carbs_g']:.1f} g")
	print(f"  • 纤维: {total_nutrition['fiber_g']:.1f} g")
	
	# 详细食物信息
	print(f"\n🍽️  详细食物营养信息:")
	foods_with_nutrition = result["foods_with_nutrition"]
	
	for i, item in enumerate(foods_with_nutrition, 1):
		combined = item.get("combined_data")
		original = item["original_food"]
		
		print(f"\n{i}. {original.get('name', 'Unknown Food')}")
		print(f"   估算重量: {original.get('estimated_weight_grams', 0)}g")
		print(f"   烹饪方法: {original.get('cooking_method', 'unknown')}")
		print(f"   识别置信度: {original.get('confidence', 0):.1%}")
		
		if combined:
			# 营养信息可用
			usda_match = combined.get('usda_match', {})
			nutrition = combined.get('nutrition_per_portion', {})
			
			print(f"   USDA 匹配: {usda_match.get('description', 'N/A')}")
			print(f"   匹配置信度: {usda_match.get('match_confidence', 0):.1%}")
			print(f"   营养成分 (该份量):")
			print(f"     - 卡路里: {nutrition.get('calories', 0):.1f} kcal")
			print(f"     - 蛋白质: {nutrition.get('protein_g', 0):.1f} g")
			print(f"     - 脂肪: {nutrition.get('fat_g', 0):.1f} g")
			print(f"     - 碳水化合物: {nutrition.get('carbs_g', 0):.1f} g")
			print(f"     - 纤维: {nutrition.get('fiber_g', 0):.1f} g")
		else:
			# 营养信息获取失败
			nutrition_result = item.get("nutrition_lookup", {})
			error = nutrition_result.get("error", "Unknown error")
			print(f"   ❌ 营养数据获取失败: {error}")


async def example_with_custom_callback():
	"""自定义回调示例"""
	
	print("\n" + "=" * 60)
	print("🔧 自定义进度回调示例")
	print("=" * 60)
	
	# 自定义回调函数
	progress_data = {
		"stage1_time": None,
		"stage2_time": None,
		"nutrition_results": []
	}
	
	def custom_callback(stage: str, data: dict):
		import time
		current_time = time.time()
		
		if stage == "stage1_start":
			progress_data["stage1_start"] = current_time
			print("🔍 [自定义] 食物识别阶段开始")
		
		elif stage == "stage1_complete":
			progress_data["stage1_time"] = current_time - progress_data["stage1_start"]
			print(f"✅ [自定义] 食物识别完成 ({progress_data['stage1_time']:.2f}s)")
			print(f"    发现食物: {[f['name'] for f in data['foods']]}")
		
		elif stage == "stage2_start":
			progress_data["stage2_start"] = current_time
			print("📊 [自定义] 营养数据获取阶段开始")
		
		elif stage == "stage2_progress":
			latest = data.get('latest_result', {})
			if latest.get('success'):
				food_name = latest['food_item']['name']
				progress_data["nutrition_results"].append(food_name)
				print(f"✅ [自定义] {food_name} 营养数据完成")
		
		elif stage == "analysis_complete":
			progress_data["stage2_time"] = current_time - progress_data["stage2_start"]
			print(f"🎉 [自定义] 分析完成！")
			print(f"    阶段1时间: {progress_data['stage1_time']:.2f}s")
			print(f"    阶段2时间: {progress_data['stage2_time']:.2f}s")
	
	# 这里可以添加实际的分析代码
	print("📝 自定义回调函数已定义，可用于 analyzer.analyze_food_image()")


async def main():
	"""主函数"""
	
	print("🤖 两阶段食物分析器使用示例")
	print("=" * 60)
	
	# 基本使用示例
	await example_basic_usage()
	
	# 自定义回调示例
	await example_with_custom_callback()
	
	print(f"\n✅ 示例演示完成！")
	print(f"\n💡 提示:")
	print(f"  - 将食物图片放入 test_images/ 目录")
	print(f"  - 确保设置了 OPENAI_API_KEY 环境变量")
	print(f"  - 可以修改 config_two_stage.json 来调整参数")


if __name__ == "__main__":
	asyncio.run(main())