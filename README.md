# basic-django-app

A minimal Django + Django REST Framework project template with JWT auth, pytest and factory_boy.

## Stack

- Python 3.14, managed with [uv](https://docs.astral.sh/uv/)
- Django + Django REST Framework
- JWT auth via `djangorestframework-simplejwt`
- SQLite by default (override with `DATABASE_URL`)
- pytest + pytest-django + factory_boy
- black, isort, flake8, pre-commit

## Layout

```
config/          project settings and root urls
users/           custom User model, JWT token endpoints, user CRUD API, UserFactory
common/          sample app: Sample model, ModelViewSet, SampleFactory
conftest.py      shared pytest fixtures (api_client, authed_api_client)
```

## Setup

```bash
uv sync                      # creates .venv with Python 3.14 + all deps
cp .env.example .env         # optional; edit as needed
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

The Django admin is at `/admin/`, with `User` and `Sample` registered. Log in with the superuser created above.

## API

All API routes are versioned under `/api/v1/`. Every endpoint requires a JWT
unless it opts in with `permission_classes = [AllowAny]`. Tokens carry a hash of the
user's password, so changing the password revokes every previously issued token.

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/auth/token/` | Obtain access + refresh tokens (`username`, `password`) |
| POST | `/api/v1/auth/token/refresh/` | Get a new access token (`refresh`) |
| POST | `/api/v1/auth/token/verify/` | Verify a token (`token`) |
| POST | `/api/v1/users/` | Sign up (no token needed) |
| GET, PUT, PATCH, DELETE | `/api/v1/users/` | Read / update / delete your own profile (`email` is read-only); never a list |
| POST | `/api/v1/users/change-password/` | Change password (`current_password`, `new_password`); revokes old tokens and returns new ones |
| GET, POST | `/api/v1/common/samples/` | List / create samples |
| GET, PUT, PATCH, DELETE | `/api/v1/common/samples/<id>/` | Retrieve / update / delete a sample |

```bash
curl -X POST localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "..."}'

curl localhost:8000/api/v1/common/samples/ -H "Authorization: Bearer <access>"
```

## Tests

```bash
uv run pytest
uv run pytest --cov
```

Tests are class-based, marked with `@pytest.mark.django_db`, build data with
factory_boy factories (`<app>/factories/`), and authenticate with the
`authed_api_client(user)` fixture.

## Linting

```bash
uv run pre-commit install    # run hooks on every commit
uv run pre-commit run --all-files
```
