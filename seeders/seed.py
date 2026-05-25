import asyncio
from seeders.users_seeder import seed_users

async def run_seeders():
    print("Seeding users...")
    await seed_users()

    print("\nDone.")

if __name__ == "__main__":
    asyncio.run(run_seeders())
