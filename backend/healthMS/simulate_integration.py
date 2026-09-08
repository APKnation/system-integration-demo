"""End-to-end demonstration: HMS submits a lab request and retrieves results.

Run with the Django dev server running in another terminal:

    python simulate_integration.py

Uses only the public HTTP API (JWT auth, request validation, error handling).
"""

import sys
import time
import uuid

import requests

BASE_URL = "http://127.0.0.1:8000"
LAB_ADMIN = ("lab_admin", "LabAdmin#2024")
HMS_SERVICE = ("hms_demo", "HmsDemo#2024")


def step(n, title):
    print(f"\n{'=' * 72}\nSTEP {n}: {title}\n{'=' * 72}")


def get_token(session, username, password):
    resp = session.post(
        f"{BASE_URL}/api/auth/token/", json={"username": username, "password": password}
    )
    resp.raise_for_status()
    session.headers.update({"Authorization": f"Bearer {resp.json()['access']}"})


def show(resp, note=None):
    if note:
        print(f"-- {note}")
    print(f"   {resp.request.method} {resp.request.path_url} -> HTTP {resp.status_code}")
    try:
        body = resp.json()
        print(f"   {body}")
    except ValueError:
        print(f"   {resp.text[:300]}")


def main():
    lab = requests.Session()
    get_token(lab, *LAB_ADMIN)
    print("Lab staff authenticated (JWT obtained).")

    hms = requests.Session()
    get_token(hms, *HMS_SERVICE)
    print("HMS service authenticated (JWT obtained).")

    # ------------------------------------------------------------------ step 1
    step(1, "Request validation: HMS rejects a lab request with missing fields")
    show(
        hms.post(f"{BASE_URL}/api/hms/lab-requests/", json={"test_code": "CBC"}),
        "Missing patient_number and test_name ->",
    )
    show(
        hms.post(
            f"{BASE_URL}/api/hms/lab-requests/",
            json={
                "patient_number": "NO-SUCH-PATIENT",
                "test_code": "CBC",
                "test_name": "Complete Blood Count",
            },
        ),
        "Unknown patient_number ->",
    )

    # ------------------------------------------------------------------ step 2
    step(2, "Authentication: unauthenticated call is rejected (401)")
    anon = requests.Session()
    show(
        anon.get(f"{BASE_URL}/api/lis/catalog/"),
        "No JWT supplied ->",
    )

    # ------------------------------------------------------------------ step 3
    step(3, "HMS submits a valid lab test request to the LIS")
    show(
        hms.post(
            f"{BASE_URL}/api/hms/lab-requests/",
            json={
                "patient_number": "HMS-0001",
                "test_code": "CBC",
                "test_name": "Complete Blood Count",
            },
        ),
        "Valid request ->",
    )
    show(
        hms.get(f"{BASE_URL}/api/hms/lab-requests/"),
        "Request now stored in HMS with status SENT ->",
    )

    # ------------------------------------------------------------------ step 4
    step(4, "Result not ready yet: LIS returns 409 RESULT_NOT_READY")
    requests_qs = hms.get(f"{BASE_URL}/api/hms/lab-requests/").json()
    request_id = requests_qs[0]["request_id"]
    show(
        hms.get(f"{BASE_URL}/api/hms/lab-requests/{request_id}/result/"),
        "Result retrieval before analysis ->",
    )

    # ------------------------------------------------------------------ step 5
    step(5, "Lab staff processes the order in the LIS")
    order = None
    for attempt in range(20):
        resp = lab.get(f"{BASE_URL}/api/lis/orders/{request_id}/")
        if resp.status_code == 200:
            order = resp.json()
            break
        time.sleep(0.5)
    if order is None:
        print("Could not find the lab order on the LIS; aborting.")
        sys.exit(1)
    print(f"   Found order {order['order_number']} (status={order['status']})")

    show(
        lab.post(
            f"{BASE_URL}/api/lis/orders/{request_id}/process/",
            json={
                "result_value": "4.8",
                "unit": "10^3/uL",
                "reference_range": "4.0-10.0",
                "is_abnormal": False,
                "notes": "Within normal limits.",
                "performed_by": "Tech. Neema Kileo",
                "verified_by": "Dr. Aisha Mwaky",
            },
        ),
        "Result recorded ->",
    )

    # ------------------------------------------------------------------ step 6
    step(6, "HMS retrieves the patient's laboratory result")
    show(
        hms.get(f"{BASE_URL}/api/hms/lab-requests/{request_id}/result/"),
        "Result retrieval ->",
    )

    # ------------------------------------------------------------------ step 7
    step(7, "Unknown test code: LIS rejects with 422")
    show(
        hms.post(
            f"{BASE_URL}/api/hms/lab-requests/",
            json={
                "patient_number": "HMS-0002",
                "test_code": "XYZ-999",
                "test_name": "Non-existent Panel",
            },
        ),
        "HMS forwards request; LIS rejects ->",
    )

    # ------------------------------------------------------------------ step 8
    step(8, "Idempotency: re-submitting the same request_id returns the same order")
    rid = str(uuid.uuid4())
    payload = {
        "request_id": rid,
        "patient_number": "HMS-0003",
        "test_code": "BS",
        "test_name": "Blood Sugar (Fasting)",
    }
    show(
        hms.post(f"{BASE_URL}/api/hms/lab-requests/", json=payload),
        "First submission ->",
    )
    show(
        hms.post(f"{BASE_URL}/api/hms/lab-requests/", json=payload),
        "Second submission (same request_id) ->",
    )

    # ------------------------------------------------------------------ step 9
    step(9, "Transaction log: every request/response exchange was recorded")
    print("   Open Django admin -> Integration logs")
    print("   or run: python manage.py transaction_log -n 30")


if __name__ == "__main__":
    main()
