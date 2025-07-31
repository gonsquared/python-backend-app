import asyncio
from seeders.users_seeder import seed_users
from seeders.tasks_seeder import seed_tasks

async def run_seeders():
    print("Seeding users...")
    await seed_users()

    print("Seeding tasks...")
    await seed_tasks()

    print("\nDone.")

if __name__ == "__main__":
    asyncio.run(run_seeders())
