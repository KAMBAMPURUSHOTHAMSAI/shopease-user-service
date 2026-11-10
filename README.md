# ShopEase User Management Microservice

Independent FastAPI microservice for customer profiles and delivery addresses. It integrates with the existing ShopEase Authentication Service by validating its signed JWT access tokens. It does **not** implement registration, login, password storage, or a second authentication database.

## 1. Features

- Create, retrieve, replace, partially update, and delete the authenticated user's profile.
- Create, list, retrieve, replace, partially update, delete, and set the default delivery address.
- Validate bearer JWTs issued by the existing ShopEase Authentication Service.
- Derive `auth_user_id` only from the token's `sub` claim; clients cannot submit an owner ID to take ownership of another profile or address.
- Enforce one default address per profile when an address is made default. Default changes lock the profile row in MySQL before clearing the prior default.
- Support local profile deactivation without silently changing the Authentication Service account state.
- SQLAlchemy ORM, Alembic migrations, MySQL 8.4, Docker Compose, Swagger UI, Postman collection, and SQLite-backed API tests.

## 2. Technology Stack

| Area | Technology |
|---|---|
| Runtime / API | Python 3.11, FastAPI, Uvicorn |
| Validation | Pydantic v2 |
| Database | MySQL 8.4, SQLAlchemy 2, PyMySQL |
| Migrations | Alembic |
| Authentication | PyJWT, HS256 bearer-token validation |
| Containerization | Docker, Docker Compose |
| Testing | Swagger UI, Postman, pytest, FastAPI TestClient |

## 3. Project Structure

```text
shopease-user-service/
├── app/
│   ├── main.py
│   ├── routers/
│   │   ├── user_routes.py
│   │   └── address_routes.py
│   ├── models/
│   │   ├── user_model.py
│   │   └── address_model.py
│   ├── schemas/
│   │   ├── user_schema.py
│   │   └── address_schema.py
│   ├── services/
│   │   ├── user_service.py
│   │   └── address_service.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   └── database/
│       └── connection.py
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/0001_create_user_profiles_and_addresses.py
├── tests/
│   ├── conftest.py
│   └── test_user_api.py
├── postman/ShopEase_User_Service.postman_collection.json
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── requirements.txt
├── .env.example
├── .gitignore
├── .dockerignore
└── README.md
```

## 4. Authentication Service Integration

The existing ShopEase Authentication Service issues HS256 JWT access tokens. Its documented token contract contains:

- `sub`: Authentication Service user ID (numeric ID serialized as text).
- `role`: user role (for example, `customer`).
- `iss`: `shopease-auth-service`.
- `exp`: token expiry.

The User Service validates the token signature, algorithm, issuer, subject, and expiry. It obtains `auth_user_id` from `sub` and never trusts a user ID supplied in a request body or query parameter.

### Critical shared setting

The User Service must use the **exact same `JWT_SECRET_KEY` value** as the existing Authentication Service. Copy it securely from the Authentication Service's private `.env` into this service's `.env`. Do not use the placeholder from `.env.example`. Keep the same algorithm (`HS256`) and issuer (`shopease-auth-service`). Do not commit either service's `.env` file or expose the signing secret in screenshots.

This implementation performs local signature validation with the shared HS256 secret. For production, protect secret distribution carefully; consider a public-key signing/verification contract (for example RS256/JWKS) or a dedicated introspection contract if services should not share a symmetric signing secret.

### Request header

```http
Authorization: Bearer <access_token_from_auth_service>
```

There are deliberately no `/register` or `/login` endpoints in this service. Register and log in only through the Authentication Service at `http://localhost:8002`.

## 5. Database Design

Database: `shopease_user_db`.

### `user_profiles`

| Column | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| auth_user_id | Integer | Unique ID from Authentication Service |
| full_name | String(150) | Required |
| phone_number | String(25) | Required and validated |
| date_of_birth | Date | Optional; must be in the past |
| gender | String(30) | Optional; Male, Female, Other, Prefer not to say |
| profile_image | String(500) | Optional URL or storage path |
| is_active | Boolean | User Service local profile status; extension for deactivation requirement |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

### `user_addresses`

| Column | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| user_id | Integer | FK to `user_profiles.id`, cascade delete |
| address_type | String(20) | Home, Office, Other |
| full_name | String(150) | Required recipient name |
| phone_number | String(25) | Required and validated |
| address_line_1 | String(255) | Required |
| address_line_2 | String(255) | Optional |
| city / state / country | String | Required |
| postal_code | String(20) | Required and validated |
| is_default | Boolean | At most one default per profile |
| created_at / updated_at | DateTime | Timestamps |

The profile table's `auth_user_id` is unique. The address table has a foreign-key relationship to the local profile. A profile deletion cascades to its saved addresses. The `is_active` profile field is an explicit extension to support User Service-local deactivation; it is not an Authentication Service credential or account-status field.

## 6. Environment Configuration

Create a private `.env` file from the template:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set unique database passwords. Most importantly, copy the existing Authentication Service's actual `JWT_SECRET_KEY` into this service's `.env` exactly. Example placeholders are not valid shared secrets.

```dotenv
APP_NAME=ShopEase User Service
APP_VERSION=1.0.0
APP_PORT=8004
DEBUG=false

DB_HOST=127.0.0.1
DB_PORT=3309
DB_NAME=shopease_user_db
DB_USER=shopease_user
DB_PASSWORD=replace-with-a-strong-user-db-password
DB_ROOT_PASSWORD=replace-with-a-different-strong-root-password

JWT_SECRET_KEY=copy-the-exact-secret-from-shopease-auth-service
JWT_ALGORITHM=HS256
JWT_ISSUER=shopease-auth-service
```

Ports are intentionally separate from the earlier services: Auth API `8002`, Auth MySQL host port `3308`, Product API `8003`, User API `8004`, and User MySQL host port `3309`.

## 7. Run with Docker Compose (Recommended)

Prerequisites: Docker Desktop running; `.env` created and filled with real private values.

From the project root:

```powershell
docker compose build --no-cache user-api
docker compose up -d
docker compose ps
docker compose logs --tail=100 user-api
```

Compose starts:

- `shopease-user-mysql` — MySQL 8.4 with persistent named volume `user_mysql_data`.
- `shopease-user-container` — FastAPI User Service.

The API waits for `user-db` to become healthy. Inside Compose, the API connects to host `user-db` on internal port `3306`, not `localhost`. The container runs `alembic upgrade head` before Uvicorn starts.

Open:

- Swagger UI: `http://localhost:8004/docs`
- Health check: `http://localhost:8004/health`

Stop containers without deleting saved data:

```powershell
docker compose down
```

Only when intentionally deleting the User Service database and all profile/address records:

```powershell
docker compose down -v
```

Do not use `down -v` for a normal restart.

## 8. Local Development

Run the MySQL service in Docker and the API from the local virtual environment:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# Start only the User Service database
docker compose up -d user-db

# Apply the schema migration
alembic upgrade head

# Run FastAPI locally
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8004
```

## 9. API Catalogue

Base URL: `http://localhost:8004`. All profile and address endpoints require a valid Bearer JWT from the Authentication Service.

### Profile and account APIs

| Method | Endpoint | Purpose | Success |
|---|---|---|---:|
| POST | `/api/users/profile` | Create the current user's profile | 201 |
| GET | `/api/users/profile` | Retrieve current user's profile | 200 |
| PUT | `/api/users/profile` | Replace current user's profile | 200 |
| PATCH | `/api/users/profile` | Partially update profile fields | 200 |
| DELETE | `/api/users/profile` | Delete current profile and its addresses | 204 |
| POST | `/api/users/profile/deactivate` | Deactivate only the local User Service profile | 200 |
| GET | `/api/users/account` | Retrieve account/profile information | 200 |
| GET | `/api/users/account/status` | Retrieve local profile status | 200 |

Profile creation example (no `auth_user_id` field is accepted):

```json
{
  "full_name": "ShopEase Test User",
  "phone_number": "+91 9876543210",
  "date_of_birth": "2000-01-10",
  "gender": "Prefer not to say",
  "profile_image": null
}
```

### Address APIs

| Method | Endpoint | Purpose | Success |
|---|---|---|---:|
| POST | `/api/users/addresses` | Add an address | 201 |
| GET | `/api/users/addresses` | List current user's addresses | 200 |
| GET | `/api/users/addresses/{address_id}` | Retrieve one owned address | 200 |
| PUT | `/api/users/addresses/{address_id}` | Replace an owned address | 200 |
| PATCH | `/api/users/addresses/{address_id}` | Partially update an owned address | 200 |
| DELETE | `/api/users/addresses/{address_id}` | Delete an owned address | 204 |
| PATCH | `/api/users/addresses/{address_id}/default` | Set an owned address as default | 200 |

Address creation example:

```json
{
  "address_type": "Home",
  "full_name": "ShopEase Test User",
  "phone_number": "+91 9876543210",
  "address_line_1": "12 Main Road",
  "address_line_2": "Near City Park",
  "city": "Kurnool",
  "state": "Andhra Pradesh",
  "country": "India",
  "postal_code": "518001",
  "is_default": true
}
```

When a new or updated address is marked default, the service clears the previous default for that profile in the same transaction. The profile row is locked during default changes to serialize concurrent updates on MySQL. The service permits zero default addresses, but never intentionally sets more than one default for a profile.

### Authorization behavior

- Missing, malformed, invalid, or expired JWT: `401 Unauthorized`.
- A valid Auth Service token whose user has not created a local profile: `404 Not Found`.
- A request for an existing address owned by a different profile: `403 Forbidden`.
- A nonexistent address: `404 Not Found`.
- Duplicate profile for one `auth_user_id`: `409 Conflict`.
- Invalid request fields: `422 Unprocessable Entity`.
- Operations against a locally deactivated profile: `403 Forbidden`.

The API never accepts `auth_user_id` or local `user_id` in create/update payloads as an ownership credential. Ownership is derived from the verified token subject and local database relationships.

## 10. Account Deactivation Semantics

`POST /api/users/profile/deactivate` sets `user_profiles.is_active = false` in the User Service database only. It does **not** delete or update the Authentication Service `users` row, revoke the Authentication Service token, or prevent login at the Authentication Service. While the local profile is inactive, profile and address operations are blocked by this service.

To disable authentication globally, the Authentication Service must separately deactivate its own user record through its own reviewed administrative/account process. The two services own separate databases and do not silently mutate each other's account state.

`DELETE /api/users/profile` is a separate hard-delete operation. It deletes the local profile and cascades its addresses; it still does not delete the Authentication Service account.

## 11. Alembic Migrations and Database Verification

```powershell
alembic current
alembic history
alembic upgrade head
```

Verify tables using MySQL:

```powershell
docker compose exec user-db mysql -u root -p shopease_user_db
```

Then:

```sql
SHOW TABLES;
DESCRIBE user_profiles;
DESCRIBE user_addresses;
SELECT id, auth_user_id, full_name, is_active FROM user_profiles;
SELECT id, user_id, address_type, is_default FROM user_addresses;
EXIT;
```

## 12. Testing

### Automated tests

The included API tests use an isolated in-memory SQLite database and test JWT signature validation with a test-only key. They do not write to the MySQL database.

```powershell
pip install -r requirements.txt
python -m pytest -q
```

### Swagger / Postman manual testing

1. Start Auth Service and User Service. Register/login only through Auth Service (`http://localhost:8002/docs`).
2. Copy the login `access_token` into Swagger Authorize on `http://localhost:8004/docs` or Postman collection variable `access_token`.
3. Create profile; repeat to verify duplicate response 409.
4. Get, PUT, PATCH and delete the current user's profile.
5. Create at least two addresses; mark the first default, then mark the second default; verify only one is true.
6. List/get/update/delete an address and test the `/default` action.
7. Use a second Auth Service account/token and try to access the first user's address ID; expect 403. A second account without a local profile receives 404 on its own profile lookup.
8. Call profile endpoints without a token and with an invalid/expired token; expect 401.
9. Deactivate a local profile and verify its profile/address operations return 403; verify separately that the Auth Service account state is unchanged.
10. Verify the rows directly in MySQL using the SQL commands above.

Import `postman/ShopEase_User_Service.postman_collection.json`. Set:

- `base_url` = `http://localhost:8004`
- `access_token` = token copied from the existing Auth Service login response

The collection does not contain login/register requests by design.

## 13. GitHub Submission

Before committing, verify `.env` and `venv/` are ignored. Commit `.env.example`, never `.env`.

```powershell
git init
git branch -M main
git add app alembic tests postman Dockerfile docker-compose.yml alembic.ini requirements.txt README.md .env.example .gitignore .dockerignore
git status
git check-ignore -v .env venv
git commit -m "Build ShopEase User Management Microservice"
git remote add origin https://github.com/KAMBAMPURUSHOTHAMSAI/shopease-user-service.git
git push -u origin main
```

## 14. Security and Operational Notes

- The User Service has no local registration/login and stores no password or password hash.
- Never commit `.env`, database passwords, or JWT signing secrets.
- JWT validation uses the existing Auth Service's HS256 secret, algorithm, issuer, `sub`, and `exp` contract.
- User and address reads/writes are scoped to the authenticated identity.
- Profile deletion is a local hard delete with address cascade; local deactivation is a reversible database flag only via an administrative DB operation (no public reactivation endpoint is exposed).
- Back up the named `user_mysql_data` volume before destructive database maintenance.
- This source package is a starting implementation. Run the supplied tests and the full Docker/MySQL + Auth-token integration workflow in your Windows environment before declaring the assignment complete.
