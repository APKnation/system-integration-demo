import logging
import uuid
from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from integration.logging_util import log_transaction

from .models import LabOrder, LabResult, LabTestCatalog
from .serializers import (
    LabOrderIngestSerializer,
    LabOrderSerializer,
    LabResultSerializer,
    LabTestCatalogSerializer,
)

logger = logging.getLogger(__name__)


class LabOrderIngestView(APIView):
    """GET/POST /api/lis/orders/ - the LIS-side endpoint the HMS posts to."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = LabOrder.objects.select_related("result").all()
        return Response(LabOrderSerializer(orders, many=True).data)

    def post(self, request):
        serializer = LabOrderIngestSerializer(data=request.data)
        if not serializer.is_valid():
            log_transaction(
                endpoint=request.path,
                method=request.method,
                status_code=status.HTTP_400_BAD_REQUEST,
                status="VALIDATION_ERROR",
                error_message=str(serializer.errors),
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Idempotency: a repeated request_id returns the existing order.
        existing = LabOrder.objects.filter(hms_request_id=data["request_id"]).first()
        if existing is not None:
            log_transaction(
                endpoint=request.path,
                method=request.method,
                status_code=status.HTTP_200_OK,
                status="DUPLICATE_IGNORED",
            )
            return Response(
                {
                    "accepted": True,
                    "order_number": existing.order_number,
                    "status": existing.status,
                    "reason": "Duplicate request_id; returning existing order.",
                },
                status=status.HTTP_200_OK,
            )

        dob = data["patient_date_of_birth"]
        if dob > date.today():
            log_transaction(
                endpoint=request.path,
                method=request.method,
                status_code=status.HTTP_400_BAD_REQUEST,
                status="VALIDATION_ERROR",
                error_message="patient_date_of_birth is in the future.",
            )
            return Response(
                {"patient_date_of_birth": ["Date of birth cannot be in the future."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        catalog_entry = LabTestCatalog.objects.filter(
            code=data["test_code"], is_active=True
        ).first()
        if catalog_entry is None:
            reason = f"Unknown or inactive test code '{data['test_code']}'."
            log_transaction(
                endpoint=request.path,
                method=request.method,
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                status="UNKNOWN_TEST_CODE",
                error_message=reason,
            )
            return Response(
                {"accepted": False, "detail": reason},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        order_number = (
            f"LIS-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        )

        try:
            with transaction.atomic():
                order = LabOrder.objects.create(
                    order_number=order_number,
                    hms_request_id=data["request_id"],
                    patient_number=data["patient_number"],
                    patient_name=f"{data['patient_first_name']} {data['patient_last_name']}",
                    patient_date_of_birth=dob,
                    test_code=data["test_code"],
                    test_name=catalog_entry.name,
                    status=LabOrder.Status.ACCEPTED,
                )
        except Exception as exc:
            log_transaction(
                endpoint=request.path,
                method=request.method,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="DB_ERROR",
                error_message=str(exc),
            )
            logger.exception("Failed to persist lab order")
            return Response(
                {"detail": "Could not persist lab order."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        log_transaction(
            endpoint=request.path,
            method=request.method,
            status_code=status.HTTP_201_CREATED,
            status="ORDER_ACCEPTED",
            request_id=data["request_id"],
        )
        return Response(
            {
                "accepted": True,
                "order_number": order.order_number,
                "status": order.status,
                "test_code": order.test_code,
                "test_name": order.test_name,
                "reason": "",
            },
            status=status.HTTP_201_CREATED,
        )


class LabOrderStatusView(APIView):
    """GET /api/lis/orders/<request_id>/ - HMS polls order status here."""

    permission_classes = [IsAuthenticated]

    def get(self, request, request_id: uuid.UUID):
        order = LabOrder.objects.filter(hms_request_id=request_id).select_related(
            "result"
        ).first()
        if order is None:
            log_transaction(
                endpoint=request.path,
                method=request.method,
                status_code=status.HTTP_404_NOT_FOUND,
                status="ORDER_NOT_FOUND",
                request_id=request_id,
            )
            return Response(
                {"detail": "No lab order found for this request_id."},
                status=status.HTTP_404_NOT_FOUND,
            )

        log_transaction(
            endpoint=request.path,
            method=request.method,
            status_code=status.HTTP_200_OK,
            status="ORDER_STATUS_QUERIED",
            request_id=request_id,
        )
        return Response(LabOrderSerializer(order).data)


class LabResultView(APIView):
    """GET /api/lis/orders/<request_id>/result/ - result retrieval endpoint."""

    permission_classes = [IsAuthenticated]

    def get(self, request, request_id: uuid.UUID):
        order = LabOrder.objects.filter(hms_request_id=request_id).select_related(
            "result"
        ).first()
        if order is None:
            log_transaction(
                endpoint=request.path,
                method=request.method,
                status_code=status.HTTP_404_NOT_FOUND,
                status="ORDER_NOT_FOUND",
                request_id=request_id,
            )
            return Response(
                {"detail": "No lab order found for this request_id."},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = getattr(order, "result", None)
        if result is None:
            log_transaction(
                endpoint=request.path,
                method=request.method,
                status_code=status.HTTP_409_CONFLICT,
                status="RESULT_NOT_READY",
                request_id=request_id,
            )
            return Response(
                {
                    "detail": "Result not available yet.",
                    "order_number": order.order_number,
                    "order_status": order.status,
                },
                status=status.HTTP_409_CONFLICT,
            )

        log_transaction(
            endpoint=request.path,
            method=request.method,
            status_code=status.HTTP_200_OK,
            status="RESULT_RETRIEVED",
            request_id=request_id,
        )
        return Response(
            {
                "order_number": order.order_number,
                "order_status": order.status,
                "result": LabResultSerializer(result).data,
            }
        )


class LabOrderStatusUpdateView(APIView):
    """PATCH /api/lis/orders/<request_id>/status/ - update order status."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, request_id: uuid.UUID):
        order = LabOrder.objects.filter(hms_request_id=request_id).first()
        if order is None:
            return Response(
                {"detail": "No lab order found for this request_id."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = LabOrderStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_status = serializer.validated_data["status"]
        old_status = order.status

        # Only allow forward transitions
        allowed = {
            "ACCEPTED": ["IN_PROGRESS"],
            "IN_PROGRESS": ["COMPLETED"],
        }
        if new_status not in allowed.get(old_status, []):
            return Response(
                {
                    "detail": (
                        f"Cannot transition from {old_status} to {new_status}. "
                        f"Allowed: {allowed.get(old_status, [])}"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # If completing, ensure result exists
        if new_status == "COMPLETED" and not hasattr(order, "result"):
            return Response(
                {"detail": "Cannot complete order without a recorded result."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = new_status
        order.save(update_fields=["status", "updated_at"])

        log_transaction(
            endpoint=request.path,
            method="PATCH",
            status_code=status.HTTP_200_OK,
            status="ORDER_STATUS_UPDATED",
            request_id=request_id,
            error_message=f"{old_status} -> {new_status}",
        )

        return Response(
            {
                "order_number": order.order_number,
                "status": order.status,
                "previous_status": old_status,
            }
        )


class LabOrderProcessView(APIView):
    """POST /api/lis/orders/<request_id>/process/

    Lab staff record the analysis result; the order is marked COMPLETED.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, request_id: uuid.UUID):
        order = LabOrder.objects.filter(hms_request_id=request_id).first()
        if order is None:
            return Response(
                {"detail": "No lab order found for this request_id."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if hasattr(order, "result"):
            return Response(
                {"detail": "Result has already been recorded for this order."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = LabResultSerializer(data=request.data)
        if not serializer.is_valid():
            log_transaction(
                endpoint=request.path,
                method=request.method,
                status_code=status.HTTP_400_BAD_REQUEST,
                status="VALIDATION_ERROR",
                error_message=str(serializer.errors),
                request_id=request_id,
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        performed_by = serializer.validated_data.get("performed_by") or ""
        if not performed_by.strip():
            return Response(
                {"performed_by": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                result = serializer.save(order=order)
                order.status = LabOrder.Status.COMPLETED
                order.save(update_fields=["status", "updated_at"])
        except Exception as exc:
            log_transaction(
                endpoint=request.path,
                method=request.method,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="DB_ERROR",
                error_message=str(exc),
                request_id=request_id,
            )
            logger.exception("Failed to persist lab result")
            return Response(
                {"detail": "Could not persist lab result."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        log_transaction(
            endpoint=request.path,
            method=request.method,
            status_code=status.HTTP_201_CREATED,
            status="RESULT_RECORDED",
            request_id=request_id,
        )
        return Response(
            {
                "detail": "Result recorded; order completed.",
                "order_number": order.order_number,
                "order_status": order.status,
                "result": LabResultSerializer(result).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LabTestCatalogView(APIView):
    """GET /api/lis/catalog/ - list of tests the LIS can perform."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        catalog = LabTestCatalog.objects.filter(is_active=True)
        serializer = LabTestCatalogSerializer(catalog, many=True)
        log_transaction(
            endpoint=request.path,
            method=request.method,
            status_code=status.HTTP_200_OK,
            status="CATALOG_QUERIED",
        )
        return Response(serializer.data)
