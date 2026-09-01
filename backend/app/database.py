from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.orm import Session
from typing import Generator
from backend.app.config import settings

engine_kwargs = {"pool_pre_ping": True}
if "sqlite" not in settings.database_url:
    engine_kwargs.update({"pool_size": 5, "max_overflow": 10})

engine = create_engine(
    settings.database_url,
    **engine_kwargs
)

# SessionLocal is a factory class for generating database sessions (temporary transactions)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class used by SQLAlchemy ORM models to map tables
Base = declarative_base()

# FastAPI Dependency Injection provider for database sessions
def get_db() -> Generator[Session, None, None]:
    """
    Yields a database session instance to be used within a single API request context,
    ensuring that the connection is closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
