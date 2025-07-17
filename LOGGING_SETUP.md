# Django Logging Setup - Complete Guide

## Overview

This document describes the comprehensive logging system implemented for the Django calorie tracker backend. The logging system is designed to help with debugging, monitoring, and troubleshooting API requests and application behavior.

## 📁 Log Files Structure

All log files are stored in `/backend/logs/` directory:

```
logs/
├── django.log        # General Django application logs
├── debug.log         # Detailed debug information including SQL queries
├── api.log           # API request/response logs with detailed timing
├── error.log         # Error and exception logs
├── openai.log        # OpenAI service calls and responses
└── usda.log          # USDA API integration logs
```

## 🔧 Logging Configuration

### Log Levels

- **DEBUG**: Detailed information for diagnosing problems
- **INFO**: General information about application operation
- **WARNING**: Something unexpected happened but the app is still working
- **ERROR**: A serious problem occurred

### Log Formats

#### Verbose Format
```
[LEVEL] timestamp logger_name process_id thread_id - message
```

#### Simple Format
```
[LEVEL] timestamp - message
```

#### Detailed Format
```
[LEVEL] timestamp logger_name function_name:line_number - message
```

## 🔍 What Gets Logged

### 1. API Request/Response Logging

**Automatically logs:**
- All incoming HTTP requests (method, path, user, IP, user agent)
- Request parameters and body (sensitive data hidden)
- Response status codes and timing
- Response body (for JSON responses under 2KB)
- Slow requests (>1 second)
- Failed requests with stack traces

**Example API Log:**
```json
[INFO] 2025-07-15 00:46:43,729 api_requests - REQUEST START: {
  "method": "POST",
  "path": "/api/v1/auth/register",
  "user": "Anonymous",
  "ip": "127.0.0.1",
  "user_agent": "curl/8.5.0",
  "content_type": "application/json",
  "request_body": "[SENSITIVE DATA HIDDEN]"
}
```

### 2. Authentication Events

**Logs all:**
- User registration attempts and results
- Login attempts (success/failure)
- Token refresh operations
- Logout events
- Profile updates

**Example:**
```
[INFO] accounts - User registration attempt for username: testuser123
[INFO] accounts - User registered successfully: testuser123 (ID: 4)
```

### 3. Database Queries

**Logs:**
- SQL queries with execution time
- Database connection info
- Query performance (in debug mode)

### 4. External Service Calls

**Future implementation for:**
- OpenAI API calls (food recognition)
- USDA API calls (nutrition data)
- Response times and error rates

### 5. Security Events

**Logs:**
- Failed authentication attempts
- Suspicious request patterns
- Token blacklisting events

## 📊 Custom Middleware

### RequestLoggingMiddleware
- Logs all incoming requests and outgoing responses
- Tracks request timing and user information
- Hides sensitive data (passwords, tokens)
- Handles exceptions and errors

### PerformanceLoggingMiddleware
- Identifies slow requests (>1 second)
- Helps identify performance bottlenecks
- Tracks response times for optimization

### SecurityLoggingMiddleware
- Logs security-related events
- Tracks login/registration attempts
- Monitors for suspicious activity

## 🛠 Usage Examples

### Viewing Real-time Logs

```bash
# Watch all API requests
tail -f logs/api.log

# Watch for errors
tail -f logs/error.log

# Watch debug information
tail -f logs/debug.log

# Watch specific service logs
tail -f logs/openai.log
tail -f logs/usda.log
```

### Filtering Logs

```bash
# Find all registration attempts
grep "registration attempt" logs/api.log

# Find failed requests
grep "REQUEST ERROR" logs/api.log

# Find slow requests
grep "SLOW REQUEST" logs/api.log

# Find specific user actions
grep "testuser123" logs/api.log
```

### Log Analysis Commands

```bash
# Count requests by endpoint
grep "REQUEST START" logs/api.log | grep -o '"/api/v1/[^"]*"' | sort | uniq -c

# Find average response times
grep "response_time_ms" logs/api.log | grep -o '"response_time_ms": [0-9.]*' | awk -F': ' '{sum+=$2; count++} END {print "Average:", sum/count, "ms"}'

# Find error patterns
grep "REQUEST ERROR" logs/api.log | grep -o '"status_code": [0-9]*' | sort | uniq -c
```

## 🎯 Debugging Common Issues

### 1. Authentication Problems

**Check these logs:**
```bash
# Look for login failures
grep "Login failed" logs/api.log

# Check token issues
grep "AUTHENTICATION_ERROR" logs/api.log

# View security events
grep "SECURITY EVENT" logs/api.log
```

### 2. Performance Issues

**Check these logs:**
```bash
# Find slow requests
grep "SLOW REQUEST" logs/api.log

# Check database query times
grep "django.db.backends" logs/debug.log

# Look for long response times
grep "response_time_ms" logs/api.log | awk -F'"response_time_ms": ' '{print $2}' | awk -F',' '{print $1}' | sort -n | tail -10
```

### 3. API Endpoint Issues

**Check these logs:**
```bash
# Find 4xx errors (client errors)
grep "status_code": 4[0-9][0-9]' logs/api.log

# Find 5xx errors (server errors)
grep '"status_code": 5[0-9][0-9]' logs/api.log

# Check specific endpoint
grep "/api/v1/foods/search" logs/api.log
```

### 4. External Service Issues

**Check these logs:**
```bash
# OpenAI service problems
tail -f logs/openai.log

# USDA service problems  
tail -f logs/usda.log

# Check for timeout errors
grep "timeout\|TimeoutError" logs/*.log
```

## 🔧 Log Rotation

Logs are automatically rotated when they reach 10MB (5MB for USDA logs):
- **django.log**: 5 backup files
- **debug.log**: 3 backup files  
- **api.log**: 5 backup files
- **error.log**: 5 backup files
- **openai.log**: 3 backup files
- **usda.log**: 3 backup files

## 🚀 Production Considerations

### Log Level Adjustments

For production, consider changing log levels in `settings.py`:

```python
# Production logging levels
'loggers': {
    'django': {
        'level': 'WARNING',  # Reduce django logs
    },
    'django.db.backends': {
        'level': 'ERROR',    # Disable SQL query logging
    },
    'api_requests': {
        'level': 'INFO',     # Keep API logging
    },
}
```

### Log Monitoring

Consider implementing:
- Log aggregation (ELK Stack, Splunk)
- Error alerting (email/Slack notifications)
- Log analysis dashboards
- Automated log cleanup policies

### Security

- Ensure log files have proper permissions
- Implement log encryption for sensitive data
- Regular log backup and archival
- Monitor log file sizes and disk usage

## 🧪 Testing the Logging System

### Test API Logging

```bash
# Test successful registration
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"testpass123"}'

# Test failed login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"wrongpassword"}'

# Check the logs
tail -f logs/api.log
```

### Test Performance Logging

```bash
# Make multiple rapid requests to test performance logging
for i in {1..5}; do
  curl -X GET http://localhost:8000/api/v1/foods/search?query=apple &
done

# Check for slow request logs
grep "SLOW REQUEST" logs/api.log
```

## 📋 Log Retention Policy

| Log File | Retention | Reason |
|----------|-----------|---------|
| `api.log` | 30 days | API debugging and monitoring |
| `debug.log` | 7 days | Development debugging only |
| `django.log` | 30 days | General application monitoring |
| `error.log` | 90 days | Long-term error analysis |
| `openai.log` | 14 days | External service monitoring |
| `usda.log` | 14 days | External service monitoring |

## 🚨 Troubleshooting

### Common Issues

1. **Log files not created**: Check directory permissions
2. **No logs appearing**: Verify middleware is loaded
3. **Too much logging**: Adjust log levels in settings
4. **Disk space issues**: Implement log rotation and cleanup

### Quick Fixes

```bash
# Fix log directory permissions
chmod 755 logs/
chmod 644 logs/*.log

# Clear old logs (be careful!)
rm logs/*.log.1 logs/*.log.2

# Test logging configuration
python manage.py check

# Restart Django to reload logging config
# (kill and restart the runserver process)
```

This comprehensive logging system provides excellent visibility into your Django application's behavior and will help you quickly identify and resolve issues.