# 两阶段食物分析系统

这个系统将食物图片分析分为两个阶段，提供更好的用户体验和更快的响应时间。

## 🔄 两阶段架构

### 阶段 1: 食物识别 (快速)
- **目标**: 快速识别图片中的食物并估算份量
- **时间**: 通常 5-15 秒
- **输出**: 食物列表、重量估算、烹饪方法、置信度
- **用户体验**: 用户可以立即看到识别的食物

### 阶段 2: 营养数据获取 (并行)
- **目标**: 为每个食物获取准确的 USDA 营养数据
- **时间**: 通常 10-30 秒（并行处理）
- **输出**: 详细营养信息、USDA 匹配数据
- **用户体验**: 营养数据逐个显示，总体等待时间更短

## 🚀 优势

1. **更快的初步反馈** - 用户立即看到识别的食物
2. **并行处理** - 多个 agent 同时处理营养数据获取
3. **更好的错误处理** - 单个食物的营养查找失败不影响其他食物
4. **可配置的并发度** - 根据 API 限制调整并行数量
5. **进度回调** - 实时显示处理进度

## 📁 文件结构

```
testing/
├── two_stage_food_analyzer.py    # 主要的两阶段分析器
├── config_two_stage.json         # 两阶段专用配置
├── TWO_STAGE_README.md           # 这个说明文档
└── test_images/                  # 测试图片目录
```

## ⚙️ 配置选项

### 阶段配置
```json
"stages": {
    "food_identification": {
        "max_iterations": 3,      // 食物识别最大迭代次数
        "temperature": 0.2,       // AI 温度设置
        "timeout_seconds": 30     // 超时时间
    },
    "nutrition_lookup": {
        "max_iterations": 5,      // 营养查找最大迭代次数
        "temperature": 0.0,       // AI 温度设置（更确定性）
        "timeout_seconds": 45,    // 超时时间
        "parallel_agents": 3,     // 并行 agent 数量
        "max_concurrent_foods": 5 // 最大并发处理食物数
    }
}
```

### 系统提示消息
```json
"system_messages": {
    "food_identification_prompt": "专门用于食物识别的提示...",
    "nutrition_lookup_prompt": "专门用于营养数据查找的提示..."
}
```

## 🔧 使用方法

### 基本使用
```python
from two_stage_food_analyzer import TwoStageFoodAnalyzer

# 初始化分析器
analyzer = TwoStageFoodAnalyzer("config_two_stage.json")

# 分析图片（带进度回调）
def progress_callback(stage: str, data: dict):
    if stage == "stage1_complete":
        print(f"阶段1完成：发现 {data['foods_count']} 种食物")
    elif stage == "stage2_progress":
        print(f"营养查找进度: {data['completed']}/{data['total']}")

result = await analyzer.analyze_food_image(
    "test_image.jpg", 
    progress_callback=progress_callback
)
```

### 进度回调事件
- `stage1_start` - 食物识别开始
- `stage1_complete` - 食物识别完成，包含食物列表
- `stage2_start` - 营养查找开始
- `stage2_progress` - 营养查找进度更新
- `analysis_complete` - 完整分析完成

### 结果结构
```python
{
    "success": True,
    "analysis_time_seconds": 25.3,
    "stage1_result": {
        "foods_identified": [
            {
                "name": "苹果",
                "estimated_weight_grams": 150,
                "cooking_method": "生",
                "confidence": 0.95,
                "search_terms": ["apple", "apple raw"]
            }
        ]
    },
    "stage2_results": [
        {
            "success": True,
            "nutrition_data": { ... },
            "agent_id": 0
        }
    ],
    "foods_with_nutrition": [ ... ],
    "summary": {
        "total_foods_identified": 3,
        "successful_nutrition_lookups": 3,
        "total_nutrition": {
            "calories": 245.5,
            "protein_g": 12.3,
            "fat_g": 8.1,
            "carbs_g": 35.2,
            "fiber_g": 4.8
        },
        "success_rate": "100.0%"
    }
}
```

## 🧪 测试

### 运行测试
```bash
cd testing
source ../venv/bin/activate
python3 two_stage_food_analyzer.py
```

### 测试输出示例
```
🤖 Two-Stage Food Analysis Test
==================================================
🔍 Stage 1: Identifying foods in test_image.jpg

✅ Food Identification completed!
Found 3 foods:
  1. 苹果 (150g, 95.0% confidence)
  2. 香蕉 (120g, 90.0% confidence)
  3. 面包 (80g, 85.0% confidence)

📊 Nutrition Lookup starting...
  Progress: 1/3 completed
  Progress: 2/3 completed
  Progress: 3/3 completed

🎉 Complete - Analysis finished!

📊 Final Results:
==============================
📋 Summary:
  • Total foods: 3
  • Successful lookups: 3
  • Success rate: 100.0%
  • Analysis time: 23.45 seconds

🧮 Total Nutrition:
  • calories: 245.5
  • protein_g: 12.3
  • fat_g: 8.1
  • carbs_g: 35.2
  • fiber_g: 4.8
```

## 🔄 与单阶段系统的对比

| 特性 | 单阶段系统 | 两阶段系统 |
|------|------------|------------|
| 初步反馈时间 | 30-60秒 | 5-15秒 |
| 总处理时间 | 30-60秒 | 20-45秒 |
| 用户体验 | 等待完整结果 | 逐步显示结果 |
| 错误恢复 | 全部失败 | 部分失败 |
| 并行处理 | 否 | 是 |
| 资源利用 | 单线程 | 多线程 |

## 📊 性能优化

### 配置建议
- **parallel_agents**: 设置为可用 API key 数量
- **max_concurrent_foods**: 不超过 5-10 个
- **timeout_seconds**: 根据网络状况调整

### API 使用优化
- 多个 API key 轮换使用
- 智能重试机制
- 速率限制处理

## 🚨 注意事项

1. **API Key 配置**: 确保配置了足够的 OpenAI API keys
2. **USDA API**: 需要网络连接访问 USDA 数据库
3. **并发限制**: 根据 API 限制调整并发数量
4. **错误处理**: 单个食物失败不影响其他食物的处理

## 🔮 未来改进

1. **缓存机制** - 缓存常见食物的营养数据
2. **本地数据库** - 减少对外部 API 的依赖
3. **图片预处理** - 提高食物识别准确性
4. **用户反馈** - 允许用户修正识别结果