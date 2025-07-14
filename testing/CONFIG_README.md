# OpenAI USDA Agent Configuration

这个文档说明如何使用和修改 `config.json` 配置文件来自定义 OpenAI USDA Agent 的行为。

## 配置文件结构

### OpenAI 设置
```json
"openai": {
    "model": "gpt-4o",           // 使用的 OpenAI 模型
    "temperature": 0.1,          // 响应的随机性 (0.0-2.0)
    "max_iterations": 10,        // 最大对话轮数
    "timeout_seconds": 60        // API 请求超时时间
}
```

### USDA 搜索设置
```json
"usda_search": {
    "default_page_size": 25,     // 默认搜索结果数量
    "max_page_size": 100         // 最大搜索结果数量
}
```

### 日志设置
```json
"logging": {
    "enable_debug": true,        // 启用调试信息
    "show_function_calls": true, // 显示函数调用详情
    "show_timing": true          // 显示处理时间
}
```

### 函数定义
可以在 `function_definitions` 中修改 OpenAI 函数调用的描述和参数：

```json
"function_definitions": {
    "search_usda_database": {
        "name": "search_usda_database",
        "description": "搜索描述...",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询..."
                },
                "page_size": {
                    "type": "integer", 
                    "description": "结果数量...",
                    "default": 25
                }
            },
            "required": ["query"]
        }
    }
}
```

### 系统提示消息
可以在 `system_messages` 中修改给 AI 的指令：

```json
"system_messages": {
    "food_analysis_prompt": "您是一位专业的营养分析师..."
}
```

## 常用修改示例

### 1. 修改默认搜索结果数量
```json
"usda_search": {
    "default_page_size": 50,  // 改为 50 个结果
    "max_page_size": 100
}
```

### 2. 使用不同的 AI 模型
```json
"openai": {
    "model": "gpt-4",        // 改为 gpt-4
    "temperature": 0.0,      // 更确定性的回答
    "max_iterations": 15,    // 更多对话轮数
    "timeout_seconds": 120   // 更长超时时间
}
```

### 3. 关闭调试信息
```json
"logging": {
    "enable_debug": false,
    "show_function_calls": false, 
    "show_timing": false
}
```

### 4. 修改搜索函数描述
```json
"function_definitions": {
    "search_usda_database": {
        "description": "搜索 USDA 食物数据库。请使用具体的食物名称和烹饪方法以获得更好结果。默认请求 50 个结果进行全面搜索。"
    }
}
```

## 使用方法

1. **直接修改 config.json 文件** - 所有更改会立即生效
2. **自定义配置文件路径** - 在代码中指定不同的配置文件：
   ```python
   agent = OpenAIUSDAAgent(config_path="/path/to/custom_config.json")
   ```

## 注意事项

- JSON 格式必须正确，否则会使用默认配置
- `page_size` 的实际效果取决于 OpenAI 模型是否遵循指令
- 修改 `system_messages` 时需要保持 JSON 格式正确
- 配置文件支持中文，但建议 function descriptions 使用英文以提高 AI 理解准确性

## 故障排除

如果配置文件无法加载：
1. 检查 JSON 语法是否正确
2. 确保文件编码为 UTF-8
3. 查看控制台输出的错误信息
4. 程序会自动回退到默认配置继续运行