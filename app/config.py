import os
from dataclasses import dataclass, field
from functools import lru_cache


DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def _parse_csv(value: str | None, default: tuple[str, ...]) -> list[str]:
    if not value:
        return list(default)

    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    mongo_uri: str = field(
        default_factory=lambda: os.getenv("MONGO_URI", "mongodb://mongodb:27017")
    )
    db_name: str = field(default_factory=lambda: os.getenv("DB_NAME", "backendapp"))
    cors_origins: list[str] = field(
        default_factory=lambda: _parse_csv(
            os.getenv("CORS_ORIGINS"),
            DEFAULT_CORS_ORIGINS,
        )
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
