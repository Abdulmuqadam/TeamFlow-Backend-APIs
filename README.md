# TeamFlow Backend API

TeamFlow is a multi-tenant project-management backend built with Django and Django REST Framework. It provides email-based authentication, JWT tokens, organization membership and roles, projects, tasks, task activity history, project statistics, and user notifications.

The API is designed around tenant isolation: users can access project-management data only through organizations where they have an active membership.

## Features

- Custom user model with email authentication
- User registration and authenticated profile endpoint
- JWT access and refresh tokens
- Organizations with unique slugs
- Organization membership roles:
  - `OWNER`
  - `ADMIN`
  - `MEMBER`
- Tenant-scoped organization, project, task, activity, and notification access
- Organization member management
- Projects with `ACTIVE` and `ARCHIVED` statuses
- Tasks with:
  - `TODO`, `IN_PROGRESS`, and `DONE` statuses
  - `LOW`, `MEDIUM`, and `HIGH` priorities
  - Optional due dates
  - Organization-member assignment validation
- Task list pagination, filtering, searching, and ordering
- Project task statistics
- Task activity history for creation, assignment, and status changes
- Notifications for task assignment and status changes
- Individual and bulk notification read actions
- OpenAPI schema, Swagger UI, and ReDoc
- Separate base, development, and production settings
- Django and Ruff validation support

## Technology Stack

- Python 3.13
- Django 6.1.1
- Django REST Framework 3.18.1
- Simple JWT 5.5.1
- drf-spectacular 0.30.0
- SQLite for the default local/test configuration
- PostgreSQL client dependencies included for deployment-oriented database configuration
- Ruff 0.16.6

Pinned dependencies are listed in [requirements.txt](requirements.txt).

## Project Structure

```text
config/
  settings/
    base.py
    development.py
    production.py
  urls.py

apps/
  users/
    models.py
    serializers.py
    views.py
    tests.py
  organizations/
    models.py
    permissions.py
    serializers.py
    views.py
    tests.py
  projects/
    models.py
    pagination.py
    permissions.py
    serializers.py
    views.py
    tests.py
  activity/
    models.py
    notification_models.py
    notification_services.py
    serializers.py
    services.py
    views.py
    tests.py
```

The main tenant hierarchy is:

```text
User
  -> Membership
    -> Organization
      -> Project
        -> Task
```

`Membership` is an explicit many-to-many through model. It stores the user's organization role and enforces one membership per user and organization.

## Requirements

- Python 3.13 or newer
- PowerShell on Windows, or an equivalent shell on another platform
- PostgreSQL is optional for local development because the default configuration uses SQLite

## Installation

### 1. Clone the repository

```powershell
git clone https://github.com/Abdulmuqadam/TeamFlow-Backend-APIs.git
cd TeamFlow-Backend-APIs
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example file:

```powershell
Copy-Item .env.example .env
```

At minimum, set a non-default secret:

```dotenv
SECRET_KEY=replace-with-a-long-random-secret
DEBUG=True
```

The example file also contains database variables for environments that provide a PostgreSQL configuration:

| Variable | Description |
| --- | --- |
| `SECRET_KEY` | Django signing key |
| `DEBUG` | Enables development diagnostics |
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASSWORD` | Database password |
| `DB_HOST` | Database host |
| `DB_PORT` | Database port |

Do not commit `.env` or real credentials.

### 5. Apply migrations

```powershell
python manage.py migrate
```

### 6. Start the development server

```powershell
python manage.py runserver
```

The API is available at `http://127.0.0.1:8000/`.

## Settings Profiles

`manage.py` uses `config.settings.development` by default.

| Settings module | Intended use | Database |
| --- | --- | --- |
| `config.settings.base` | Shared defaults and tests | SQLite |
| `config.settings.development` | Local development | SQLite, console email |
| `config.settings.production` | Deployment baseline | Inherits the base database unless deployment settings override it |

The production profile enables secure cookies, HTTPS redirect, HSTS, and configurable allowed hosts. Configure these values through environment variables before deployment:

```dotenv
ALLOWED_HOSTS=api.example.com
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
```

The production database, static-file serving, email delivery, logging, and secret-management strategy should be finalized for the target deployment platform.

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

Access tokens expire after 30 minutes. Refresh tokens expire after 7 days. Refresh-token rotation and blacklisting are disabled in the current configuration.

### Authentication endpoints

| Method | Endpoint | Access | Description |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/register/` | Public | Register a user |
| `POST` | `/api/v1/auth/login/` | Public | Obtain access and refresh tokens |
| `POST` | `/api/v1/auth/refresh/` | Public | Obtain a new access token |
| `GET` | `/api/v1/auth/me/` | Authenticated | Return the current user's profile |

Registration requires an email, full name, and password. Passwords are hashed by Django and are never returned by the API.

Example registration request:

```json
{
  "email": "user@example.com",
  "full_name": "Example User",
  "password": "a-secure-password"
}
```

## API Reference

### Organizations and memberships

| Method | Endpoint | Access | Description |
| --- | --- | --- | --- |
| `GET` | `/api/v1/organizations/` | Authenticated | List the user's organizations |
| `POST` | `/api/v1/organizations/` | Authenticated | Create an organization; creator becomes `OWNER` |
| `GET` | `/api/v1/organizations/{organization_id}/members/` | Member | List organization memberships |
| `POST` | `/api/v1/organizations/{organization_id}/members/` | Owner/admin | Add an existing user by email |
| `GET` | `/api/v1/organizations/{organization_id}/members/{membership_id}/` | Member | Retrieve a membership |
| `PATCH` | `/api/v1/organizations/{organization_id}/members/{membership_id}/` | Owner/admin | Change a non-owner member's role |
| `DELETE` | `/api/v1/organizations/{organization_id}/members/{membership_id}/` | Owner/admin | Remove a non-owner member |

Ownership cannot be transferred or removed through the membership API. Members can read membership data but cannot manage it. Users cannot remove themselves through the membership endpoint.

### Projects

| Method | Endpoint | Access | Description |
| --- | --- | --- | --- |
| `GET` | `/api/v1/organizations/{organization_id}/projects/` | Member | List organization projects |
| `POST` | `/api/v1/organizations/{organization_id}/projects/` | Owner/admin | Create a project |
| `GET` | `/api/v1/projects/{project_id}/` | Member | Retrieve a project |
| `PUT` / `PATCH` | `/api/v1/projects/{project_id}/` | Owner/admin | Update a project |
| `DELETE` | `/api/v1/projects/{project_id}/` | Owner/admin | Delete a project |
| `GET` | `/api/v1/projects/{project_id}/stats/` | Member | Return task status counts |

Projects receive their organization and creator from the request context. Client-supplied values for these server-owned fields are ignored.

### Tasks

| Method | Endpoint | Access | Description |
| --- | --- | --- | --- |
| `GET` | `/api/v1/projects/{project_id}/tasks/` | Member | List project tasks |
| `POST` | `/api/v1/projects/{project_id}/tasks/` | Owner/admin | Create a task |
| `GET` | `/api/v1/tasks/{task_id}/` | Member | Retrieve a task |
| `PUT` / `PATCH` | `/api/v1/tasks/{task_id}/` | Owner/admin or assigned member | Update a task |
| `DELETE` | `/api/v1/tasks/{task_id}/` | Owner/admin | Delete a task |

Task creation records a `TASK_CREATED` activity. Status changes and assignment changes record activity entries. Assignment and status changes also create notifications for the affected assignee, except when the actor is the assignee.

#### Task list query parameters

```text
?status=TODO|IN_PROGRESS|DONE
?priority=LOW|MEDIUM|HIGH
?assigned_to=<user_id>
?search=<keyword>
?ordering=created_at|-created_at|due_date|-due_date|priority|-priority
?page=<number>
?page_size=<number>
```

The default page size is 10 and the maximum page size is 50. Search checks both task titles and descriptions.

### Task activity

| Method | Endpoint | Access | Description |
| --- | --- | --- | --- |
| `GET` | `/api/v1/tasks/{task_id}/activity/` | Organization member | List task activity history |

Activity entries include the actor, actor email, action, message, metadata, and creation timestamp.

### Notifications

| Method | Endpoint | Access | Description |
| --- | --- | --- | --- |
| `GET` | `/api/v1/notifications/` | Authenticated | List notifications for the current user |
| `PATCH` | `/api/v1/notifications/{notification_id}/read/` | Notification recipient | Mark one notification as read |
| `POST` | `/api/v1/notifications/read-all/` | Authenticated | Mark all current-user notifications as read |

Notification responses include the task ID, task title, notification type, message, read state, and creation timestamp. Users cannot read or modify another user's notifications.

## Project Statistics Response

`GET /api/v1/projects/{project_id}/stats/` returns:

```json
{
  "project_id": 1,
  "project_name": "Website refresh",
  "total_tasks": 3,
  "todo": 1,
  "in_progress": 1,
  "done": 1
}
```

## Role Permissions

| Capability | Owner | Admin | Member |
| --- | :---: | :---: | :---: |
| View organization data | Yes | Yes | Yes |
| Add organization members | Yes | Yes | No |
| Change non-owner member roles | Yes | Yes | No |
| Remove non-owner members | Yes | Yes | No |
| Create, update, or delete projects | Yes | Yes | No |
| Create tasks | Yes | Yes | No |
| View projects and tasks | Yes | Yes | Yes |
| Update assigned tasks | Yes | Yes | Own assignments only |
| Delete tasks | Yes | Yes | No |
| View task activity | Yes | Yes | Yes |
| View own notifications | Yes | Yes | Yes |

## Testing and Quality Checks

Run all tests:

```powershell
python manage.py test --noinput --parallel 4
```

Run focused tests:

```powershell
python manage.py test apps.projects.tests
python manage.py test apps.activity.tests
```

Run Django validation:

```powershell
python manage.py check
python manage.py check --deploy --settings=config.settings.production
python manage.py makemigrations --check --dry-run
```

Run Ruff:

```powershell
ruff check .
ruff format --check .
```

The test suite covers authentication, organization membership, tenant isolation, project and task permissions, task validation, filtering, statistics, activity records, notification privacy, notification read actions, and notification side effects.

## Security and Production Checklist

Before exposing the API publicly:

- Set a strong, unique `SECRET_KEY`.
- Set `DEBUG=False`.
- Configure explicit `ALLOWED_HOSTS`.
- Use a production database and configure database credentials securely.
- Configure SMTP or another production email backend.
- Serve the application through HTTPS.
- Keep `SECURE_SSL_REDIRECT`, secure cookies, and HSTS aligned with the deployment topology.
- Configure static files and a production WSGI/ASGI serving strategy.
- Add rate limiting, structured logging, error monitoring, health checks, and backups.
- Review JWT lifetime, rotation, and blacklist requirements.
- Never commit `.env`, credentials, database files, or generated secrets.

## License

No license has been declared yet.
