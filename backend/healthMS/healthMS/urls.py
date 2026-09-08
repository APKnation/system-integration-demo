from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from integration.views import TransactionLogAPIView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('hms.urls_auth')),
    path('api/hms/', include('hms.urls')),
    path('api/lis/', include('lis.urls')),
    path('api/logs/', TransactionLogAPIView.as_view(), name='api-logs'),
    path(
        '',
        TemplateView.as_view(template_name='dashboard.html'),
        name='dashboard',
    ),
]
