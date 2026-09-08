# HMS ↔ LIS Integration (Group 2)

An API-based integration between a **Hospital Management System (HMS)** and a
**Laboratory Information System (LIS)**, built with Django + Django REST
Framework on **PostgreSQL** — everything runs in **Docker**.

The HMS submits a laboratory test request to the LIS over HTTP and later
retrieves the patient's laboratory results. The project demonstrates:

| Requirement | Where it is shown |
|---|---|
| **Request validation** | `hms/serializers.py`, `lis/serializers.py`, and explicit checks in `lis/views.py` (unknown patient, unknown test code → 422, future DOB, blank fields, bad UUIDs) |
| **Authentication** | JWT (`djangorestframework-simplejwt`) — `/api/auth/token/`; every API call requires `Authorization: Bearer <token>` |
| **Authorization** | Service-level permissioning: HMS service account submits orders; LIS-side processing endpoints demonstrated in the demo with the lab-staff account |
| **Response handling** | `integration/lis_client.py` maps LIS responses (201/200/400/404/409/422/5xx) to HMS `LabRequest` status transitions |
| **Error handling** | Connection errors, auth failures, retries with token refresh, DB failures wrapped in `transaction.atomic()`, and consistent JSON error bodies |
| **Transaction logging** | Every inbound and outbound exchange is persisted in `integration.IntegrationLog` (Postgres table) |## Architecture

```
+-----------+   HTTP/JSON + JWT    +-----------+
|   HMS     | -------------------> |    LIS    |
| (hms app) |  POST /api/lis/orders| (lis app) |
|           | <--------------------|           |
+-----------+  status / results    +-----------+
      |                                   |
      +-------- integration.IntegrationLog (audit trail) --------+
```

Both systems run in one Django project (two apps) so the demo is self-contained,
but they only communicate through the public HTTP API — nothing is shared.

A single-page **dashboard** at `/` visually demonstrates the whole flow:
submit requests as the HMS, process them as lab staff, watch results arrive,
and see every transaction logged live.

### Endpoints

| Method | URL | Purpose |
|---|---|---|
| GET | `/` | **Dashboard frontend (demo UI)** |
| POST | `/api/auth/token/` | Obtain JWT (username + password) |
| POST | `/api/auth/token/refresh/` | Refresh JWT |
| GET/POST | `/api/hms/patients/` | List / create patients (HMS-side) |
| GET/POST | `/api/hms/lab-requests/` | List / submit lab test requests (HMS → LIS) |
| GET | `/api/hms/lab-requests/<request_id>/result/` | HMS retrieves result from LIS |
| GET/POST | `/api/lis/orders/` | List orders / LIS ingests an order (idempotent on `request_id`) |
| GET | `/api/lis/orders/<request_id>/` | Order status incl. result when complete |
| POST | `/api/lis/orders/<request_id>/process/` | Lab staff record the result |
| GET | `/api/lis/orders/<request_id>/result/` | LIS-side result retrieval (409 until ready) |
| GET | `/api/lis/catalog/` | Active lab test catalog |
| GET | `/api/logs/?limit=50` | Integration transaction log (JSON) |

## Quick start (Docker)

Requires Docker + Docker Compose only.

```bash
docker compose up --build
```

That's it. The `web` container waits for PostgreSQL, runs migrations, seeds the
catalog/users/patients, then serves the app and dashboard at:

> **http://localhost:8000/** — open the dashboard in your browser

- Admin: http://localhost:8000/admin/ (login `lab_admin` / `LabAdmin#2024`)
- Demo accounts: `lab_admin` / `LabAdmin#2024` and `hms_demo` / `HmsDemo#2024`
- Demo patients: `HMS-0001` Amina Juma, `HMS-0002` Baraka Mushi, `HMS-0003` Neema Kileo

### Run the demonstration

**Option A — in the browser (recommended for the demo):**

1. Open http://localhost:8000/
2. Click **▶ Run Full Demo (auto)** — it walks through validation errors,
   auth check, submission, 409 result-not-ready, lab processing, result
   retrieval, 422 unknown test code, and idempotent re-submission.
3. Watch the HMS requests, LIS orders/results, and the integration transaction
   log update live. Or drive each step manually with the buttons.

**Option B — CLI script:**

```bash
python simulate_integration.py   # run on the host, or:
docker compose exec web python simulate_integration.py  # inside the container
```

> Note: inside the container the script's `BASE_URL` must be
> `http://web:8000` (container-to-container); `http://127.0.0.1:8000` works
> when run from the host.

### Inspect the transaction log

### Inspect the transaction log

From the dashboard's **Integration Transaction Log** panel, via the API
(`/api/logs/?limit=50`), or:

```bash
python manage.py transaction_log -n 30
```

or browse http://localhost:8000/admin/ → **Integration logs**
(login: `lab_admin` / `LabAdmin#2024`).

## Test accounts

| Username | Password | Role |
|---|---|---|
| `lab_admin` | `LabAdmin#2024` | Lab staff / admin |
| `hms_demo` | `HmsDemo#2024` | HMS service account |

Demo patients: `HMS-0001` Amina Juma, `HMS-0002` Baraka Mushi, `HMS-0003` Neema Kileo.

## Tests

```bash
python manage.py test integration                 # on the host
docker compose exec web python manage.py test integration  # in Docker
```

Covers authentication, validation, order ingestion, idempotency, result
lifecycle (409 → 200), unknown-request handling, and transaction logging.

## Notes

- `docker compose up --build` is the single command: Postgres + Django
  (gunicorn) + auto-migrations + auto-seeding + dashboard.
- Database settings come from `.env` (`POSTGRES_*`); the Postgres container
  stores data in a named volume, so it survives restarts.
- The LIS client authenticates once, caches the JWT, retries once on 401 with a
  fresh token, and logs every exchange — including failures.
- `request_id` (UUID) is the correlation key across both systems and is the
  idempotency key for order submission.
