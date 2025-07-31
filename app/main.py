from fastapi import FastAPI
from app.routes import users

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Welcome to the Python Users API"}

app.include_router(users.router, prefix="/api/users", tags=["Users"])
