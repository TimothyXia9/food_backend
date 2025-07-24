"""
Custom middleware for enhanced logging and request tracking
"""

import logging
import time
import json
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse

# Get loggers
api_logger = logging.getLogger('api_requests')
debug_logger = logging.getLogger('debug')


class RequestLoggingMiddleware(MiddlewareMixin):
	"""
	Middleware to log all API requests and responses for debugging
	"""
	
	def process_request(self, request):
		"""Log incoming requests"""
		request.start_time = time.time()
		
		# Skip logging for static files and admin
		if request.path.startswith('/static/') or request.path.startswith('/admin/'):
			return None
		
		# Enhanced logging for Railway debugging
		api_logger.info(f"[REQUEST] {request.method} {request.path} from {request.META.get('REMOTE_ADDR', 'unknown')}")
		
		# Log request details
		log_data = {
			'method': request.method,
			'path': request.path,
			'user': str(request.user) if hasattr(request, 'user') and request.user.is_authenticated else 'Anonymous',
			'ip': self.get_client_ip(request),
			'user_agent': request.META.get('HTTP_USER_AGENT', ''),
			'content_type': request.META.get('CONTENT_TYPE', ''),
		}
		
		# Log query parameters
		if request.GET:
			log_data['query_params'] = dict(request.GET)
		
		# Log request body for POST/PUT/PATCH (but not for file uploads)
		if request.method in ['POST', 'PUT', 'PATCH']:
			if request.content_type and 'multipart/form-data' not in request.content_type:
				try:
					if hasattr(request, 'body') and request.body:
						body = request.body.decode('utf-8')
						# Don't log sensitive data like passwords
						if 'password' not in body.lower():
							log_data['request_body'] = body[:1000]  # Limit body size
						else:
							log_data['request_body'] = '[SENSITIVE DATA HIDDEN]'
				except Exception as e:
					log_data['request_body'] = f'[ERROR READING BODY: {str(e)}]'
			else:
				log_data['request_body'] = '[MULTIPART DATA]'
		
		api_logger.info(f"REQUEST START: {json.dumps(log_data, indent=2)}")
		debug_logger.debug(f"Request details: {log_data}")
		
		return None
	
	def process_response(self, request, response):
		"""Log response details"""
		
		# Skip logging for static files and admin
		if request.path.startswith('/static/') or request.path.startswith('/admin/'):
			return response
		
		# Calculate response time
		if hasattr(request, 'start_time'):
			response_time = time.time() - request.start_time
		else:
			response_time = 0
		
		# Log response details
		log_data = {
			'method': request.method,
			'path': request.path,
			'status_code': response.status_code,
			'response_time_ms': round(response_time * 1000, 2),
			'content_type': response.get('Content-Type', ''),
		}
		
		# Log response body for JSON responses (limit size)
		if isinstance(response, JsonResponse) or 'application/json' in response.get('Content-Type', ''):
			try:
				if hasattr(response, 'content'):
					content = response.content.decode('utf-8')
					if len(content) < 2000:  # Only log small responses
						log_data['response_body'] = content
					else:
						log_data['response_body'] = f'[LARGE RESPONSE: {len(content)} bytes]'
			except Exception as e:
				log_data['response_body'] = f'[ERROR READING RESPONSE: {str(e)}]'
		
		# Log with appropriate level based on status code
		if response.status_code >= 500:
			api_logger.error(f"REQUEST ERROR: {json.dumps(log_data, indent=2)}")
		elif response.status_code >= 400:
			api_logger.warning(f"REQUEST WARNING: {json.dumps(log_data, indent=2)}")
		else:
			api_logger.info(f"REQUEST SUCCESS: {json.dumps(log_data, indent=2)}")
		
		debug_logger.debug(f"Response details: {log_data}")
		
		return response
	
	def process_exception(self, request, exception):
		"""Log exceptions"""
		
		# Calculate response time if available
		if hasattr(request, 'start_time'):
			response_time = time.time() - request.start_time
		else:
			response_time = 0
		
		log_data = {
			'method': request.method,
			'path': request.path,
			'user': str(request.user) if hasattr(request, 'user') and request.user.is_authenticated else 'Anonymous',
			'ip': self.get_client_ip(request),
			'exception_type': type(exception).__name__,
			'exception_message': str(exception),
			'response_time_ms': round(response_time * 1000, 2),
		}
		
		api_logger.error(f"REQUEST EXCEPTION: {json.dumps(log_data, indent=2)}")
		debug_logger.error(f"Exception details: {log_data}", exc_info=True)
		
		return None
	
	def get_client_ip(self, request):
		"""Get the client's IP address"""
		x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
		if x_forwarded_for:
			ip = x_forwarded_for.split(',')[0]
		else:
			ip = request.META.get('REMOTE_ADDR')
		return ip


class PerformanceLoggingMiddleware(MiddlewareMixin):
	"""
	Middleware to log slow requests for performance monitoring
	"""
	
	def __init__(self, get_response):
		self.get_response = get_response
		self.slow_request_threshold = 1.0  # Log requests slower than 1 second
		super().__init__(get_response)
	
	def process_request(self, request):
		request.performance_start_time = time.time()
		return None
	
	def process_response(self, request, response):
		if hasattr(request, 'performance_start_time'):
			response_time = time.time() - request.performance_start_time
			
			# Log slow requests
			if response_time > self.slow_request_threshold:
				log_data = {
					'path': request.path,
					'method': request.method,
					'response_time_ms': round(response_time * 1000, 2),
					'status_code': response.status_code,
					'user': str(request.user) if hasattr(request, 'user') and request.user.is_authenticated else 'Anonymous',
				}
				
				api_logger.warning(f"SLOW REQUEST: {json.dumps(log_data)}")
		
		return response


class SecurityLoggingMiddleware(MiddlewareMixin):
	"""
	Middleware to log security-related events
	"""
	
	def process_request(self, request):
		# Log authentication attempts
		if request.path.endswith('/login') and request.method == 'POST':
			log_data = {
				'event': 'LOGIN_ATTEMPT',
				'ip': self.get_client_ip(request),
				'user_agent': request.META.get('HTTP_USER_AGENT', ''),
				'path': request.path,
			}
			api_logger.info(f"SECURITY EVENT: {json.dumps(log_data)}")
		
		# Log registration attempts
		if request.path.endswith('/register') and request.method == 'POST':
			log_data = {
				'event': 'REGISTRATION_ATTEMPT',
				'ip': self.get_client_ip(request),
				'user_agent': request.META.get('HTTP_USER_AGENT', ''),
				'path': request.path,
			}
			api_logger.info(f"SECURITY EVENT: {json.dumps(log_data)}")
		
		return None
	
	def get_client_ip(self, request):
		"""Get the client's IP address"""
		x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
		if x_forwarded_for:
			ip = x_forwarded_for.split(',')[0]
		else:
			ip = request.META.get('REMOTE_ADDR')
		return ip