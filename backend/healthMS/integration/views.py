from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import IntegrationLog


class IntegrationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationLog
        fields = [
            "transaction_id",
            "request_id",
            "endpoint",
            "method",
            "status_code",
            "status",
            "error_message",
            "created_at",
        ]


class TransactionLogAPIView(APIView):
    """GET /api/logs/?limit=50 - recent integration transaction log entries."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            limit = max(1, min(int(request.query_params.get("limit", "50")), 200))
        except (TypeError, ValueError):
            limit = 50
        qs = IntegrationLog.objects.all()[:limit]
        return Response(IntegrationLogSerializer(qs, many=True).data)
