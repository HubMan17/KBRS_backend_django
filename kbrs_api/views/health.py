"""
Health check endpoints for monitoring and orchestration.

Endpoints:
- /health/ - Liveness probe (simple)
- /readiness/ - Readiness probe (checks dependencies)
"""

import time
from django.http import JsonResponse
from django.db import connection
from django.conf import settings


def health_check(request):
    """
    Basic liveness check.

    Returns 200 if service is running.
    Use for Kubernetes liveness probe.
    """
    return JsonResponse({
        "status": "ok",
        "service": "kbrs-backend",
        "version": "1.0.0",
        "timestamp": int(time.time()),
    })


def readiness_check(request):
    """
    Comprehensive readiness check.

    Checks:
    - Database connectivity
    - Celery workers (if configured)
    - Cache backend (if configured)

    Returns:
        200: All systems operational
        503: One or more systems unavailable
    """
    checks = {
        "database": _check_database(),
        "celery": _check_celery(),
    }

    # Optional checks
    if hasattr(settings, 'CACHES') and 'default' in settings.CACHES:
        checks["cache"] = _check_cache()

    all_ok = all(check["status"] == "ok" for check in checks.values())
    status_code = 200 if all_ok else 503

    response = {
        "ready": all_ok,
        "checks": checks,
        "timestamp": int(time.time()),
    }

    return JsonResponse(response, status=status_code)


def _check_database() -> dict:
    """Check PostgreSQL connectivity."""
    try:
        start = time.time()

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        latency_ms = int((time.time() - start) * 1000)

        return {
            "status": "ok",
            "latency_ms": latency_ms,
            "engine": settings.DATABASES['default']['ENGINE'],
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def _check_celery() -> dict:
    """Check Celery workers availability."""
    try:
        from celery import current_app

        # Get active workers
        inspect = current_app.control.inspect()
        stats = inspect.stats()

        if not stats:
            return {
                "status": "warning",
                "message": "No workers found",
            }

        worker_count = len(stats)

        return {
            "status": "ok",
            "workers": worker_count,
            "worker_names": list(stats.keys()),
        }

    except ImportError:
        return {
            "status": "disabled",
            "message": "Celery not installed",
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def _check_cache() -> dict:
    """Check cache backend connectivity."""
    try:
        from django.core.cache import cache

        start = time.time()

        # Test write
        test_key = "__health_check__"
        cache.set(test_key, "ok", timeout=10)

        # Test read
        value = cache.get(test_key)

        # Clean up
        cache.delete(test_key)

        latency_ms = int((time.time() - start) * 1000)

        if value != "ok":
            return {
                "status": "error",
                "error": "Cache read/write mismatch",
            }

        return {
            "status": "ok",
            "latency_ms": latency_ms,
            "backend": settings.CACHES['default']['BACKEND'],
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }
