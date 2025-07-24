#!/bin/bash

# 设置错误时退出
set -e

echo "Starting Django application..."

# 创建必要的目录
echo "Creating necessary directories..."
mkdir -p staticfiles
mkdir -p media
mkdir -p logs


echo "Running database migrations..."
python manage.py migrate --noinput

# 收集静态文件
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# 可选：创建超级用户（如果需要）
# if [ "$CREATE_SUPERUSER" = "true" ]; then
#     echo "👤 Creating superuser..."
#     python manage.py createsuperuser --noinput || echo "Superuser already exists"
# fi

echo "Starting Gunicorn server..."

# 启动 Gunicorn
exec gunicorn calorie_tracker.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info