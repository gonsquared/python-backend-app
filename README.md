# python-backend-app

## Requirements:

- Docker Desktop
- Docker Compose

## Running the application:

docker-compose up --build

## Running the users seeder:

docker exec -it fastapi-backend python users_seeder.py

## Stoping the application:

docker-compose down

## Restarting the application:

docker-compose up -d
