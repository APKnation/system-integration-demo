from django.urls import path
from .views import TransactionLogAPIView

urlpatterns = [
    path("logs/", TransactionLogAPIView.as_view(), name="transaction-log"),
]
