"""
Integration tests for the HMS <-> LIS API integration.

Covers authentication, request validation, order submission, result
retrieval, error handling, idempotency and transaction logging.
"""

import uuid

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from hms.models import Patient
from lis.models import LabOrder, LabTestCatalog
from integration.models import IntegrationLog


class BaseAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.lab_user = User.objects.create_user(
            username="lab_admin", password="LabAdmin#2024"
        )
        self.hms_user = User.objects.create_user(
            username="hms_demo", password="HmsDemo#2024"
        )
        LabTestCatalog.objects.create(code="CBC", name="Complete Blood Count")
        LabTestCatalog.objects.create(code="BS", name="Blood Sugar (Fasting)")
        self.patient = Patient.objects.create(
            patient_number="HMS-0001",
            first_name="Amina",
            last_name="Juma",
            date_of_birth="1990-04-12",
            gender="F",
        )

    def auth(self, username="hms_demo"):
        user = self.lab_user if username == "lab_admin" else self.hms_user
        self.client.force_authenticate(user=user)


class AuthenticationTests(BaseAPITestCase):
    def test_unauthenticated_request_is_rejected(self):
        resp = self.client.get("/api/lis/catalog/")
        self.assertEqual(resp.status_code, 401)

    def test_jwt_token_can_be_obtained(self):
        resp = self.client.post(
            "/api/auth/token/",
            {"username": "hms_demo", "password": "HmsDemo#2024"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.json())


class HMSValidationTests(BaseAPITestCase):
    def test_missing_fields_rejected(self):
        self.auth()
        resp = self.client.post("/api/hms/lab-requests/", {"test_code": "CBC"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("patient_number", resp.json())
        self.assertIn("test_name", resp.json())

    def test_unknown_patient_rejected(self):
        self.auth()
        resp = self.client.post(
            "/api/hms/lab-requests/",
            {
                "patient_number": "NO-SUCH",
                "test_code": "CBC",
                "test_name": "Complete Blood Count",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("does not exist", resp.json()["patient_number"][0])

    def test_invalid_request_id_uuid_rejected(self):
        self.auth()
        resp = self.client.post(
            "/api/hms/lab-requests/",
            {
                "request_id": "not-a-uuid",
                "patient_number": "HMS-0001",
                "test_code": "CBC",
                "test_name": "Complete Blood Count",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)


class LabOrderIngestTests(BaseAPITestCase):
    def payload(self, **overrides):
        data = {
            "request_id": str(uuid.uuid4()),
            "patient_number": "HMS-0001",
            "patient_first_name": "Amina",
            "patient_last_name": "Juma",
            "patient_date_of_birth": "1990-04-12",
            "test_code": "CBC",
            "test_name": "Complete Blood Count",
        }
        data.update(overrides)
        return data

    def setUp(self):
        super().setUp()
        self.auth("lab_admin")

    def test_valid_order_is_accepted(self):
        resp = self.client.post("/api/lis/orders/", self.payload(), format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.json()["accepted"])
        self.assertTrue(resp.json()["order_number"].startswith("LIS-"))

    def test_unknown_test_code_rejected_422(self):
        resp = self.client.post(
            "/api/lis/orders/", self.payload(test_code="XYZ-999"), format="json"
        )
        self.assertEqual(resp.status_code, 422)
        self.assertFalse(resp.json()["accepted"])

    def test_future_dob_rejected_400(self):
        resp = self.client.post(
            "/api/lis/orders/",
            self.payload(patient_date_of_birth="2999-01-01"),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_duplicate_request_id_is_idempotent(self):
        rid = str(uuid.uuid4())
        first = self.client.post("/api/lis/orders/", self.payload(request_id=rid), format="json")
        second = self.client.post("/api/lis/orders/", self.payload(request_id=rid), format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            first.json()["order_number"], second.json()["order_number"]
        )
        self.assertEqual(LabOrder.objects.count(), 1)

    def test_ingest_is_transaction_logged(self):
        self.client.post("/api/lis/orders/", self.payload(), format="json")
        self.assertTrue(
            IntegrationLog.objects.filter(status="ORDER_ACCEPTED").exists()
        )


class ResultRetrievalTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.auth("lab_admin")
        rid = uuid.uuid4()
        resp = self.client.post(
            "/api/lis/orders/",
            {
                "request_id": str(rid),
                "patient_number": "HMS-0001",
                "patient_first_name": "Amina",
                "patient_last_name": "Juma",
                "patient_date_of_birth": "1990-04-12",
                "test_code": "CBC",
                "test_name": "Complete Blood Count",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.request_id = rid
        self.order = LabOrder.objects.get(hms_request_id=rid)
        self.auth("hms_demo")

    def test_result_not_ready_returns_409(self):
        resp = self.client.get(f"/api/lis/orders/{self.request_id}/result/")
        self.assertEqual(resp.status_code, 409)
        self.assertIn("not available", resp.json()["detail"].lower())

    def test_result_retrieved_after_processing(self):
        self.auth("lab_admin")
        resp = self.client.post(
            f"/api/lis/orders/{self.request_id}/process/",
            {
                "result_value": "4.8",
                "unit": "10^3/uL",
                "reference_range": "4.0-10.0",
                "is_abnormal": False,
                "performed_by": "Tech. Neema Kileo",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self.order.refresh_from_db() or self.order.status, "COMPLETED")

        self.auth("hms_demo")
        resp = self.client.get(f"/api/lis/orders/{self.request_id}/result/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result"]["result_value"], "4.8")

    def test_unknown_request_id_returns_404(self):
        resp = self.client.get(f"/api/lis/orders/{uuid.uuid4()}/result/")
        self.assertEqual(resp.status_code, 404)

    def test_retrieval_is_transaction_logged(self):
        self.client.get(f"/api/lis/orders/{self.request_id}/result/")
        self.assertTrue(
            IntegrationLog.objects.filter(status="RESULT_NOT_READY").exists()
        )
