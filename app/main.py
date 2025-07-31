from fastapi import FastAPI
from app.routes import users
from app.middleware.validate_email import validate_email

app = FastAPI()

app.middleware("http")(validate_email)

@app.get("/")
async def root():
    return {"message": "Welcome to the Python Users API"}

app.include_router(users.router, prefix="/api/users", tags=["Users"])
