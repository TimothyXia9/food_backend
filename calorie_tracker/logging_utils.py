"""
Logging utilities for the calorie tracker application
"""

import logging
import functools
import time
from typing import Any, Callable


def log_function_call(logger_name: str = None, log_level: int = logging.INFO):
	"""
	Decorator to log function calls with arguments and execution time
	
	Args:
		logger_name: Name of the logger to use (defaults to module name)
		log_level: Logging level to use
	"""
	def decorator(func: Callable) -> Callable:
		@functools.wraps(func)
		def wrapper(*args, **kwargs) -> Any:
			# Get logger
			if logger_name:
				logger = logging.getLogger(logger_name)
			else:
				logger = logging.getLogger(func.__module__)
			
			# Log function call
			func_name = f"{func.__module__}.{func.__name__}"
			start_time = time.time()
			
			# Log arguments (sanitize sensitive data)
			safe_args = []
			for arg in args:
				if hasattr(arg, '__dict__') and hasattr(arg, 'password'):
					safe_args.append('[USER_OBJECT]')
				else:
					safe_args.append(str(arg)[:100])  # Limit length
			
			safe_kwargs = {}
			for key, value in kwargs.items():
				if 'password' in key.lower():
					safe_kwargs[key] = '[HIDDEN]'
				else:
					safe_kwargs[key] = str(value)[:100]  # Limit length
			
			logger.log(log_level, f"CALLING {func_name} with args={safe_args}, kwargs={safe_kwargs}")
			
			try:
				# Execute function
				result = func(*args, **kwargs)
				
				# Log successful execution
				execution_time = time.time() - start_time
				logger.log(log_level, f"COMPLETED {func_name} in {execution_time:.3f}s")
				
				return result
				
			except Exception as e:
				# Log exception
				execution_time = time.time() - start_time
				logger.error(f"FAILED {func_name} after {execution_time:.3f}s: {str(e)}")
				raise
		
		return wrapper
	return decorator


def log_api_endpoint(logger_name: str = None):
	"""
	Decorator specifically for API endpoint logging
	"""
	def decorator(func: Callable) -> Callable:
		@functools.wraps(func)
		def wrapper(request, *args, **kwargs) -> Any:
			# Get logger
			if logger_name:
				logger = logging.getLogger(logger_name)
			else:
				logger = logging.getLogger('api_requests')
			
			# Extract request info
			user = str(request.user) if hasattr(request, 'user') and request.user.is_authenticated else 'Anonymous'
			endpoint = f"{request.method} {request.path}"
			
			start_time = time.time()
			logger.info(f"API CALL START: {endpoint} by {user}")
			
			try:
				# Execute function
				result = func(request, *args, **kwargs)
				
				# Log successful execution
				execution_time = time.time() - start_time
				status_code = getattr(result, 'status_code', 'Unknown')
				logger.info(f"API CALL SUCCESS: {endpoint} by {user} - {status_code} in {execution_time:.3f}s")
				
				return result
				
			except Exception as e:
				# Log exception
				execution_time = time.time() - start_time
				logger.error(f"API CALL FAILED: {endpoint} by {user} after {execution_time:.3f}s: {str(e)}")
				raise
		
		return wrapper
	return decorator


def log_external_service_call(service_name: str, logger_name: str = None):
	"""
	Decorator for logging external service calls (OpenAI, USDA, etc.)
	"""
	def decorator(func: Callable) -> Callable:
		@functools.wraps(func)
		def wrapper(*args, **kwargs) -> Any:
			# Get logger
			if logger_name:
				logger = logging.getLogger(logger_name)
			else:
				logger = logging.getLogger(f'{service_name.lower()}_service')
			
			start_time = time.time()
			func_name = f"{service_name}.{func.__name__}"
			
			logger.info(f"EXTERNAL CALL START: {func_name}")
			
			try:
				# Execute function
				result = func(*args, **kwargs)
				
				# Log successful execution
				execution_time = time.time() - start_time
				logger.info(f"EXTERNAL CALL SUCCESS: {func_name} in {execution_time:.3f}s")
				
				return result
				
			except Exception as e:
				# Log exception
				execution_time = time.time() - start_time
				logger.error(f"EXTERNAL CALL FAILED: {func_name} after {execution_time:.3f}s: {str(e)}")
				raise
		
		return wrapper
	return decorator


class DatabaseQueryLogger:
	"""
	Context manager for logging database queries
	"""
	
	def __init__(self, operation: str, logger_name: str = 'database'):
		self.operation = operation
		self.logger = logging.getLogger(logger_name)
		self.start_time = None
	
	def __enter__(self):
		self.start_time = time.time()
		self.logger.debug(f"DATABASE QUERY START: {self.operation}")
		return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		execution_time = time.time() - self.start_time
		
		if exc_type is None:
			self.logger.debug(f"DATABASE QUERY SUCCESS: {self.operation} in {execution_time:.3f}s")
		else:
			self.logger.error(f"DATABASE QUERY FAILED: {self.operation} after {execution_time:.3f}s: {exc_val}")


def get_logger_for_module(module_name: str, level: int = logging.INFO) -> logging.Logger:
	"""
	Get a configured logger for a specific module
	
	Args:
		module_name: Name of the module
		level: Logging level
		
	Returns:
		Configured logger instance
	"""
	logger = logging.getLogger(module_name)
	logger.setLevel(level)
	return logger


def log_user_action(user, action: str, details: dict = None, logger_name: str = 'user_actions'):
	"""
	Log user actions for audit trail
	
	Args:
		user: User object
		action: Action description
		details: Additional details to log
		logger_name: Logger name to use
	"""
	logger = logging.getLogger(logger_name)
	
	log_data = {
		'user_id': user.id if user and hasattr(user, 'id') else None,
		'username': user.username if user and hasattr(user, 'username') else 'Anonymous',
		'action': action,
		'timestamp': time.time(),
	}
	
	if details:
		log_data['details'] = details
	
	logger.info(f"USER ACTION: {log_data}")


def sanitize_log_data(data: dict) -> dict:
	"""
	Sanitize sensitive data from log entries
	
	Args:
		data: Dictionary containing data to sanitize
		
	Returns:
		Sanitized dictionary
	"""
	sensitive_keys = ['password', 'token', 'secret', 'key', 'api_key']
	sanitized = {}
	
	for key, value in data.items():
		if any(sensitive in key.lower() for sensitive in sensitive_keys):
			sanitized[key] = '[HIDDEN]'
		elif isinstance(value, dict):
			sanitized[key] = sanitize_log_data(value)
		elif isinstance(value, str) and len(value) > 200:
			sanitized[key] = value[:200] + '...[TRUNCATED]'
		else:
			sanitized[key] = value
	
	return sanitized