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
│   └── routes/             # Route handlers for users and tasks
├── seeders/
│   ├── seed.py             # Runs all seeders
│   ├── users_seeder.py     # Seeds user data
│   └── tasks_seeder.py     # Seeds task data
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
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

Requires a running MongoDB instance. Set `MONGO_URI` in a `.env` file.

## Docker Setup

| Command                        | Description                         |
| ------------------------------ | ----------------------------------- |
| `docker compose up --build -d` | Build and start all services        |
| `docker compose up -d`         | Start services (no rebuild)         |
| `docker compose down`          | Stop and remove containers          |

Docker Compose services:

- **backend** — FastAPI app on port `4000`
- **mongodb** — MongoDB on port `27017` with persistent volume `mongo_data`

## Database Seeding

```bash
# Run all seeders (users + tasks)
docker exec -it python-backend-app python seeders/seed.py

# Seed only users
docker exec -it python-backend-app python seeders/users_seeder.py

# Seed only tasks
docker exec -it python-backend-app python seeders/tasks_seeder.py
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

User schema: `name` (2–100 chars), `email` (valid email), `age` (0–120, optional).

### Tasks — `/api/tasks`

| Method | Endpoint              | Description               |
| ------ | --------------------- | ------------------------- |
| POST   | `/`                   | Create a task             |
| GET    | `/`                   | List all tasks            |
| GET    | `/{task_id}`          | Get task by ID            |
| GET    | `/user/{user_id}`     | Get all tasks for a user  |
| PUT    | `/{task_id}`          | Update a task             |
| DELETE | `/{task_id}`          | Delete a task             |

Task schema: `user` (user ObjectId), `label` (string), `status` (`pending` | `on-going` | `done`).

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
