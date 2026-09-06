from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Engine configuration for PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Enables connection health checks before use
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
