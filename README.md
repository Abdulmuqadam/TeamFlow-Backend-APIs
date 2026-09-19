# TeamFlow API

TeamFlow is a multi-tenant project-management REST API built with Django REST Framework. It provides email-based accounts, JWT authentication, organizations, role-based memberships, projects, and tasks.

The project is a working multi-tenant backend foundation with the core identity, tenant isolation, organization, project, and task workflows implemented and verified for the project/task API layer. The codebase includes role-aware organization access, project task enumeration and validation, and API coverage for the project task flow.

## Current Scope

### Implemented

- Custom user model with email login
- User registration and current-user profile endpoint
- JWT access and refresh tokens
- Organization creation and membership-scoped organization listing
- Organization roles: `OWNER`, `ADMIN`, and `MEMBER`
- Adding existing users to organizations by email
- Organization member role changes and removals
- Organization-scoped projects with `ACTIVE` and `ARCHIVED` statuses
- Project-scoped tasks with status, priority, assignment, and due date
- Tenant-aware permission checks for organizations, projects, and tasks
- OpenAPI schema, Swagger UI, and ReDoc
- Separate base, development, and production settings modules

### Project Status

This repository is suitable for local development and API integration work. It is not yet production-ready. The most important remaining work is:

- Complete production settings, including `ALLOWED_HOSTS`, database configuration, secret management, email delivery, static files, and deployment serving.
- Add rate limiting, structured logging, error monitoring, health checks, and backup procedures.
- Decide whether Django admin needs model registrations and add them if required.
- Add a declared project license.
- Add more regression coverage for edge cases around assignment validation, ordering, search, and project statistics.

## Technology Stack

- Python 3.12+
- Django 6.1.1
- Django REST Framework 3.18.1
- `djangorestframework-simplejwt` 5.5.1
- `drf-spectacular` 0.30.0
- PostgreSQL via Psycopg for development settings
- SQLite fallback in the shared base settings
- Ruff for formatting

All pinned dependencies are listed in [requirements.txt](requirements.txt).

## Architecture

```text
config/
  settings/       Shared, development, and production configuration
apps/
  users/          Custom user model, registration, login support, and profile API
  organizations/  Organizations, memberships, serializers, permissions, and API
  projects/       Projects, tasks, serializers, permissions, and API
```

The tenant hierarchy is:

```text
User -> Membership -> Organization -> Project -> Task
```

`Membership` is an explicit through model between users and organizations. It stores the user's organization role and enforces one membership per user and organization. API queries and permission checks use the organization associated with the requested resource to prevent cross-tenant access.

## Requirements

- Python 3.12 or newer
- PostgreSQL 14 or newer when using `config.settings.development`
- A PostgreSQL database and user matching the environment variables below

## Local Setup

The project defaults to the shared SQLite configuration for local development and test execution, while `config.settings.development` remains the PostgreSQL-oriented profile for a real local database setup.

### 1. Create a virtual environment

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

Create a local `.env` file from the provided template:

```powershell
Copy-Item .env.example .env
```

Set values appropriate for the local PostgreSQL instance:

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Django signing key; use a unique secret outside local development |
| `DEBUG` | Enables development diagnostics when `True` |
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | PostgreSQL username |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | PostgreSQL host, commonly `localhost` |
| `DB_PORT` | PostgreSQL port, commonly `5432` |

The PostgreSQL development profile uses `sslmode=require`. If your local PostgreSQL instance does not require SSL, change that option or switch to the SQLite base profile for lightweight local work.

### 4. Apply migrations

```powershell
python manage.py migrate
```

### 5. Start the development server

```powershell
python manage.py runserver
```

The API is available at `http://127.0.0.1:8000/`.

## API Documentation

The API is versioned under `/api/v1/`.

| Resource | URL |
| --- | --- |
| Swagger UI | `http://127.0.0.1:8000/api/v1/docs/` |
| ReDoc | `http://127.0.0.1:8000/api/v1/redoc/` |
| OpenAPI schema | `http://127.0.0.1:8000/api/v1/schema/` |

## Authentication

Protected endpoints require a JWT access token:

```http
Authorization: Bearer <access-token>
```

Access tokens expire after 30 minutes. Refresh tokens expire after 7 days. Refresh token rotation and blacklisting are currently disabled.

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/register/` | Public | Create an account with email, full name, and password |
| `POST` | `/api/v1/auth/login/` | Public | Obtain access and refresh tokens |
| `POST` | `/api/v1/auth/refresh/` | Public | Obtain a new access token |
| `GET` | `/api/v1/auth/me/` | Authenticated | Return the current user's profile |

Passwords must be at least eight characters when registering. Passwords are hashed through Django's user manager and are never returned by the API.

## API Reference

### Organizations and memberships

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/v1/organizations/` | Authenticated | List organizations where the current user is a member |
| `POST` | `/api/v1/organizations/` | Authenticated | Create an organization; the creator becomes `OWNER` |
| `GET` | `/api/v1/organizations/{organization_id}/members/` | Organization member | List memberships |
| `POST` | `/api/v1/organizations/{organization_id}/members/` | Owner or admin | Add an existing user by email |
| `GET` | `/api/v1/organizations/{organization_id}/members/{membership_id}/` | Organization member | Retrieve a membership |
| `PATCH` | `/api/v1/organizations/{organization_id}/members/{membership_id}/` | Owner or admin | Change a member's role |
| `DELETE` | `/api/v1/organizations/{organization_id}/members/{membership_id}/` | Owner or admin | Remove a member |

Ownership cannot be reassigned or removed through the membership API. Members can read membership data but cannot manage it. A user cannot remove themself from an organization through this endpoint.

### Projects

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/v1/organizations/{organization_id}/projects/` | Organization member | List projects in an organization |
| `POST` | `/api/v1/organizations/{organization_id}/projects/` | Owner or admin | Create a project in an organization |
| `GET` | `/api/v1/projects/{project_id}/` | Organization member | Retrieve a project |
| `PUT` / `PATCH` | `/api/v1/projects/{project_id}/` | Owner or admin | Update a project |
| `DELETE` | `/api/v1/projects/{project_id}/` | Owner or admin | Delete a project |
| `GET` | `/api/v1/projects/{project_id}/stats/` | Organization member | Return project task summary counts for the dashboard |

Projects are automatically associated with the organization in the URL and record the authenticated creator.

### Tasks

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/v1/projects/{project_id}/tasks/` | Organization member | List tasks in a project |
| `POST` | `/api/v1/projects/{project_id}/tasks/` | Owner or admin | Create a task |
| `GET` | `/api/v1/tasks/{task_id}/` | Organization member | Retrieve a task |
| `PUT` / `PATCH` | `/api/v1/tasks/{task_id}/` | Owner/admin, or assigned member | Update a task |
| `DELETE` | `/api/v1/tasks/{task_id}/` | Owner or admin | Delete a task |

Supported task list query parameters:

- `?status=TODO|IN_PROGRESS|DONE`
- `?priority=LOW|MEDIUM|HIGH`
- `?assigned_to=<user_id>`
- `?search=<keyword>`
- `?ordering=created_at|-created_at|due_date|-due_date|priority|-priority`
- `?page=<number>`
- `?page_size=<number>`

Tasks support the statuses `TODO`, `IN_PROGRESS`, and `DONE`, and the priorities `LOW`, `MEDIUM`, and `HIGH`. Assignment is optional. Regular members may update only tasks assigned to them.

## Role Permissions

| Capability | Owner | Admin | Member |
| --- | :---: | :---: | :---: |
| View organization and memberships | Yes | Yes | Yes |
| Add organization members | Yes | Yes | No |
| Change non-owner member roles | Yes | Yes | No |
| Remove non-owner members | Yes | Yes | No |
| Create, update, or delete projects | Yes | Yes | No |
| Create tasks | Yes | Yes | No |
| View tasks | Yes | Yes | Yes |
| Update assigned tasks | Yes | Yes | Own assignments only |
| Delete tasks | Yes | Yes | No |

## Testing and Quality Checks

Run the Django checks and the relevant project suite with:

```powershell
python manage.py check
python manage.py test apps.projects.tests --settings=config.settings.base
```

Format Python code with:

```powershell
ruff format .
```

The project includes API coverage for user authentication, organization membership enforcement, project access rules, task creation permissions, task validation, and project-scoped task behavior. The project/task test suite is active and passes under the SQLite-backed local configuration used for development and verification.

## Security and Operations Notes

- Do not commit `.env` or real credentials.
- Use a strong, unique `SECRET_KEY` outside local development.
- Configure explicit production `ALLOWED_HOSTS`; the production settings currently leave it empty.
- Review database SSL, secret loading, email delivery, static files, and serving configuration before deployment.
- Add rate limiting, request logging, error monitoring, health checks, backups, and a deployment process before exposing the API publicly.

## License

No license has been declared yet.
