# CLAUDE.md

In all interactions and commit messages, be extremely concise and sacrifice grammar for the sake of concision.

## Project Overview

Django REST API for the Bunker Hills Men's Club (BHMC) golf organization. Manages event registration, payments, tournament scoring, and member management.

## Development Commands

```bash
# Install dependencies (uses uv package manager)
uv sync

# Run development server
uv run python manage.py runserver

# Run tests
uv run python manage.py test

# Run single test file
uv run python manage.py test register.tests.test_registration

# Run single test class
uv run python manage.py test register.tests.test_registration.RegistrationTests

# Run migrations
uv run python manage.py migrate

# Create migrations
uv run python manage.py makemigrations

# Lint with ruff
uvx ruff check {file or folder}

# Format with ruff
uvx ruff format {file or folder}

# Docker development (starts MySQL, Redis, Mailpit, Django, Celery)
docker-compose up
```

## Architecture

### Django Apps
- **bhmc/**: Main Django project with settings, URLs, Celery config
- **core/**: User management, authentication, season settings, middleware
- **events/**: Event models (tournaments, weeknight events, majors), fee types, rounds, tournament results
- **register/**: Player profiles, event registrations, registration slots, fees
- **payments/**: Stripe payment processing, refunds
- **courses/**: Golf course and hole data
- **damcup/**: Season-long points competition
- **scores/**: Event scoring
- **documents/**: Photos and document management
- **content/**: Tags and page content
- **messaging/**: Announcements and contact messages
- **policies/**: Club policies
- **reporting/**: Report generation

### Key Patterns
- REST API via Django REST Framework with `DefaultRouter` (see `bhmc/urls.py`)
- Token authentication with Djoser for user management
- `ModelViewSet` pattern for CRUD operations with `@action` decorators for custom endpoints
- Custom managers for complex queries (e.g., `EventManager`, `RegistrationSlotManager`)

### Database
- MySQL 8.4 (production and Docker)
- Environment variables for credentials in `/config/.env.*`

### Environment Configuration
- `DJANGO_ENV` controls environment: `local`, `docker`, or `prod`
- Environment files: `config/.env.local`, `config/.env.docker`, `config/.env`
- Key settings: `SECRET_KEY`, `STRIPE_*`, `DATABASE_*`, `AWS_*`

### Caching & Async
- Redis for caching and Celery broker
- Celery Beat for scheduled tasks
- Task results stored in database via `django-celery-results`

## Code Style

- Follow PEP 8 with 120 character line limit
- Use double quotes for Python strings
- Sort imports with isort
- Use f-strings for string formatting
- Run ruff to lint and format before committing

## Testing

- Tests use Django's `TestCase` with fixtures
- Fixtures located in `*/fixtures/` directories
- Use `APIClient` from `rest_framework.test` for API tests
- Only write tests when explicitly requested

## Plans

- At the end of each plan, give me a list of unresolved questions to answer, if any. Make the questions extremely concise.
