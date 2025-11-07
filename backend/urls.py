from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

# Health check endpoints
from kbrs_api.views.health import health_check, readiness_check

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Health checks (no authentication required)
    path('health/', health_check, name='health'),
    path('readiness/', readiness_check, name='readiness'),

    # Authentication
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # API
    path('api/v1/', include('kbrs_api.urls')),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)