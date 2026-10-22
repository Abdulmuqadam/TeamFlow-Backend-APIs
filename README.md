# TeamFlow Backend API

TeamFlow is a multi-tenant project-management API built with Django and Django REST Framework. It provides email-based authentication, organization membership and role-based authorization, project and task management, activity history, and private in-app notifications.

The API is tenant-scoped by design: a user can access project-management data only through an active membership in the relevant organization.

## Features

- Custom user model with email authentication
- JWT access and refresh tokens
- Organizations with unique slugs and explicit memberships
- Owner, admin, and member roles
- Tenant-isolated project and task CRUD operations
- Task assignment with organization-member validation
- Task status, priority, due dates, filtering, search, ordering, and pagination
- Project task statistics
- Activity history for task creation, assignment, and status changes
- Private notifications with individual and bulk read actions
- OpenAPI schema with Swagger UI and ReDoc
- Separate development and production settings
- Automated Django API tests and Ruff checks

## Technology

| Component | Version |
| --- | --- |
| Python | 3.13 |
| Django | 6.1.1 |
| Django REST Framework | 3.18.1 |
| Simple JWT | 5.5.1 |
| drf-spectacular | 0.30.0 |
| Database | SQLite by default; PostgreSQL supported |
| Linting and formatting | Ruff 0.16.6 |

All Python dependencies are pinned in [requirements.txt](requirements.txt).

## Architecture

```text
User
  └── Membership (role)
        └── Organization
              └── Project
                    └── Task
```

The `Membership` model is the explicit many-to-many relationship between users and organizations. It stores the user's role and enforces one membership per user and organization.

```text
config/
├── settings/
│   ├── base.py
│   ├── development.py
│   └── production.py
└── urls.py

apps/
├── users/
├── organizations/
├── projects/
└── activity/
```

## Requirements

- Python 3.13 or newer
- PowerShell on Windows, or an equivalent shell on macOS/Linux
- PostgreSQL only when using a PostgreSQL deployment; local development uses SQLite

## Quick start

### 1. Clone the repository

```powershell
git clone https://github.com/Abdulmuqadam/TeamFlow-Backend-APIs.git
cd TeamFlow-Backend-APIs
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure the environment

Copy the example environment file and replace placeholder values:

```powershell
Copy-Item .env.example .env
```

| Variable | Purpose | Local default |
| --- | --- | --- |
| `SECRET_KEY` | Django signing key | Replace the placeholder |
| `DEBUG` | Development diagnostics | `True` |
| `DB_NAME` | PostgreSQL database name | `teamflow_db` |
| `DB_USER` | PostgreSQL user | `postgres` |
| `DB_PASSWORD` | PostgreSQL password | Replace the placeholder |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |

The development profile uses SQLite, so PostgreSQL variables are not required for the default local setup. Do not commit `.env`, credentials, or the local database file.

### 5. Apply migrations and run the server

```powershell
python manage.py migrate
python manage.py runserver
```

The API is available at <http://127.0.0.1:8000/>.

To create an administrator for Django admin:

```powershell
python manage.py createsuperuser
```

## Settings profiles

`manage.py` uses `config.settings.development` by default.

| Module | Use | Database |
| --- | --- | --- |
| `config.settings.base` | Shared defaults and tests | SQLite |
| `config.settings.development` | Local development | SQLite and console email |
| `config.settings.production` | Deployment baseline | Configure for the target platform |

Run a command with another profile by setting `DJANGO_SETTINGS_MODULE`:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings.production"
python manage.py check --deploy
```

Production deployments should set `DEBUG=False`, configure explicit `ALLOWED_HOSTS`, use HTTPS, provide a production database and email backend, and manage secrets outside source control. The production profile enables SSL redirect and HSTS by default; verify those settings against the deployment topology before going live.

## API documentation

The API is versioned under `/api/v1/`:

| Resource | URL |
| --- | --- |
| Swagger UI | <http://127.0.0.1:8000/api/v1/docs/> |
| ReDoc | <http://127.0.0.1:8000/api/v1/redoc/> |
| OpenAPI schema | <http://127.0.0.1:8000/api/v1/schema/> |
| Django admin | <http://127.0.0.1:8000/admin/> |

## Authentication

Register or log in to obtain JWT tokens:

```http
POST /api/v1/auth/register/
Content-Type: application/json

{
  "email": "user@example.com",
  "full_name": "Example User",
  "password": "a-secure-password"
}
```

Use the returned access token on protected requests:

```http
Authorization: Bearer <access-token>
```

Authentication endpoints:

| Method | Endpoint | Access | Description |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/register/` | Public | Register a user |
| `POST` | `/api/v1/auth/login/` | Public | Obtain access and refresh tokens |
| `POST` | `/api/v1/auth/refresh/` | Public | Obtain a new access token |
| `GET` | `/api/v1/auth/me/` | Authenticated | Return the current user's profile |

Access tokens expire after 30 minutes and refresh tokens after 7 days. Refresh-token rotation and blacklisting are currently disabled.

## API reference

All endpoints below are prefixed with `/api/v1`. Protected endpoints require a bearer token.

### Organizations and memberships

| Method | Endpoint | Permission |
| --- | --- | --- |
| `GET`, `POST` | `/organizations/` | Authenticated |
| `GET`, `POST` | `/organizations/{organization_id}/members/` | Member; add requires owner/admin |
| `GET`, `PATCH`, `DELETE` | `/organizations/{organization_id}/members/{membership_id}/` | Read requires member; changes require owner/admin |

Creating an organization makes the creator its `OWNER`. Owners cannot be removed or changed through the membership API, and ownership cannot be transferred through the current API.

### Projects

| Method | Endpoint | Permission |
| --- | --- | --- |
| `GET`, `POST` | `/organizations/{organization_id}/projects/` | List requires member; create requires owner/admin |
| `GET` | `/projects/{project_id}/` | Member |
| `PUT`, `PATCH`, `DELETE` | `/projects/{project_id}/` | Owner/admin |
| `GET` | `/projects/{project_id}/stats/` | Member |

Projects are assigned their organization and creator from the request context; client-supplied values for those fields are ignored.

### Tasks

| Method | Endpoint | Permission |
| --- | --- | --- |
| `GET`, `POST` | `/projects/{project_id}/tasks/` | List requires member; create requires owner/admin |
| `GET` | `/tasks/{task_id}/` | Member |
| `PUT`, `PATCH` | `/tasks/{task_id}/` | Owner/admin or assigned member |
| `DELETE` | `/tasks/{task_id}/` | Owner/admin |
| `GET` | `/tasks/{task_id}/activity/` | Organization member |

Supported task values:

- Status: `TODO`, `IN_PROGRESS`, `DONE`
- Priority: `LOW`, `MEDIUM`, `HIGH`
- Project status: `ACTIVE`, `ARCHIVED`

Task list query parameters:

```text
?status=TODO|IN_PROGRESS|DONE
?priority=LOW|MEDIUM|HIGH
?assigned_to=<user_id>
?search=<keyword>
?ordering=created_at|-created_at|due_date|-due_date|priority|-priority
?page=<number>
?page_size=<number>
```

The default page size is 10 and the maximum is 50. Search checks task titles and descriptions.

Creating a task records a `TASK_CREATED` activity. Assignment and status changes record activity and notify the affected assignee, except when the actor is the assignee.

### Notifications

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/notifications/` | List the authenticated user's notifications |
| `PATCH` | `/notifications/{notification_id}/read/` | Mark one notification as read |
| `POST` | `/notifications/read-all/` | Mark all current-user notifications as read |

Notifications are private to their recipient.

## Role permissions

| Capability | Owner | Admin | Member |
| --- | :---: | :---: | :---: |
| View organization, project, and task data | Yes | Yes | Yes |
| Add organization members | Yes | Yes | No |
| Change non-owner roles | Yes | Yes | No |
| Remove non-owner members | Yes | Yes | No |
| Create, update, or delete projects | Yes | Yes | No |
| Create tasks | Yes | Yes | No |
| Update assigned tasks | Yes | Yes | Own assignments only |
| Delete tasks | Yes | Yes | No |
| View activity and own notifications | Yes | Yes | Yes |

## Testing and quality checks

Run the full test suite:

```powershell
python manage.py test --noinput --parallel 4
```

Run focused tests:

```powershell
python manage.py test apps.users.tests
python manage.py test apps.organizations.tests
python manage.py test apps.projects.tests
python manage.py test apps.activity.tests
```

Run Django checks and Ruff:

```powershell
python manage.py check
python manage.py check --deploy --settings=config.settings.production
python manage.py makemigrations --check --dry-run
ruff check .
ruff format --check .
```

The test suite covers authentication, tenant isolation, membership and role permissions, task validation, filtering, statistics, activity records, notification privacy, and notification side effects.

## Production checklist

Before exposing the API publicly:

- Set a strong, unique `SECRET_KEY` and `DEBUG=False`.
- Configure explicit `ALLOWED_HOSTS`.
- Use managed secret storage and a production database.
- Serve the API over HTTPS and validate SSL redirect/HSTS behavior.
- Configure a production email backend, static files, and WSGI/ASGI serving.
- Add rate limiting, structured logging, monitoring, health checks, and backups.
- Review JWT lifetimes, rotation, and blacklist requirements.
- Never commit `.env`, credentials, generated secrets, or database files.

## Roadmap

- Email notifications
- Background jobs with Celery
- Real-time updates with Django Channels
- CI/CD with GitHub Actions
- Deployment and monitoring improvements
- Expanded test coverage

## License

No license has been declared yet.

## Author

Built as a backend portfolio project demonstrating REST API design, authentication, authorization, relational data modeling, testing, and PostgreSQL integration.
