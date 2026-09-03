from collections.abc import Generator
from sqlalchemy.orm import Session
from app.db.database import SessionLocal


def db_get() -> Generator[Session,None,None]:

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


