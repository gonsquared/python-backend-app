# python-backend-app

## Requirements:

- Docker Desktop
- Docker Compose

## Running the application:

docker-compose up --build -d

## Running the main seeder:

docker exec -it python-backend-app python seeders/seed.py

## Running the users seeder:

docker exec -it python-backend-app python seeders/users_seeder.py

## Stoping the application:

docker-compose down

## Restarting the application:

docker-compose up -d
