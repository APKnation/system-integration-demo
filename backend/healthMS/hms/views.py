import uuid

from django.db import IntegrityError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from integration.logging_util import log_transaction
from integration.lis_client import LISClient, LISClientError

from .models import LabRequest, Patient
from .serializers import (
    LabRequestCreateSerializer,
    LabRequestSerializer,
    PatientSerializer,
)


class PatientListCreateView(APIView):
    """GET /api/hms/patients/ and POST /api/hms/patients/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        patients = Patient.objects.all()
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PatientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()
        return Response(
            PatientSerializer(patient).data, status=status.HTTP_201_CREATED
        )


class LabRequestListCreateView(APIView):
    """GET /api/hms/lab-requests/ and POST /api/hms/lab-requests/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        requests_qs = LabRequest.objects.select_related("patient").all()
        serializer = LabRequestSerializer(requests_qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = LabRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Idempotency: a repeated request_id re-uses the stored request
        # instead of raising a uniqueness error (retry-safe submission).
        request_id = serializer.validated_data.get("request_id")
        lab_request = (
            LabRequest.objects.filter(request_id=request_id).first()
            if request_id is not None
            else None
        )
        created = False
        if lab_request is None:
            try:
                lab_request = serializer.save()  # status=PENDING
                created = True
            except IntegrityError:
                lab_request = LabRequest.objects.get(request_id=request_id)
        else:
            # Retry semantics: refresh the payload fields, keep the same
            # request_id as the correlation key.
            patient = Patient.objects.get(
                patient_number=serializer.validated_data["patient_number"]
            )
            lab_request.patient = patient
            lab_request.test_code = serializer.validated_data["test_code"]
            lab_request.test_name = serializer.validated_data["test_name"]
            lab_request.save(update_fields=[
                "patient", "test_code", "test_name", "updated_at"
            ])

        client = LISClient(user=request.user)
        response_data, error = client.submit_lab_request(lab_request)

        if error is not None:
            # submit_lab_request already updated the LabRequest status
            # (REJECTED/ERROR) and wrote a transaction log entry.
            return Response(
                {
                    "detail": error["detail"],
                    "request_id": str(lab_request.request_id),
                    "status": lab_request.status,
                    "lis_order_number": lab_request.lis_order_number,
                    "rejection_reason": lab_request.rejection_reason,
                    "upstream_status_code": error.get("status_code"),
                },
                status=error["status_code"],
            )

        lab_request.refresh_from_db()
        return Response(
            {
                "detail": (
                    "Lab test request submitted to LIS successfully."
                    if created
                    else "Lab test request already exists; returning existing order."
                ),
                "request_id": str(lab_request.request_id),
                "status": lab_request.status,
                "lis_order_number": lab_request.lis_order_number,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class LabRequestResultView(APIView):
    """GET /api/hms/lab-requests/<request_id>/result/

    The HMS asks the LIS for the patient's lab result via LISClient.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, request_id: uuid.UUID):
        lab_request = LabRequest.objects.filter(request_id=request_id).first()
        if lab_request is None:
            return Response(
                {"detail": "Lab request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        client = LISClient(user=request.user)
        data, error = client.get_result(lab_request.request_id)
        if error is not None:
            return Response(
                {
                    "detail": error["detail"],
                    "request_id": str(lab_request.request_id),
                    "lis_status_code": error.get("status_code"),
                },
                status=error["status_code"],
            )

        return Response(
            {
                "request_id": str(lab_request.request_id),
                "patient_number": lab_request.patient.patient_number,
                "test_code": lab_request.test_code,
                "lis_order_number": lab_request.lis_order_number,
                **data,
            }
        )
