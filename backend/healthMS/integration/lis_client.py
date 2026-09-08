"""HTTP client the Hospital Management System uses to talk to the LIS API.

Demonstrates:
- service-to-service authentication (JWT via token endpoint)
- request submission and result retrieval
- response handling and structured error handling
- transaction logging for every outbound call
"""

import logging
from urllib.parse import urljoin

import requests
from django.conf import settings

from .logging_util import log_transaction

logger = logging.getLogger(__name__)


class LISClientError(Exception):
    """Raised when the LIS cannot be reached or returns an error response."""

    def __init__(self, detail, status_code=None, kind="ERROR"):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.kind = kind  # AUTH_ERROR | VALIDATION_ERROR | REJECTED | SERVER_ERROR | CONNECTION_ERROR


class LISClient:
    """Thin wrapper around the LIS REST API used by HMS views."""

    def __init__(self, user=None, base_url=None, timeout=None):
        self.base_url = (base_url or settings.LIS_API_BASE_URL).rstrip("/") + "/"
        self.timeout = timeout or settings.LIS_TIMEOUT_SECONDS
        self._token = None
        self._user = user

    # ------------------------------------------------------------------ auth

    def _authenticate(self):
        url = urljoin(self.base_url, "api/auth/token/")
        try:
            resp = requests.post(
                url,
                json={
                    "username": settings.LIS_SERVICE_USERNAME,
                    "password": settings.LIS_SERVICE_PASSWORD,
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise LISClientError(
                f"Could not reach LIS authentication endpoint: {exc}",
                kind="CONNECTION_ERROR",
            )
        if resp.status_code != 200:
            raise LISClientError(
                "LIS authentication failed.",
                status_code=resp.status_code,
                kind="AUTH_ERROR",
            )
        self._token = resp.json().get("access")

    def _request(self, method, path, payload=None):
        url = urljoin(self.base_url, path)
        for attempt in (1, 2):
            if self._token is None:
                self._authenticate()
            headers = {
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            }
            try:
                resp = requests.request(
                    method, url, json=payload, headers=headers, timeout=self.timeout
                )
            except requests.RequestException as exc:
                raise LISClientError(
                    f"Could not reach LIS endpoint {url}: {exc}",
                    kind="CONNECTION_ERROR",
                )
            if resp.status_code == 401 and attempt == 1:
                # Token may have expired: re-authenticate once and retry.
                self._token = None
                continue
            return resp
        raise LISClientError(
            "LIS authentication failed.", status_code=401, kind="AUTH_ERROR"
        )

    # ----------------------------------------------------------------- apis

    def submit_lab_request(self, lab_request):
        """Submit a LabRequest to the LIS.

        Updates the LabRequest (status / order number / rejection reason),
        writes a transaction log entry, and returns (data, error).
        """
        patient = lab_request.patient
        payload = {
            "request_id": str(lab_request.request_id),
            "patient_number": patient.patient_number,
            "patient_first_name": patient.first_name,
            "patient_last_name": patient.last_name,
            "patient_date_of_birth": patient.date_of_birth.isoformat(),
            "test_code": lab_request.test_code,
            "test_name": lab_request.test_name,
        }
        endpoint = "api/lis/orders/"

        try:
            resp = self._request("POST", endpoint, payload)
        except LISClientError as exc:
            lab_request.status = lab_request.Status.ERROR
            lab_request.rejection_reason = exc.detail
            lab_request.save(update_fields=["status", "rejection_reason", "updated_at"])
            log_transaction(
                endpoint=endpoint,
                method="POST",
                status_code=exc.status_code or 503,
                status=exc.kind,
                error_message=exc.detail,
                request_id=lab_request.request_id,
            )
            return None, {
                "detail": exc.detail,
                "status_code": exc.status_code or 503,
            }

        if resp.status_code in (200, 201):
            data = resp.json()
            if lab_request.status != lab_request.Status.COMPLETED:
                # Never downgrade a COMPLETED request on a duplicate submit.
                lab_request.status = lab_request.Status.SENT
            lab_request.lis_order_number = data.get("order_number") or ""
            lab_request.rejection_reason = ""
            lab_request.save(
                update_fields=["status", "lis_order_number", "rejection_reason", "updated_at"]
            )
            log_transaction(
                endpoint=endpoint,
                method="POST",
                status_code=resp.status_code,
                status="ORDER_SUBMITTED",
                request_id=lab_request.request_id,
            )
            return data, None

        if resp.status_code == 422:
            detail = resp.json().get("detail", "LIS rejected the request.")
            lab_request.status = lab_request.Status.REJECTED
            lab_request.rejection_reason = detail
            lab_request.save(update_fields=["status", "rejection_reason", "updated_at"])
            log_transaction(
                endpoint=endpoint,
                method="POST",
                status_code=resp.status_code,
                status="REJECTED_BY_LIS",
                error_message=detail,
                request_id=lab_request.request_id,
            )
            return None, {"detail": detail, "status_code": resp.status_code}

        if resp.status_code == 400:
            detail = f"LIS validation error: {resp.json()}"
            lab_request.status = lab_request.Status.REJECTED
            lab_request.rejection_reason = detail
            lab_request.save(update_fields=["status", "rejection_reason", "updated_at"])
            log_transaction(
                endpoint=endpoint,
                method="POST",
                status_code=resp.status_code,
                status="VALIDATION_ERROR",
                error_message=detail,
                request_id=lab_request.request_id,
            )
            return None, {"detail": detail, "status_code": resp.status_code}

        detail = f"Unexpected LIS response (HTTP {resp.status_code})."
        lab_request.status = lab_request.Status.ERROR
        lab_request.rejection_reason = detail
        lab_request.save(update_fields=["status", "rejection_reason", "updated_at"])
        log_transaction(
            endpoint=endpoint,
            method="POST",
            status_code=resp.status_code,
            status="SERVER_ERROR",
            error_message=detail,
            request_id=lab_request.request_id,
        )
        return None, {"detail": detail, "status_code": 502}

    def get_result(self, request_id):
        """Retrieve the lab result for a request_id. Returns (data, error)."""
        endpoint = f"api/lis/orders/{request_id}/result/"
        try:
            resp = self._request("GET", endpoint)
        except LISClientError as exc:
            log_transaction(
                endpoint=endpoint,
                method="GET",
                status_code=exc.status_code or 503,
                status=exc.kind,
                error_message=exc.detail,
                request_id=request_id,
            )
            return None, {"detail": exc.detail, "status_code": exc.status_code or 503}

        if resp.status_code == 200:
            log_transaction(
                endpoint=endpoint,
                method="GET",
                status_code=200,
                status="RESULT_RETRIEVED",
                request_id=request_id,
            )
            return resp.json(), None

        if resp.status_code == 404:
            detail = "No lab order found on the LIS for this request_id."
            log_transaction(
                endpoint=endpoint,
                method="GET",
                status_code=404,
                status="ORDER_NOT_FOUND",
                error_message=detail,
                request_id=request_id,
            )
            return None, {"detail": detail, "status_code": 404}

        if resp.status_code == 409:
            data = resp.json()
            detail = data.get("detail", "Result not available yet.")
            log_transaction(
                endpoint=endpoint,
                method="GET",
                status_code=409,
                status="RESULT_NOT_READY",
                error_message=detail,
                request_id=request_id,
            )
            return None, {"detail": detail, "status_code": 409}

        detail = f"Unexpected LIS response (HTTP {resp.status_code})."
        log_transaction(
            endpoint=endpoint,
            method="GET",
            status_code=resp.status_code,
            status="SERVER_ERROR",
            error_message=detail,
            request_id=request_id,
        )
        return None, {"detail": detail, "status_code": 502}
