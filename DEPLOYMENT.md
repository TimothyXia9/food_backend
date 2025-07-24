# 后端部署指南

## 部署文件说明

### Procfile
定义应用进程类型，用于Heroku、Railway等平台：
```
web: gunicorn calorie_tracker.wsgi:application --bind 0.0.0.0:$PORT
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
```

### runtime.txt
指定Python版本：
```
python-3.12.6
```

### app.json
Heroku应用配置文件，包含环境变量定义和插件配置。

## 部署平台

### 1. Railway部署

```bash
# 安装Railway CLI
npm install -g @railway/cli

# 登录Railway
railway login

# 初始化项目
railway init

# 设置环境变量
railway variables set FRONTEND_URL=https://your-frontend.vercel.app
railway variables set DEBUG=False
railway variables set SECRET_KEY=your-secret-key
railway variables set OPENAI_API_KEY=your-openai-key

# 部署
railway up
```

### 2. Heroku部署

```bash
# 安装Heroku CLI
# 登录Heroku
heroku login

# 创建应用
heroku create your-app-name

# 设置环境变量
heroku config:set FRONTEND_URL=https://your-frontend.vercel.app
heroku config:set DEBUG=False
heroku config:set SECRET_KEY=your-secret-key
heroku config:set OPENAI_API_KEY=your-openai-key

# 添加PostgreSQL数据库
heroku addons:create heroku-postgresql:mini

# 部署
git push heroku main
```

### 3. Vercel部署

创建 `vercel.json` 文件：
```json
{
  "version": 2,
  "builds": [
    {
      "src": "calorie_tracker/wsgi.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "calorie_tracker/wsgi.py"
    }
  ],
  "env": {
    "FRONTEND_URL": "https://your-frontend.vercel.app",
    "DEBUG": "False"
  }
}
```

### 4. Docker部署

创建 `Dockerfile`：
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 设置环境变量
ENV DEBUG=False
ENV FRONTEND_URL=https://your-frontend.com

# 收集静态文件
RUN python manage.py collectstatic --noinput

# 运行应用
CMD ["gunicorn", "calorie_tracker.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## 环境变量配置

### 必需环境变量
- `SECRET_KEY` - Django密钥
- `DEBUG` - 调试模式（生产环境设为False）
- `FRONTEND_URL` - 前端域名

### 可选环境变量  
- `OPENAI_API_KEY` - OpenAI API密钥（启用AI功能）
- `USDA_API_KEY` - USDA API密钥（增强营养数据）
- `DATABASE_URL` - 数据库连接字符串（自动检测）
- `ALLOWED_HOSTS` - 允许的主机列表
- `CORS_ALLOWED_ORIGINS` - CORS白名单

## 数据库配置

### PostgreSQL（推荐生产环境）
```bash
# 设置数据库URL
DATABASE_URL=postgresql://user:password@localhost:5432/calorie_tracker
```

### SQLite（默认开发环境）
无需额外配置，使用本地文件数据库。

## 静态文件服务

生产环境使用WhiteNoise处理静态文件：
- 自动压缩CSS/JS文件
- 设置合适的缓存头
- 支持Gzip压缩

## 部署检查清单

### 部署前
- [ ] 设置 `DEBUG=False`
- [ ] 配置 `SECRET_KEY`
- [ ] 设置 `FRONTEND_URL`
- [ ] 配置数据库连接
- [ ] 添加OpenAI API密钥

### 部署后
- [ ] 运行数据库迁移
- [ ] 收集静态文件
- [ ] 测试API端点
- [ ] 验证CORS配置
- [ ] 检查日志输出

## 故障排除

### 常见问题

#### 1. CORS错误
```bash
# 检查CORS配置
heroku config:get FRONTEND_URL
```

#### 2. 静态文件404
```bash
# 手动收集静态文件
heroku run python manage.py collectstatic --noinput
```

#### 3. 数据库连接错误
```bash
# 检查数据库配置
heroku config:get DATABASE_URL
heroku run python manage.py migrate
```

#### 4. 应用启动失败
```bash
# 查看日志
heroku logs --tail
railway logs
```

## 监控和维护

### 日志监控
```bash
# 实时查看日志
heroku logs --tail
railway logs --follow

# 检查特定时间段
heroku logs --since="2024-01-01"
```

### 性能优化
- 启用数据库连接池
- 配置Redis缓存
- 设置CDN服务静态文件
- 启用压缩中间件

### 定期维护
- 定期备份数据库
- 监控API使用量
- 更新依赖包
- 检查安全更新