import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import client, ensure_database_indexes
from app.routes import auth, labels, notes, users
from app.storage import STORAGE_DIR

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

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/api/images", StaticFiles(directory=str(STORAGE_DIR)), name="images")

app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(notes.router, prefix="/api/notes", tags=["Notes"])
app.include_router(labels.router, prefix="/api/labels", tags=["Labels"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "backend app is running."}
