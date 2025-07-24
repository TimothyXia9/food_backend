#!/bin/bash

# 更安全的启动脚本，专门为Railway优化

# 设置错误处理
set -e

echo "🚀 Starting Django application for Railway..."

# 检查并设置默认端口
if [ -z "$PORT" ]; then
    export PORT=8000
    echo "⚠️  PORT not set, using default: $PORT"
else
    echo "✅ Using PORT: $PORT"
fi

# 设置Railway环境标识
export RAILWAY_ENVIRONMENT=1

# 检查Python和Django
echo "🔍 Checking Python and Django..."
python --version
python -c "import django; print(f'Django version: {django.get_version()}')"

# 运行数据库迁移
echo "📊 Running database migrations..."
python manage.py migrate --noinput

# 收集静态文件
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput --clear

# 创建必要的目录
echo "📂 Creating necessary directories..."
mkdir -p /tmp/media
chmod 755 /tmp/media

# 验证Gunicorn配置
echo "🔧 Testing Gunicorn configuration..."
gunicorn --check-config calorie_tracker.wsgi:application

# 启动应用
echo "🌟 Starting Gunicorn server..."
echo "   - Host: 0.0.0.0"
echo "   - Port: $PORT"
echo "   - Workers: 2"
echo "   - Timeout: 120s"

exec gunicorn calorie_tracker.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --worker-class sync \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 120 \
    --keepalive 5 \
    --preload \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --capture-output