"""
database.py
------------
Sets up SQLAlchemy — the library that lets Python talk to a real
database using Python objects instead of raw SQL strings.

Three things live here:
  1. `engine`    — the actual connection to the database file
  2. `SessionLocal` — a factory that creates one "conversation" with
                      the database per request
  3. `Base`      — the parent class every table model will inherit from
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite stores the entire database as a single file on disk —
# "portfolio.db" will be created automatically the first time you run
# the app, sitting right next to this script. No separate database
# server to install or run, which makes it the easiest real database
# to start learning with.
DATABASE_URL = "sqlite:///./portfolio.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed only for SQLite + FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    A FastAPI "dependency". FastAPI calls this once per incoming
    request, hands the resulting session to your endpoint function,
    and — thanks to the try/finally — guarantees the session is
    closed afterwards even if the endpoint raises an error.

    You'll see this used in main.py as:
        def some_endpoint(db: Session = Depends(get_db)):
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()