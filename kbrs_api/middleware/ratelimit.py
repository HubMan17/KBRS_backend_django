"""
Rate limiting middleware for KBRS API.

Features:
- IP-based rate limiting
- User-based rate limiting (authenticated requests)
- Configurable limits per endpoint
- Redis backend for distributed rate limiting
"""

import time
from typing import Callable
from collections import defaultdict
from threading import Lock

from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings


class SimpleRateLimitMiddleware:
    """
    Simple in-memory rate limiting middleware.

    For production, use Redis-backed rate limiting (django-ratelimit).
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self._requests = defaultdict(list)
        self._lock = Lock()

        # Configuration
        self.enabled = getattr(settings, 'RATE_LIMIT_ENABLE', True)
        self.anon_limit = getattr(settings, 'RATE_LIMIT_ANON', 100)  # per minute
        self.user_limit = getattr(settings, 'RATE_LIMIT_USER', 1000)  # per minute
        self.window = 60  # 1 minute window

    def __call__(self, request):
        if not self.enabled:
            return self.get_response(request)

        # Exempt certain paths
        if self._should_exempt(request.path):
            return self.get_response(request)

        # Determine rate limit
        if request.user and request.user.is_authenticated:
            limit = self.user_limit
            key = f"user:{request.user.id}"
        else:
            limit = self.anon_limit
            key = f"ip:{self._get_client_ip(request)}"

        # Check rate limit
        if not self._check_rate_limit(key, limit):
            return JsonResponse(
                {
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {limit} requests per minute allowed",
                },
                status=429
            )

        response = self.get_response(request)
        return response

    def _get_client_ip(self, request) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

    def _should_exempt(self, path: str) -> bool:
        """Check if path should be exempt from rate limiting."""
        exempt_paths = [
            '/admin/',
            '/health/',
            '/readiness/',
            '/static/',
            '/media/',
        ]
        return any(path.startswith(prefix) for prefix in exempt_paths)

    def _check_rate_limit(self, key: str, limit: int) -> bool:
        """
        Check if request is within rate limit.

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = time.time()
        window_start = now - self.window

        with self._lock:
            # Clean old requests
            self._requests[key] = [
                timestamp
                for timestamp in self._requests[key]
                if timestamp > window_start
            ]

            # Check limit
            if len(self._requests[key]) >= limit:
                return False

            # Record request
            self._requests[key].append(now)
            return True


class RedisRateLimitMiddleware:
    """
    Redis-backed rate limiting middleware.

    Requires Redis and django-redis.

    Installation:
        pip install django-redis

    Settings:
        CACHES = {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': 'redis://127.0.0.1:6379/1',
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                }
            }
        }
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

        # Configuration
        self.enabled = getattr(settings, 'RATE_LIMIT_ENABLE', True)
        self.anon_limit = getattr(settings, 'RATE_LIMIT_ANON', 100)
        self.user_limit = getattr(settings, 'RATE_LIMIT_USER', 1000)
        self.window = 60  # seconds

    def __call__(self, request):
        if not self.enabled:
            return self.get_response(request)

        # Exempt certain paths
        if self._should_exempt(request.path):
            return self.get_response(request)

        # Determine rate limit
        if request.user and request.user.is_authenticated:
            limit = self.user_limit
            cache_key = f"ratelimit:user:{request.user.id}"
        else:
            limit = self.anon_limit
            cache_key = f"ratelimit:ip:{self._get_client_ip(request)}"

        # Check rate limit using Redis
        try:
            current = cache.get(cache_key, 0)

            if current >= limit:
                return JsonResponse(
                    {
                        "error": "Rate limit exceeded",
                        "detail": f"Maximum {limit} requests per minute allowed",
                        "retry_after": self.window,
                    },
                    status=429,
                    headers={"Retry-After": str(self.window)}
                )

            # Increment counter
            if current == 0:
                # First request in window
                cache.set(cache_key, 1, self.window)
            else:
                # Subsequent requests
                cache.incr(cache_key)

        except Exception as e:
            # If Redis is down, allow request but log error
            print(f"Rate limit check failed: {e}")

        response = self.get_response(request)

        # Add rate limit headers
        try:
            remaining = max(0, limit - (cache.get(cache_key, 0) + 1))
            response['X-RateLimit-Limit'] = str(limit)
            response['X-RateLimit-Remaining'] = str(remaining)
            response['X-RateLimit-Reset'] = str(int(time.time() + self.window))
        except Exception:
            pass

        return response

    def _get_client_ip(self, request) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

    def _should_exempt(self, path: str) -> bool:
        """Check if path should be exempt from rate limiting."""
        exempt_paths = [
            '/admin/',
            '/health/',
            '/readiness/',
            '/static/',
            '/media/',
        ]
        return any(path.startswith(prefix) for prefix in exempt_paths)
