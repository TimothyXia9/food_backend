# Railway PostgreSQL 部署指南

## 1. 准备步骤

### 1.1 安装依赖
确保你的 `requirements.txt` 包含PostgreSQL相关依赖:
```bash
psycopg2-binary==2.9.9
dj-database-url==2.1.0
```

### 1.2 更新数据库配置
Django settings.py 已经配置为自动检测Railway环境并使用PostgreSQL。

## 2. Railway部署步骤

### 2.1 创建Railway项目
1. 访问 [railway.app](https://railway.app)
2. 登录GitHub账号
3. 点击 "New Project"
4. 选择 "Deploy from GitHub repo"
5. 选择你的项目仓库

### 2.2 添加PostgreSQL数据库
1. 在Railway项目中点击 "New"
2. 选择 "Database" -> "PostgreSQL"
3. Railway会自动创建PostgreSQL实例并设置环境变量

### 2.3 配置环境变量
在Railway项目设置中添加以下环境变量:

#### 必需变量:
```bash
OPENAI_API_KEY=your-openai-api-key
SECRET_KEY=your-django-secret-key
DEBUG=False
RAILWAY_ENVIRONMENT=production
```

#### 可选变量:
```bash
USDA_API_KEY=your-usda-api-key
ALLOWED_HOSTS=your-app.railway.app,localhost
CORS_ALLOWED_ORIGINS=https://your-frontend.com,http://localhost:3000
```

### 2.4 数据库变量 (Railway自动设置)
Railway会自动为PostgreSQL服务设置以下变量:
- `DATABASE_URL`
- `PGDATABASE`
- `PGUSER` 
- `PGPASSWORD`
- `PGHOST`
- `PGPORT`

## 3. 部署配置文件

### 3.1 railway.toml
```toml
[build]
builder = "NIXPACKS"

[deploy]
healthcheckPath = "/api/v1/health/"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

[env]
PYTHONPATH = "/app/backend:$PYTHONPATH"
```

### 3.2 Procfile
```
web: python manage.py migrate --noinput && gunicorn calorie_tracker.wsgi:application --bind 0.0.0.0:$PORT --log-level info --access-logfile - --error-logfile -
release: python manage.py collectstatic --noinput
```

## 4. 部署验证

### 4.1 检查数据库连接
部署后访问: `https://your-app.railway.app/admin/`

### 4.2 API端点测试
```bash
# 健康检查
curl https://your-app.railway.app/api/v1/health/

# 用户注册
curl -X POST https://your-app.railway.app/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"testpass123"}'
```

## 5. 常见问题解决

### 5.1 数据库连接错误
- 确保PostgreSQL服务已启动
- 检查DATABASE_URL环境变量
- 验证数据库凭证

### 5.2 静态文件问题
- 确保STATIC_ROOT设置正确
- 运行collectstatic命令
- 检查WhiteNoise配置

### 5.3 CORS问题
- 更新CORS_ALLOWED_ORIGINS包含前端域名
- 确保ALLOWED_HOSTS包含Railway域名

## 6. 本地PostgreSQL测试

如果想在本地测试PostgreSQL配置:

### 6.1 安装PostgreSQL
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql
```

### 6.2 创建本地数据库
```bash
sudo -u postgres createdb calorie_tracker
sudo -u postgres createuser --interactive
```

### 6.3 设置本地环境变量
```bash
export DATABASE_URL="postgresql://username:password@localhost:5432/calorie_tracker"
```

### 6.4 运行迁移
```bash
cd backend
source venv/bin/activate
python manage.py migrate
python manage.py runserver
```

## 7. 生产环境优化

### 7.1 性能设置
```python
# settings.py 生产环境优化
CONN_MAX_AGE = 60
DATABASES['default']['CONN_MAX_AGE'] = 60
```

### 7.2 日志配置
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
```

## 8. 监控和维护

### 8.1 Railway控制台
- 查看实时日志
- 监控资源使用
- 管理环境变量

### 8.2 数据库备份
Railway会自动备份PostgreSQL数据，也可以手动创建备份点。

### 8.3 扩展配置
根据使用情况调整Railway服务配置和资源分配。