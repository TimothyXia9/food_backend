#!/usr/bin/env python3
"""
完整的API演示脚本
展示如何使用Django后端API进行食物搜索和管理
"""

import requests
import json
from typing import Dict, Optional

BASE_URL = "http://localhost:8000/api/v1"

class FoodAPIDemo:
	def __init__(self):
		self.token = None
		self.refresh_token = None
		
	def authenticate(self, username: str = "testuser", password: str = "testpass123") -> bool:
		"""登录获取token"""
		print("🔑 正在登录...")
		
		response = requests.post(
			f"{BASE_URL}/auth/login",
			headers={"Content-Type": "application/json"},
			json={"username": username, "password": password}
		)
		
		if response.status_code == 200:
			data = response.json()
			if data["success"]:
				self.token = data["data"]["access"]
				self.refresh_token = data["data"]["refresh"]
				print(f"✅ 登录成功! 用户: {data['data']['user']['username']}")
				return True
		
		print(f"❌ 登录失败: {response.text}")
		return False
	
	def get_headers(self) -> Dict[str, str]:
		"""获取请求头"""
		return {
			"Authorization": f"Bearer {self.token}",
			"Content-Type": "application/json"
		}
	
	def search_foods(self, query: str) -> Optional[Dict]:
		"""搜索本地食物数据库"""
		print(f"\n🔍 搜索本地食物: '{query}'")
		
		response = requests.get(
			f"{BASE_URL}/foods/search/",
			headers=self.get_headers(),
			params={"query": query, "page_size": 10}
		)
		
		if response.status_code == 200:
			data = response.json()
			foods = data.get("data", {}).get("foods", [])
			print(f"✅ 找到 {len(foods)} 个本地食物")
			for i, food in enumerate(foods[:3], 1):
				print(f"   {i}. {food['name']} - {food['calories_per_100g']} 卡/100g")
			return data
		else:
			print(f"❌ 搜索失败: {response.text}")
			return None
	
	def search_usda_foods(self, query: str) -> Optional[Dict]:
		"""搜索USDA食物数据库"""
		print(f"\n🥗 搜索USDA食物: '{query}'")
		
		response = requests.get(
			f"{BASE_URL}/foods/usda/search/",
			headers=self.get_headers(),
			params={"query": query, "page_size": 5}
		)
		
		if response.status_code == 200:
			data = response.json()
			foods = data.get("data", {}).get("foods", [])
			print(f"✅ 找到 {len(foods)} 个USDA食物")
			for i, food in enumerate(foods[:3], 1):
				print(f"   {i}. {food['description']} (FDC ID: {food['fdc_id']})")
			return data
		elif response.status_code == 503:
			print("⚠️  USDA API未配置，请设置USDA_API_KEY环境变量")
			return None
		else:
			print(f"❌ USDA搜索失败: {response.text}")
			return None
	
	def get_usda_nutrition(self, fdc_id: str) -> Optional[Dict]:
		"""获取USDA营养信息"""
		print(f"\n📊 获取USDA营养信息: FDC ID {fdc_id}")
		
		response = requests.get(
			f"{BASE_URL}/foods/usda/nutrition/{fdc_id}/",
			headers=self.get_headers()
		)
		
		if response.status_code == 200:
			data = response.json()
			nutrition = data.get("data", {})
			print(f"✅ 获取营养信息: {nutrition.get('description', 'N/A')}")
			
			nutrients = nutrition.get("nutrients", {})
			if nutrients:
				print("   主要营养成分 (每100g):")
				for name, info in nutrients.items():
					if isinstance(info, dict) and 'amount' in info:
						print(f"     • {name}: {info['amount']} {info.get('unit', '')}")
			
			return data
		elif response.status_code == 503:
			print("⚠️  USDA API未配置")
			return None
		else:
			print(f"❌ 获取营养信息失败: {response.text}")
			return None
	
	def create_food_from_usda(self, fdc_id: str) -> Optional[Dict]:
		"""从USDA数据创建食物记录"""
		print(f"\n➕ 从USDA创建食物: FDC ID {fdc_id}")
		
		response = requests.post(
			f"{BASE_URL}/foods/usda/create/",
			headers=self.get_headers(),
			json={"fdc_id": fdc_id}
		)
		
		if response.status_code == 201:
			data = response.json()
			food_data = data.get("data", {})
			print(f"✅ 成功创建食物: {food_data.get('name')} (ID: {food_data.get('food_id')})")
			return data
		elif response.status_code == 503:
			print("⚠️  USDA API未配置")
			return None
		else:
			print(f"❌ 创建食物失败: {response.text}")
			return None
	
	def get_food_categories(self) -> Optional[Dict]:
		"""获取食物分类"""
		print(f"\n📁 获取食物分类")
		
		response = requests.get(
			f"{BASE_URL}/foods/categories/",
			headers=self.get_headers()
		)
		
		if response.status_code == 200:
			data = response.json()
			categories = data.get("data", {}).get("categories", [])
			print(f"✅ 找到 {len(categories)} 个分类")
			for category in categories[:5]:
				print(f"   • {category['name']} ({category['food_count']} 个食物)")
			return data
		else:
			print(f"❌ 获取分类失败: {response.text}")
			return None
	
	def get_user_profile(self) -> Optional[Dict]:
		"""获取用户资料"""
		print(f"\n👤 获取用户资料")
		
		response = requests.get(
			f"{BASE_URL}/users/profile",
			headers=self.get_headers()
		)
		
		if response.status_code == 200:
			data = response.json()
			user = data.get("data", {})
			print(f"✅ 用户: {user.get('username')} ({user.get('email')})")
			profile = user.get("profile", {})
			if profile.get("daily_calorie_goal"):
				print(f"   每日卡路里目标: {profile['daily_calorie_goal']}")
			return data
		else:
			print(f"❌ 获取用户资料失败: {response.text}")
			return None

def main():
	"""主演示函数"""
	print("🥙 Django Food API 完整演示")
	print("=" * 50)
	
	# 初始化API客户端
	api = FoodAPIDemo()
	
	# 1. 登录认证
	if not api.authenticate():
		print("❌ 无法登录，演示结束")
		return
	
	# 2. 获取用户资料
	api.get_user_profile()
	
	# 3. 搜索本地食物数据库
	api.search_foods("apple")
	api.search_foods("chicken")
	
	# 4. 获取食物分类
	api.get_food_categories()
	
	# 5. 搜索USDA数据库 (如果配置了)
	usda_results = api.search_usda_foods("apple")
	
	if usda_results and usda_results.get("data", {}).get("foods"):
		# 6. 获取第一个USDA食物的营养信息
		first_food = usda_results["data"]["foods"][0]
		fdc_id = first_food["fdc_id"]
		
		# 获取详细营养信息
		nutrition_data = api.get_usda_nutrition(str(fdc_id))
		
		if nutrition_data:
			# 7. 从USDA数据创建本地食物记录
			created_food = api.create_food_from_usda(str(fdc_id))
			
			if created_food:
				# 8. 再次搜索本地数据库，应该能找到刚创建的食物
				print("\n🔄 再次搜索本地数据库...")
				api.search_foods("apple")
	
	print("\n🎉 API演示完成!")
	print("\n💡 提示:")
	print("1. 要启用USDA功能，请在.env文件中添加: USDA_API_KEY=your_key")
	print("2. 要添加更多食物，可以使用USDA搜索和创建功能")
	print("3. 所有API端点都支持完整的错误处理和认证")

if __name__ == "__main__":
	main()