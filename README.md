# FastAPI Calculator — JWT Login & Registration Front-End

A FastAPI application pairing a web calculator with a secure user layer,
built on SQLAlchemy 2.0, Pydantic v2, and bcrypt. This repository adds
the authentication front-end: registration and login pages with
client-side validation, JWT storage in the browser, and Playwright
end-to-end tests driving both pages through their positive and negative
paths — on top of the JWT routes and authenticated calculation BREAD
endpoints from the previous module.

Docker Hub: **<https://hub.docker.com/r/zyrielzero/calculator-frontend>**

```
docker pull zyrielzero/calculator-frontend:latest
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/dbname \
  -e JWT_SECRET=<at-least-32-characters> \
  zyrielzero/calculator-frontend:latest
```

On startup the app creates any missing tables against `DATABASE_URL`, so
a fresh container pointed at an empty database is immediately usable.

## Security Model

The `User` model (`app/models/user.py`) stores a UUID primary key,
`username` and `email` under unique indexed constraints enforced at the
database level, a bcrypt `password_hash`, an `is_active` flag,
`last_login`, and a `created_at` timestamp stamped by the database
through `server_default=func.now()`.

Passwords are hashed with bcrypt directly (`app/security.py`) rather than
through passlib, which is unmaintained and breaks against bcrypt >= 4.1.
Inputs beyond bcrypt's 72-byte limit are rejected explicitly instead of
silently truncated, and verification returns False on a malformed stored
hash, so a corrupted row reads as a failed login rather than a 500.

`UserCreate` validates registration input: username pattern and length,
RFC-compliant email via `EmailStr`, and a password policy requiring mixed
case and at least one digit. `UserRead` never declares `password_hash`,
so the hash cannot serialize into any response. Successful authentication
returns a `Token` envelope carrying a signed JWT.

## Calculation Model (Module 11)

`app/models/calculation.py` stores one calculation per row: a UUID primary
key, float operands `a` and `b`, a `type` string, a `user_id` foreign key
into `users` with `ON DELETE CASCADE`, and a database-stamped `created_at`.
The result is not stored — it is computed on demand through a strategy
factory (`app/calculation_factory.py`) that resolves each type to a
registered operation class, so a stored result can never drift from its
operands. Adding a new operation is one class and one decorator.

Two CHECK constraints back the application-layer rules at the database
level: `type` must be one of `add`, `sub`, `multiply`, `divide`, and a
`divide` row can never hold a zero divisor.

`CalculationCreate` validates inbound payloads — finite numeric operands
(NaN and infinity rejected), case-insensitive type strings validated
against the enum, and a zero divisor refused on divide. `CalculationRead`
serializes the row plus the computed `result` and never exposes anything
beyond its declared fields.

Calculation tests run inside the same suites and gates as the user tests;
no workflow changes were needed:

```
pytest tests/unit/test_calculation_factory.py \
       tests/unit/test_calculation_model.py \
       tests/unit/test_calculation_schemas.py
pytest tests/integration/test_calculation_persistence.py
```

## HTTP Routes (Module 12)

`app/routers/users.py` exposes the user service over HTTP:

| Endpoint          | Also at     | Method | Body                        | Success            | Error                          |
| ----------------- | ----------- | ------ | --------------------------- | ------------------ | ------------------------------ |
| `/users/register` | `/register` | POST   | JSON `UserCreate`           | `201` + `UserRead` | `409` duplicate, `400` invalid |
| `/users/login`    | `/login`    | POST   | form `username`, `password` | `200` + `Token`    | `401` bad credentials          |

Each endpoint answers at two paths. The `/users` prefix is the canonical
form and is what `tokenUrl` and the test suite target; an alias router
also serves the unprefixed paths, delegating to the same two functions
so there is one implementation behind both addresses. The GET routes
rendering the HTML pages sit on those same unprefixed paths under a
different method, which FastAPI resolves independently.

Login accepts the OAuth2 password form rather than JSON so the Swagger
UI Authorize button works end to end. Wrong password and unknown
username return byte-identical 401 responses, so the API never confirms
whether a username exists.

`app/routers/calculations.py` provides the BREAD surface. Every route
requires a bearer token and operates only on rows the caller owns; a
calculation belonging to another user returns the same 404 as one that
does not exist.

| Endpoint             | Method | Meaning                                | Success                    |
| -------------------- | ------ | -------------------------------------- | -------------------------- |
| `/calculations`      | GET    | Browse the caller's calculations       | `200` + list               |
| `/calculations/{id}` | GET    | Read one owned calculation             | `200` + `CalculationRead`  |
| `/calculations/{id}` | PUT    | Edit operands and type, re-validated   | `200` + recomputed result  |
| `/calculations`      | POST   | Add a calculation                      | `201` + `CalculationRead`  |
| `/calculations/{id}` | DELETE | Delete one owned calculation           | `204`                      |

Edits pass through the same `CalculationCreate` validation as creation,
so an update can never store a payload creation would have refused
(zero divisor on divide, unknown type, non-finite operands).

## Front-End Pages (Module 13)

Two Jinja2-served pages give the auth routes a browser surface:

| Page        | Path        | Talks to          | On success                          |
| ----------- | ----------- | ----------------- | ----------------------------------- |
| Register    | `/register` | `/users/register` | Success message, link to login      |
| Log in      | `/login`    | `/users/login`    | JWT stored, then spent on a read    |

The registration page validates before anything reaches the network,
mirroring the `UserCreate` schema exactly: username pattern and length,
email format, password length 8–72 with mixed case and a digit, and a
confirm-password match. Invalid input renders an inline error and no
request is sent; the server's Pydantic layer remains the authority for
anything that gets through.

The login page performs the assignment's minimal checks (both fields
present) and posts the OAuth2 password form — the same content type the
Swagger Authorize button sends — so one endpoint serves both flows. The
form field accepts a username or an email; the service layer matches
either column. A `401` renders "Invalid credentials." without revealing
which field was wrong.

On success the JWT is stored under `access_token` in `localStorage` and
immediately spent: the page issues `GET /calculations` with an
`Authorization: Bearer` header and reports the row count in the success
message. That endpoint rejects any request without a valid token, so a
number appearing at all is proof the stored credential authenticates —
storage and use demonstrated in one step. Module 14 grows the full BREAD
interface out of this call.

## Secret Management

`app/config.py` reads `JWT_SECRET` from the environment (or a local
`.env` file) with a dev-only fallback. Every real runtime injects a real
secret:

- **Local:** copy `.env.example` to `.env` and generate a value with
  `openssl rand -hex 32`. `.env` is gitignored.
- **Docker Compose:** the web service declares
  `JWT_SECRET: ${JWT_SECRET:?...}`, interpolated from the same `.env`.
  The `:?` form makes a missing secret a hard startup error instead of
  letting the container silently run on the dev default.
- **CI:** the workflow injects a throwaway value for tests. The deploy
  job never bakes a secret into the image — the image reads it from the
  environment at `docker run` time, which is why the pull command above
  requires `-e JWT_SECRET`.

## End-to-End Tests

`tests/e2e/test_auth_e2e.py` drives the real pages in Chromium against a
live server:

- **Positive:** register with valid data and assert the success message;
  log in with correct credentials and assert the success message reports
  zero saved calculations — the authenticated read succeeded — with a
  three-part JWT present in `localStorage`.
- **Negative:** register with a short password and assert the
  client-side error renders with no success; log in with a wrong
  password and assert the 401 surfaces as "Invalid credentials." with
  nothing stored.

Credentials are uuid-suffixed per test because the server and database
live for the whole pytest session. Assertions use Playwright's
auto-waiting `expect`, which retries until the fetch resolves and the
DOM updates — the same race guard the calculator e2e tests use.

### Manual verification via OpenAPI

Start the app (`docker compose up --build` or `python main.py` with
`DATABASE_URL` and `JWT_SECRET` set) and open <http://localhost:8000/docs>.

1. `POST /users/register` → Try it out → expect `201`.
2. Click **Authorize** and enter the same username and password. Swagger
   posts the form to `/users/login` and holds the bearer token.
3. `POST /calculations` with `{"a": 6, "b": 7, "type": "multiply"}` →
   `201` with `"result": 42.0`.
4. `GET /calculations` lists the row; `PUT` with
   `{"a": 84, "b": 2, "type": "divide"}` still yields `42.0`;
   `DELETE` returns `204`; a re-read returns `404`.
5. Log out via the lock icon and retry `GET /calculations` → `401`.

## Setup and Run (Docker Compose)

The stack runs three services: the FastAPI app, PostgreSQL 16, and
pgAdmin 4.

```
docker compose up --build
```

| Service    | URL                     | Credentials                         |
| ---------- | ----------------------- | ----------------------------------- |
| Calculator | <http://localhost:8000> | -                                   |
| pgAdmin    | <http://localhost:5050> | <admin@example.org> / admin         |
| PostgreSQL | localhost:5432          | postgres / postgres, db fastapi_db  |

Inside pgAdmin, register the server with host `db` (the Compose service
name), not localhost.

## Running Tests Locally

Dependencies are split across two files: `requirements.txt` is the
runtime freeze the Docker image installs, and `requirements-dev.txt`
layers test and lint tooling on top. Local development installs the dev
file.

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
playwright install chromium
```

Integration tests need a reachable PostgreSQL database. Copy
`.env.example` to `.env`, point `DATABASE_URL` at one (the Compose
Postgres works), and generate a secret — `app/config.py` reads the file
automatically, so no exports are needed:

```
cp .env.example .env
sed -i "s/replace-with-64-hex-chars/$(openssl rand -hex 32)/" .env
```

Then run the suites:

```
pytest                                                     # full suite
pytest tests/unit                                          # no database required
pytest tests/unit tests/integration --cov-fail-under=100   # the CI coverage gate
pytest tests/e2e                                           # Playwright against a live server
```

Unit tests cover the operations layer, password hashing, schema
validation, and model column definitions with no database. Integration
tests exercise registration, uniqueness collisions, authentication,
token resolution, and the active-user gate against a real Postgres —
and, in `test_user_routes.py` and `test_calculation_routes.py`, drive
the full HTTP stack through TestClient: register/login round trips
verified in the database, the complete BREAD cycle, ownership isolation
from two users' perspectives, and error paths for invalid payloads. The
e2e fixture starts the app with the same interpreter running pytest, so
results are stable locally and in CI.

## API

| Endpoint    | Method | Body               | Success           | Error                  |
| ----------- | ------ | ------------------ | ----------------- | ---------------------- |
| `/add`      | POST   | `{"a": 1, "b": 2}` | `{"result": 3}`   | `400 {"error": "..."}` |
| `/subtract` | POST   | `{"a": 5, "b": 2}` | `{"result": 3}`   | `400 {"error": "..."}` |
| `/multiply` | POST   | `{"a": 2, "b": 3}` | `{"result": 6}`   | `400 {"error": "..."}` |
| `/divide`   | POST   | `{"a": 6, "b": 2}` | `{"result": 3.0}` | `400` on zero divisor  |

Malformed payloads return 400 with an `error` field through a custom
validation handler. User registration and authentication live in
`app/services/user_service.py` and `app/auth/`, exposed over HTTP by
`app/routers/users.py` and the pages above.

## CI/CD Pipeline

GitHub Actions (`.github/workflows/test.yml`) runs three sequential jobs
on every push and pull request to main.

**test** spins up a PostgreSQL 16 service container, installs
`requirements-dev.txt`, and runs unit tests, the unit + integration
suite under a 100% coverage gate, and the Playwright e2e suite.

**scan** builds the Docker image and runs a Trivy vulnerability scan.
Any unpatched CRITICAL or HIGH finding fails the job, which blocks
deployment. The image installs only the runtime freeze, so test and lint
tooling never enters the scan surface.

**deploy** runs only on pushes to main after a clean scan. It builds and
pushes the image to Docker Hub tagged `latest` and with the commit SHA:
<https://hub.docker.com/r/zyrielzero/calculator-frontend>