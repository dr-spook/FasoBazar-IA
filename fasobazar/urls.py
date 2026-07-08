from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.auth_trader.urls')),   # splash /, login, logout, signup
    path('', include('apps.dashboard.urls')),      # /app/, /journal/, /score/, /dashboard/
    path('api/', include('apps.api.urls')),
    path('webhook/', include('apps.webhook.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)