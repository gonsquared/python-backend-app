from fastapi import FastAPI
from app.routes import users, tasks

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Welcome to the Python Users API"}

app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
