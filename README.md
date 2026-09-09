# TeamFlow API

TeamFlow is a multi-tenant project-management API built with Django REST Framework. It provides email-based user accounts, JWT authentication, organizations, and role-based organization membership management.

The project is currently an MVP foundation. The core identity and tenant membership flows are implemented, while automated test coverage and production hardening remain in progress.

## Product Scope

### Implemented

- Custom user model authenticated by email
- Public user registration and authenticated current-user endpoint
- JWT access and refresh tokens
- Organization creation and organization listing for the current user
- Organization memberships with `OWNER`, `ADMIN`, and `MEMBER` roles
- Member invitation by an existing user's email address
- Role updates and member removal with organization-level permission checks
- OpenAPI schema, Swagger UI, and ReDoc documentation
- Separate development and production settings modules

### Current Status

The application is suitable for continued API development and local integration work. It should not yet be treated as production-ready without completing the hardening items below:

- Add automated tests for authentication, tenant isolation, membership permissions, and validation.
- Fix the organization slug generation path for updates to existing organizations.
- Restrict membership updates to the role-only serializer for every update method, including `PUT`.
- Complete production settings, including `ALLOWED_HOSTS`, database configuration, secret management, email backend, and deployment serving.
- Register the custom models with Django admin if administrative management is required.
- Add the project-management domain model and API surface beyond organizations and memberships.

## Technology Stack

- Python
- Django 6.1
- Django REST Framework 3.18
- Simple JWT
- drf-spectacular for OpenAPI documentation
- PostgreSQL for development configuration
- SQLite fallback in the shared base settings
- Ruff for formatting and lint-oriented code quality

## Architecture

```text
config/
  settings/       Shared, development, and production configuration
apps/users/       Custom user model, registration, and current-user API
apps/organizations/
                  Organizations, memberships, serializers, permissions, and API views
```

The application uses a through model, `Membership`, between users and organizations. This keeps tenant membership and role information explicit and allows access checks to be performed against the requested organization.

Authentication is configured globally with JWT Bearer tokens, and authenticated access is the default for API views. Organization and membership queries are scoped to the organization identifier and the requesting user's membership.

## Requirements

- Python 3.12 or newer
- PostgreSQL 14 or newer for the development settings
- A database and user matching the values in `.env`

The pinned Python dependencies are listed in [requirements.txt](requirements.txt).

## Local Setup

### 1. Create and activate a virtual environment

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and set values appropriate for your local PostgreSQL instance:

```powershell
Copy-Item .env.example .env
```

Required variables:

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Django secret key |
| `DEBUG` | Enables development diagnostics when `True` |
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | PostgreSQL user |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | PostgreSQL host, commonly `localhost` |
| `DB_PORT` | PostgreSQL port, commonly `5432` |

The development settings currently require PostgreSQL SSL mode. Adjust the development database options if your local PostgreSQL server does not support SSL.

### 4. Apply migrations

```powershell
python manage.py migrate
```

### 5. Run the development server

```powershell
python manage.py runserver
```

The API is available at `http://127.0.0.1:8000/`.

## API Documentation

| Resource | URL |
| --- | --- |
| Swagger UI | `http://127.0.0.1:8000/api/v1/docs/` |
| ReDoc | `http://127.0.0.1:8000/api/v1/redoc/` |
| OpenAPI schema | `http://127.0.0.1:8000/api/v1/schema/` |

## API Reference

All API routes use the `/api/v1/` prefix.

### Authentication

| Method | Endpoint | Access | Description |
| --- | --- | --- | --- |
| `POST` | `/auth/register/` | Public | Create a user with email, full name, and password |
| `POST` | `/auth/login/` | Public | Obtain access and refresh JWTs |
| `POST` | `/auth/refresh/` | Public | Obtain a new access token |
| `GET` | `/auth/me/` | Authenticated | Return the current user's profile |

Access protected endpoints with:

```text
Authorization: Bearer <access-token>
```

Access tokens expire after 30 minutes. Refresh tokens expire after 7 days.

### Organizations and memberships

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/organizations/` | List organizations where the current user is a member |
| `POST` | `/organizations/` | Create an organization; the creator becomes `OWNER` |
| `GET` | `/organizations/{organization_id}/members/` | List organization members |
| `POST` | `/organizations/{organization_id}/members/` | Add an existing user by email; owner/admin only |
| `GET` | `/organizations/{organization_id}/members/{membership_id}/` | Retrieve a membership |
| `PATCH` | `/organizations/{organization_id}/members/{membership_id}/` | Change a member role; owner/admin only |
| `DELETE` | `/organizations/{organization_id}/members/{membership_id}/` | Remove a member; owner/admin only |

Owners cannot be reassigned or removed through the membership API. Members can view membership data but cannot manage it.

## Useful Commands

```powershell
# Run Django system checks
python manage.py check

# Run the test suite
python manage.py test

# Format Python files
ruff format .

# Create a superuser for Django admin
python manage.py createsuperuser
```

The current test modules are placeholders, so a passing test command does not yet represent meaningful behavioral coverage. Add tests before using the result as a release gate.

## Security and Operations Notes

- Never commit `.env` or place real credentials in documentation. The file is ignored by Git; rotate any credential that may have been exposed elsewhere.
- Use a unique, unpredictable `SECRET_KEY` outside local development.
- Set explicit production `ALLOWED_HOSTS` and configure a managed production database.
- Review membership update behavior before exposing the API to untrusted clients; updates should accept only fields intentionally permitted by the role-management contract.
- Add request logging, error monitoring, rate limiting, backup policy, and a deployment health check before production launch.

## License

No license has been declared yet.