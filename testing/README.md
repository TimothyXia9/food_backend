# 图片识别测试

这个目录包含了使用 OpenAI GPT-4V API 进行食物图片识别的测试功能。

## 使用方法

### 1. 安装依赖

```bash
cd /home/tim/backend
pip install -r requirements.txt
```

### 2. 设置 OpenAI API Key

创建 `.env` 文件或设置环境变量：

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### 3. 添加测试图片

将食物图片放入 `test_images/` 目录中，支持的格式：
- JPG/JPEG
- PNG  
- BMP
- GIF

### 4. 运行测试

```bash
cd testing
python test_image_recognition.py
```

## 文件说明

- `food_prompt.txt` - 用于 GPT-4V 的提示词模板
- `test_image_recognition.py` - 主要的测试脚本
- `test_images/` - 存放测试图片的目录

## 输出格式

识别结果采用 JSON 格式：

```json
{
  "foods": [
    {
      "en_name": "apple",
      "estimated_weight_grams": 150,
      "confidence": 0.9,
      "method": "raw"
    }
  ]
}
```

## 注意事项

- 需要有效的 OpenAI API Key
- 图片大小建议不超过 20MB
- 首次运行会自动创建 test_images 目录