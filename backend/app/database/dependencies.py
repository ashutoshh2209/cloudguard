from typing import Generator
from app.database.session import SessionLocal

def get_db() -> Generator:
    """
    Dependency function to provide a database session per request.
    Closes the session when the request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
