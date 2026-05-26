import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import client, ensure_database_indexes
from app.routes import auth
from app.routes import notes
from app.routes import users

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await ensure_database_indexes()
    except Exception:
        logger.exception("Failed to initialize database indexes")
        raise

    yield

    client.close()


app = FastAPI(lifespan=lifespan)

origins = get_settings().cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "backend app is running."}

app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(notes.router, prefix="/api/notes", tags=["Notes"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
