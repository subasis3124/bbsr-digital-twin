from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.orm import Session
from typing import Generator
from backend.app.config import settings

# Engine represents the core interface to the database, handling connections and pooling.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,      # Checks if connection is alive before querying
    pool_size=5,             # Number of persistent database connections
    max_overflow=10          # Extra connections allowed during peak loads
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
