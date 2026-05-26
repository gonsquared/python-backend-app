# python-backend-app

A REST API backend built with FastAPI and MongoDB, containerized with Docker.

## Project Structure

```
.
├── app/
│   ├── main.py             # FastAPI app, CORS config, router registration
│   ├── database.py         # MongoDB connection via Motor
│   ├── helpers/            # Serialization utilities
│   ├── middlewares/        # Request middleware (email validation)
│   ├── models/             # Pydantic models for request/response
│   └── routes/             # Route handlers for users
├── seeders/
│   ├── seed.py             # Runs all seeders
│   └── users_seeder.py     # Seeds user data
├── .env_dev                # Development environment variables
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Tech Stack

| Category       | Technology                  |
| -------------- | --------------------------- |
| Language       | Python 3.12                 |
| Framework      | FastAPI                     |
| ASGI Server    | Uvicorn                     |
| Database       | MongoDB                     |
| DB Driver      | Motor (async)               |
| Validation     | Pydantic v1                 |
| Containerization | Docker + Docker Compose   |

## Prerequisites

- Docker Desktop
- Docker Compose

## Environment Variables

The app reads from `.env` at runtime. The `Dockerfile` copies `.env_dev` to `.env` inside the container.

| Variable    | Description              | Default                      |
| ----------- | ------------------------ | ---------------------------- |
| `MONGO_URI` | MongoDB connection string | `mongodb://mongodb:27017`   |
| `DB_NAME`   | MongoDB database name    | `backendapp`                 |
| `ADMIN_EMAIL` | Seeded admin user email | Required for user seeder |
| `ADMIN_PASSWORD` | Seeded admin user password | Required for user seeder |

For local development without running the backend in Docker, use a local `.env`
file like this:

```bash
MONGO_URI=mongodb://localhost:27018
DB_NAME=backendapp
ADMIN_EMAIL=
ADMIN_PASSWORD=
```

## Getting Started

```bash
# Clone the repo
git clone <repo-url>
cd python-backend-app

# Start the app and MongoDB
docker compose up --build -d
```

The API will be available at `http://localhost:4000`.

## Running Locally (without Docker)

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

Requires a running MongoDB instance. Set `MONGO_URI` in a `.env` file.
If you want Docker to run only MongoDB while FastAPI runs locally, start MongoDB
with:

```bash
docker compose up -d mongodb
```

This project maps MongoDB to `localhost:27018` to avoid conflicts with other
local MongoDB containers using `27017`.

On newer Debian/Ubuntu Python installs, running `pip install -r requirements.txt`
directly may fail with `externally-managed-environment`. Use the project virtual
environment commands above instead of installing packages into system Python.

## Running Tests

```bash
.venv/bin/pytest
```

## Pre-Commit Checks

```bash
.venv/bin/pre-commit install
.venv/bin/pre-commit run --all-files
```

The pre-commit hook runs `.venv/bin/python -m pytest` and `.venv/bin/python -m compileall app seeders tests`.

## Docker Setup

| Command                        | Description                         |
| ------------------------------ | ----------------------------------- |
| `docker compose up --build -d` | Build and start all services        |
| `docker compose up -d`         | Start services (no rebuild)         |
| `docker compose down`          | Stop and remove containers          |

Docker Compose services:

- **backend** — FastAPI app on port `4000`
- **mongodb** — MongoDB on host port `27018` with persistent volume `mongo_data`

## Database Seeding

User seeding is non-destructive: sample users are created only when their email does not already exist. The configured admin user is the exception; running the seeder updates that account so it always has the configured admin credentials and permissions.

```bash
# Run all seeders
docker exec -it python-backend-app python seeders/seed.py

# Seed only users
docker exec -it python-backend-app python seeders/users_seeder.py
```

## API Reference

Base URL: `http://localhost:4000`

### Health

| Method | Endpoint | Description         |
| ------ | -------- | ------------------- |
| GET    | `/`      | Check server status |

### Users — `/api/users`

| Method | Endpoint              | Description              |
| ------ | --------------------- | ------------------------ |
| POST   | `/`                   | Create a user            |
| GET    | `/`                   | List all users           |
| GET    | `/{user_id}`          | Get user by ID           |
| GET    | `/by-email/{email}`   | Get user by email        |
| PUT    | `/{user_id}`          | Full update of a user    |
| PATCH  | `/{user_id}`          | Partial update of a user |
| DELETE | `/{user_id}`          | Delete a user            |

User schema: `firstName` (2–100 chars), `lastName` (2–100 chars), `email` (valid email), optional `password` (12–128 chars).

Password values are hashed with Argon2id before storage. API responses do not include password or password hash data.

### Auth — `/api/auth`

| Method | Endpoint    | Description                              |
| ------ | ----------- | ---------------------------------------- |
| POST   | `/register` | Register a user and store a password hash |
| POST   | `/login`    | Verify credentials and return a bearer token |
| GET    | `/activate` | Activate a registered email address       |

Registration body: `firstName`, `lastName`, `email`, `password`, `verifyPassword`.

Login body: `email`, `password`.

Login response includes `accessToken`, `tokenType`, `expiresIn`, and `user`.

New registrations are created with `status: "inactive"`. The API sends an activation email containing a frontend link like `/activate-account?token=...`; opening it changes the user status to `active`. Login returns `403` until the user status is `active`. The supported user statuses are `inactive`, `active`, and `archived`.

In Docker development, activation emails are captured by MailHog:

- MailHog UI: `http://localhost:8025`
- SMTP service: `mailhog:1025`

## Interactive API Docs

FastAPI auto-generates interactive documentation:

- Swagger UI: `http://localhost:4000/docs`
- ReDoc: `http://localhost:4000/redoc`

## CORS

The API allows requests from:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

This matches the default Vite dev server port for a frontend companion app.

## Troubleshooting

**Container fails to start**
Ensure Docker Desktop is running before executing `docker compose` commands.

**Cannot connect to MongoDB**
The backend depends on the `mongodb` service. Start both services together with `docker compose up`, not the backend alone.

**Port already in use**
Check if something else is running on port `4000` or `27017` and stop it before starting the containers.

**Seeder fails**
The container must be running before executing `docker exec` commands. Confirm with `docker ps`.
