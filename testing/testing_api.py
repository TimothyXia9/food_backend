import requests
from typing import Dict, Any, List
import json

BASE_URL = "http://localhost:8000/api/v1"

def get_token_by_register(username: str = "testuser", password: str = "testpass123", email: str = "test@example.com") -> Dict[str, str]:
	"""通过注册获取token"""
	response = requests.post(
		f"{BASE_URL}/auth/register",
		headers={"Content-Type": "application/json"},
		json={
			"username": username,
			"email": email,
			"password": password
		}
	)
	
	print(f"注册请求状态码: {response.status_code}")
	print(f"注册响应: {response.text}")
	
	if response.status_code == 201:
		data = response.json()
		if data["success"]:
			return {
				"access_token": data["data"]["token"],
				"refresh_token": data["data"]["refresh_token"]
			}
	
	return {}

def get_token_by_login(username: str = "testuser", password: str = "testpass123") -> Dict[str, str]:
	"""通过登录获取token"""
	response = requests.post(
		f"{BASE_URL}/auth/login",
		headers={"Content-Type": "application/json"},
		json={
			"username": username,
			"password": password
		}
	)
	
	print(f"登录请求状态码: {response.status_code}")
	print(f"登录响应: {response.text}")
	
	if response.status_code == 200:
		data = response.json()
		if data["success"]:
			return {
				"access_token": data["data"]["access"],
				"refresh_token": data["data"]["refresh"]
			}
	
	return {}

def test_authenticated_request(token: str):
	"""测试需要认证的API请求"""
	headers = {
		"Authorization": f"Bearer {token}",
		"Content-Type": "application/json"
	}
	
	# 测试获取用户资料
	print("\n=== 测试获取用户资料 ===")
	response = requests.get(f"{BASE_URL}/users/profile", headers=headers)
	print(f"状态码: {response.status_code}")
	print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
	
	# 测试搜索食物 (如果foods app启用)
	print("\n=== 测试搜索食物 ===")
	response = requests.get(f"{BASE_URL}/foods/search/", headers=headers, params={"query": "apple"})
	print(f"状态码: {response.status_code}")
	print(f"响应: {response.text}")
	
	# 测试获取食物分类
	print("\n=== 测试获取食物分类 ===")
	response = requests.get(f"{BASE_URL}/foods/categories/", headers=headers)
	print(f"状态码: {response.status_code}")
	print(f"响应: {response.text}")
	
	# 测试USDA搜索 (如果配置了USDA API)
	print("\n=== 测试USDA搜索 ===")
	response = requests.get(f"{BASE_URL}/foods/usda/search/", headers=headers, params={"query": "apple", "page_size": 5})
	print(f"状态码: {response.status_code}")
	print(f"响应: {response.text}")

def test_public_endpoints():
	"""测试公共API端点"""
	print("=== 测试公共端点 ===")
	
	# 测试API根路径
	response = requests.get(f"{BASE_URL}/")
	print(f"API根路径状态码: {response.status_code}")

if __name__ == "__main__":
	print("=== Django API Token 测试 ===\n")
	
	# 方法1: 先尝试注册获取token
	print("1. 尝试注册新用户获取token...")
	tokens = get_token_by_register()
	
	if not tokens:
		# 方法2: 如果注册失败，尝试登录现有用户
		print("\n2. 注册失败，尝试登录现有用户...")
		tokens = get_token_by_login()
	
	if tokens:
		print(f"\n✅ 成功获取token!")
		print(f"Access Token: {tokens['access_token']}")
		print(f"Refresh Token: {tokens['refresh_token']}")
		
		# 使用token测试API
		test_authenticated_request(tokens['access_token'])
	else:
		print("\n❌ 无法获取token，请检查:")
		print("1. Django服务器是否运行在 http://localhost:8000")
		print("2. 数据库是否已迁移 (python manage.py migrate)")
		print("3. accounts app是否正确配置")
	
	# 测试公共端点
	print("\n" + "="*50)
	test_public_endpoints()
