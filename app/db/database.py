from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings






# create_engine crea el motor de conexión con la base de datos.
#
# connect_args={"check_same_thread": False}
# es necesario con SQLite cuando trabajamos con FastAPI,
# porque las requests pueden ejecutarse en distintos threads.
engine = create_engine(
    settings.database_url,
    connect_args=(
        {"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {}
    ),
)



SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)